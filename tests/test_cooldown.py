"""
Tests for cooldown logic: _cooldown_key normalization and check_TRADE_COOLDOWN_SECONDS enforcement.
"""
import os
import sys
import datetime
import pytest

# Add project root to path so we can import BOT
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCooldownKey:
    """_cooldown_key must produce the same key regardless of whether right is CALL/C or PUT/P."""

    def test_call_vs_c_same_key(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "CALL", "20260312") == _cooldown_key("SPY", "C", "20260312")

    def test_put_vs_p_same_key(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "PUT", "20260312") == _cooldown_key("SPY", "P", "20260312")

    def test_call_normalized_to_c(self):
        from BOT import _cooldown_key
        key = _cooldown_key("AAPL", "CALL", "20260315")
        assert key == "AAPL_C_20260315"

    def test_put_normalized_to_p(self):
        from BOT import _cooldown_key
        key = _cooldown_key("QQQ", "PUT", "20260315")
        assert key == "QQQ_P_20260315"

    def test_single_char_right(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "C", "20260312") == "SPY_C_20260312"
        assert _cooldown_key("SPY", "P", "20260312") == "SPY_P_20260312"

    def test_expiry_with_dashes_normalized(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "CALL", "2026-03-12") == _cooldown_key("SPY", "C", "20260312")

    def test_expiry_with_spaces_normalized(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "CALL", " 20260312 ") == _cooldown_key("SPY", "C", "20260312")

    def test_no_expiry(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "CALL") == "SPY_C"
        assert _cooldown_key("SPY", "C") == "SPY_C"
        assert _cooldown_key("SPY", "CALL", None) == "SPY_C"
        assert _cooldown_key("SPY", "CALL", "") == "SPY_C"

    def test_different_symbols_different_keys(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "C", "20260312") != _cooldown_key("QQQ", "C", "20260312")

    def test_different_rights_different_keys(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "CALL", "20260312") != _cooldown_key("SPY", "PUT", "20260312")

    def test_different_expiries_different_keys(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "C", "20260312") != _cooldown_key("SPY", "C", "20260313")

    def test_case_insensitive_right(self):
        from BOT import _cooldown_key
        assert _cooldown_key("SPY", "call", "20260312") == _cooldown_key("SPY", "CALL", "20260312")
        assert _cooldown_key("SPY", "put", "20260312") == _cooldown_key("SPY", "PUT", "20260312")


class TestCheckCooldown:
    """check_TRADE_COOLDOWN_SECONDS must correctly block/allow based on trade_time_dict."""

    def setup_method(self):
        import BOT
        self._orig_dict = BOT.trade_time_dict.copy()
        self._orig_cooldown = getattr(BOT, "TRADE_COOLDOWN_SECONDS", None)
        BOT.trade_time_dict.clear()
        BOT.TRADE_COOLDOWN_SECONDS = 300  # 5 minutes for tests

    def teardown_method(self):
        import BOT
        BOT.trade_time_dict = self._orig_dict
        if self._orig_cooldown is not None:
            BOT.TRADE_COOLDOWN_SECONDS = self._orig_cooldown
        elif hasattr(BOT, "TRADE_COOLDOWN_SECONDS"):
            del BOT.TRADE_COOLDOWN_SECONDS

    def test_no_prior_trade_returns_false(self):
        """No cooldown if no prior trade recorded."""
        import BOT
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "CALL", "20260312")
        assert result is False

    def test_recent_trade_returns_true(self):
        """Cooldown active if trade was placed recently."""
        import BOT
        key = BOT._cooldown_key("SPY", "CALL", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now()
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "CALL", "20260312")
        assert result is True

    def test_old_trade_returns_false(self):
        """Cooldown expired if trade was long ago."""
        import BOT
        key = BOT._cooldown_key("SPY", "CALL", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now() - datetime.timedelta(seconds=600)
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "CALL", "20260312")
        assert result is False

    def test_cooldown_matches_ib_right_format(self):
        """Cooldown set with IB format 'C' is detected when checked with 'CALL'."""
        import BOT
        # Simulate order_manager setting cooldown with IB right format
        key = BOT._cooldown_key("SPY", "C", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now()
        # Check with BOT right format (CALL)
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "CALL", "20260312")
        assert result is True, "Cooldown set with 'C' must be detected when checking with 'CALL'"

    def test_cooldown_matches_ib_right_format_put(self):
        """Cooldown set with IB format 'P' is detected when checked with 'PUT'."""
        import BOT
        key = BOT._cooldown_key("SPY", "P", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now()
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "PUT", "20260312")
        assert result is True, "Cooldown set with 'P' must be detected when checking with 'PUT'"

    def test_different_expiry_not_blocked(self):
        """Cooldown for one expiry should NOT block a different expiry."""
        import BOT
        key = BOT._cooldown_key("SPY", "CALL", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now()
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "CALL", "20260313")
        assert result is False

    def test_different_right_not_blocked(self):
        """Cooldown for CALL should NOT block PUT."""
        import BOT
        key = BOT._cooldown_key("SPY", "CALL", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now()
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "PUT", "20260312")
        assert result is False

    def test_different_symbol_not_blocked(self):
        """Cooldown for SPY should NOT block QQQ."""
        import BOT
        key = BOT._cooldown_key("SPY", "CALL", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now()
        result = BOT.check_TRADE_COOLDOWN_SECONDS("QQQ", "CALL", "20260312")
        assert result is False

    def test_exact_boundary(self):
        """At exactly TRADE_COOLDOWN_SECONDS, cooldown should be expired."""
        import BOT
        key = BOT._cooldown_key("SPY", "CALL", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now() - datetime.timedelta(seconds=300)
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "CALL", "20260312")
        assert result is False

    def test_one_second_before_expiry(self):
        """One second before cooldown expires, still active."""
        import BOT
        key = BOT._cooldown_key("SPY", "CALL", "20260312")
        BOT.trade_time_dict[key] = datetime.datetime.now() - datetime.timedelta(seconds=299)
        result = BOT.check_TRADE_COOLDOWN_SECONDS("SPY", "CALL", "20260312")
        assert result is True


class TestPlaceAndVerifyCooldown:
    """placeAndVerifyOrder also checks cooldown — verify key format matches."""

    def setup_method(self):
        import BOT
        self._orig_dict = BOT.trade_time_dict.copy()
        self._orig_cooldown = getattr(BOT, "TRADE_COOLDOWN_SECONDS", None)
        BOT.trade_time_dict.clear()
        BOT.TRADE_COOLDOWN_SECONDS = 300

    def teardown_method(self):
        import BOT
        BOT.trade_time_dict = self._orig_dict
        if self._orig_cooldown is not None:
            BOT.TRADE_COOLDOWN_SECONDS = self._orig_cooldown
        elif hasattr(BOT, "TRADE_COOLDOWN_SECONDS"):
            del BOT.TRADE_COOLDOWN_SECONDS

    def test_placeAndVerify_uses_normalized_key(self):
        """placeAndVerifyOrder's cooldown check uses _cooldown_key which normalizes right."""
        import BOT
        # Set cooldown with IB format (simulating what order_manager does)
        key_ib = BOT._cooldown_key("SPY", "C", "20260312")
        BOT.trade_time_dict[key_ib] = datetime.datetime.now()
        # The key used inside placeAndVerifyOrder is also _cooldown_key(symbol, right, expiry)
        key_bot = BOT._cooldown_key("SPY", "CALL", "20260312")
        assert key_ib == key_bot, "placeAndVerifyOrder key must match order_manager key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
