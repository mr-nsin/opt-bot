"""Regression: per-row Close must pass expiry so OrderManager disambiguates contracts."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.trading_engine import TradingEngine  # noqa: E402


class ClosePositionForwardingTests(unittest.TestCase):
    def test_close_position_forwards_expiry_to_order_manager(self):
        engine = TradingEngine()
        engine._order_mgr = MagicMock()
        engine.close_position(
            {
                "symbol": "SPY",
                "strike": 580.0,
                "right": "C",
                "expiry": "20260418",
            }
        )
        engine._order_mgr.close_position_by_symbol.assert_called_once_with(
            "SPY", strike=580.0, right="C", expiry="20260418"
        )

    def test_close_position_omitted_expiry_passes_none(self):
        engine = TradingEngine()
        engine._order_mgr = MagicMock()
        engine.close_position({"symbol": "AAPL", "strike": 230.0, "right": "P"})
        engine._order_mgr.close_position_by_symbol.assert_called_once_with(
            "AAPL", strike=230.0, right="P", expiry=None
        )


if __name__ == "__main__":
    unittest.main()
