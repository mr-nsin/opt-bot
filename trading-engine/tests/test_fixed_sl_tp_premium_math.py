"""Fixed % SL/TP on option premium (BOT.takeTrade path)."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sl_tp_helpers import compute_fixed_percent_sl_tp, parse_sl_tp_settings


def test_10pct_long_matches_entry_217():
    tp, sl = compute_fixed_percent_sl_tp(2.17, 10.0, 10.0, is_long=True)
    assert abs(tp - 2.39) < 0.02
    assert abs(sl - 1.95) < 0.02


def test_10pct_long_entry_190():
    tp, sl = compute_fixed_percent_sl_tp(1.90, 10.0, 10.0, is_long=True)
    assert abs(tp - 2.09) < 0.02
    assert abs(sl - 1.71) < 0.02


def test_parse_fixed_percent_from_config_keys():
    mode, tp, sl, trail = parse_sl_tp_settings(
        {
            "sl_tp_mode": "fixed_percent",
            "fixed_take_profit_percent": 10,
            "fixed_stop_loss_percent": 10,
            "trailing_take_profit": False,
        }
    )
    assert mode == "fixed_percent"
    assert tp == 10.0
    assert sl == 10.0
    assert trail is False
