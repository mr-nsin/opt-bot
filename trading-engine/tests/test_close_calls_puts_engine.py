"""TradingEngine.close_calls / close_puts delegate to OrderManager."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.trading_engine import TradingEngine  # noqa: E402


class CloseCallsPutsEngineTests(unittest.TestCase):
    def test_close_calls_delegates(self):
        eng = TradingEngine()
        eng._order_mgr = MagicMock()
        out = eng.close_calls()
        self.assertEqual(out.get("status"), "close_calls_requested")
        eng._order_mgr.close_calls_positions.assert_called_once()

    def test_close_puts_delegates(self):
        eng = TradingEngine()
        eng._order_mgr = MagicMock()
        out = eng.close_puts()
        self.assertEqual(out.get("status"), "close_puts_requested")
        eng._order_mgr.close_puts_positions.assert_called_once()


if __name__ == "__main__":
    unittest.main()
