"""Expiry normalization must match IB/tick cache keys (YYYYMMDD, no dashes)."""

import sys
import os

# trading-engine/tests -> parents[1] = trading-engine, parents[2] = repo root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common import normalize_option_expiry_for_ticker


def test_normalize_dashed_date():
    assert normalize_option_expiry_for_ticker("2026-03-28") == "20260328"


def test_normalize_compact():
    assert normalize_option_expiry_for_ticker("20260328") == "20260328"


def test_normalize_empty():
    assert normalize_option_expiry_for_ticker("") == ""


def test_normalize_slashes():
    assert normalize_option_expiry_for_ticker("2026/03/28") == "20260328"
