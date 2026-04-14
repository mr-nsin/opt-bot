"""Canonical OPT ticker keys must match across subscribe, get_data, and get_options_data."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common import option_ticker_key


def test_strike_int_float_same_key():
    assert option_ticker_key("TSLA", "20260417", "P", 340) == option_ticker_key(
        "TSLA", "20260417", "P", 340.0
    )


def test_put_aliases():
    assert option_ticker_key("QQQ", "20260408", "PUT", 584.0) == option_ticker_key(
        "QQQ", "20260408", "P", 584.0
    )


def test_expiry_dashed():
    assert option_ticker_key("TSLA", "2026-04-17", "P", 340.0) == "TSLA20260417P340.0"
