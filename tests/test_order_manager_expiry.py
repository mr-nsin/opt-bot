"""Regression tests for ISSUES_ROADMAP P1 expiry matching in OrderManager."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from common import OptionOrder
from order_manager import OrderManager


class TestOrderManagerExpiry(unittest.TestCase):
    def setUp(self):
        self.om = OrderManager(MagicMock())

    def test_norm_expiry_iso_date(self):
        self.assertEqual(self.om._norm_expiry("2026-03-06"), "20260306")

    def test_norm_expiry_iso_datetime(self):
        self.assertEqual(self.om._norm_expiry("2026-03-06T14:30:00"), "20260306")

    def test_expiry_equivalent_dashed_vs_compact(self):
        self.assertTrue(self.om._expiry_equivalent("2026-03-21", "20260321"))
        self.assertTrue(self.om._expiry_equivalent("20260321", "2026-03-21"))

    def test_expiry_equivalent_yyyymm_vs_yyyymmdd_same_month(self):
        self.assertTrue(self.om._expiry_equivalent("202503", "20250321"))
        self.assertTrue(self.om._expiry_equivalent("20250321", "202503"))

    def test_expiry_equivalent_mismatch(self):
        self.assertFalse(self.om._expiry_equivalent("20250320", "20250321"))

    def test_find_entry_order_expiry_formats(self):
        o = OptionOrder(
            id=1,
            symbol="SPY",
            expiration="2026-03-13",
            strike=500.0,
            right="C",
        )
        key = self.om._option_key(o)
        self.om.entry_orders_cache[key] = o
        found = self.om._find_entry_order(
            "SPY", strike=500.0, right="C", expiry="20260313"
        )
        self.assertIsNotNone(found)
        self.assertEqual(found.id, 1)


if __name__ == "__main__":
    unittest.main()
