"""get_positions() must iterate TWS positions via get_all_positions() when available (locked snapshot)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.trading_engine import TradingEngine  # noqa: E402


class GetPositionsIterationTests(unittest.TestCase):
    def test_prefers_get_all_positions_over_raw_positions_dict(self):
        engine = TradingEngine()
        mock_client = MagicMock()
        mock_pos = MagicMock()
        mock_pos.position = 1
        mock_pos.account = "DU123"
        mock_pos.avg_cost = 250.0
        mock_pos.symbol = "SPY"
        mock_pos.strike = 580.0
        mock_pos.right = "C"
        mock_pos.expiry = "20260418"

        mock_client.get_all_positions.return_value = [mock_pos]
        engine._client = mock_client
        engine._order_mgr = None
        engine.config = MagicMock()
        engine.config.account_id = ""

        out = engine.get_positions()
        mock_client.get_all_positions.assert_called_once()
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["symbol"], "SPY")


if __name__ == "__main__":
    unittest.main()
