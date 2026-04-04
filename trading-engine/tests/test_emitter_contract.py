"""Contract: event names the Rust host must forward to trading:* for the UI."""

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from protocol import emitter  # noqa: E402


class EmitterContractTests(unittest.TestCase):
    def test_emit_position_uses_position_update_event(self):
        """Demo and live ticks use this; Rust must forward trading:position_update."""
        captured = []

        def fake_send(message: dict):
            captured.append(message)

        real_send = emitter._send
        emitter._send = fake_send  # type: ignore[attr-defined]
        try:
            emitter.emit_position({"symbol": "SPY", "quantity": 1})
        finally:
            emitter._send = real_send  # type: ignore[attr-defined]

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["event"], "position_update")
        self.assertIn("data", captured[0])

    def test_emit_positions_snapshot_shape(self):
        captured = []

        def fake_send(message: dict):
            captured.append(message)

        real_send = emitter._send
        emitter._send = fake_send  # type: ignore[attr-defined]
        try:
            emitter.emit_positions_snapshot([{"symbol": "X", "quantity": 1}])
        finally:
            emitter._send = real_send  # type: ignore[attr-defined]

        self.assertEqual(captured[0]["event"], "positions_snapshot")
        self.assertEqual(captured[0]["data"]["positions"][0]["symbol"], "X")


if __name__ == "__main__":
    unittest.main()
