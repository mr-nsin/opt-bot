"""JSON-RPC handler uses a bounded ThreadPoolExecutor instead of unbounded threads."""

import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from protocol import handler as handler_mod  # noqa: E402
from protocol.handler import MessageHandler, _rpc_max_workers  # noqa: E402


class MessageHandlerRpcPoolTests(unittest.TestCase):
    def test_executor_is_thread_pool_with_bounded_workers(self):
        h = MessageHandler(max_workers=4)
        self.assertIsInstance(h._executor, ThreadPoolExecutor)
        self.assertEqual(h._executor._max_workers, 4)
        h.stop()

    def test_env_clamps_rpc_workers(self):
        with patch.dict(os.environ, {"QUANTDRIFT_RPC_MAX_WORKERS": "99"}):
            self.assertEqual(_rpc_max_workers(), 32)
        with patch.dict(os.environ, {"QUANTDRIFT_RPC_MAX_WORKERS": "0"}):
            self.assertEqual(_rpc_max_workers(), 1)
        with patch.dict(os.environ, {"QUANTDRIFT_RPC_MAX_WORKERS": "not-a-number"}):
            self.assertEqual(_rpc_max_workers(), handler_mod._DEFAULT_RPC_WORKERS)


if __name__ == "__main__":
    unittest.main()
