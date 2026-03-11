#!/usr/bin/env python3
"""
QuantDrift Trading Engine Sidecar
Entry point for the Python trading engine, communicating with the Rust host
via JSON-RPC over stdio (stdin/stdout).

Protocol:
  - Reads JSON requests from stdin (one per line)
  - Writes JSON responses/events to stdout (one per line)
  - Diagnostic/error logs go to stderr
"""

import sys
import os
import signal
import time

# Ensure loguru is bundled (used by common.py for logging)
import loguru  # noqa: F401

# When frozen (PyInstaller onefile), add-data files (BOT.py, common.py, etc.) are in sys._MEIPASS.
# Use that as ROOT_DIR so "import BOT" / "from common import ..." work like on Mac.
if getattr(sys, "frozen", False):
    ROOT_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

SIDECAR_DIR = os.path.dirname(os.path.abspath(__file__))
if SIDECAR_DIR not in sys.path:
    sys.path.insert(0, SIDECAR_DIR)

from protocol.handler import MessageHandler
from protocol.emitter import emit_log, emit_engine_status, send_response
from protocol import messages
from engine.trading_engine import TradingEngine


def main():
    """Main entry point for the trading engine sidecar."""

    # Redirect print statements to stderr so they don't interfere with protocol
    class StderrWriter:
        def write(self, text):
            if text.strip():
                sys.stderr.write(text)
                sys.stderr.flush()
        def flush(self):
            sys.stderr.flush()

    # Keep original stdout for protocol, redirect prints to stderr
    original_stdout = sys.stdout
    # Uncomment below to redirect prints:
    # sys.stdout = StderrWriter()

    # Initialize engine
    engine = TradingEngine()

    # Setup message handler
    handler = MessageHandler()

    # Register command handlers
    handler.register(messages.START_TRADING, lambda params: engine.start(params.get("config", {})))
    handler.register(messages.STOP_TRADING, lambda params: engine.stop())
    handler.register(messages.EMERGENCY_STOP, lambda params: engine.emergency_stop(params or {}))
    handler.register(messages.GET_STATUS, lambda params: engine.get_status())
    handler.register(messages.GET_POSITIONS, lambda params: engine.get_positions())
    handler.register(messages.CLOSE_POSITION, lambda params: engine.close_position(params))
    handler.register(messages.CLOSE_ALL, lambda params: engine.close_all())
    handler.register(messages.CLOSE_CALLS, lambda params: engine.close_calls())
    handler.register(messages.CLOSE_PUTS, lambda params: engine.close_puts())
    handler.register(messages.UPDATE_CONFIG, lambda params: engine.update_config(params))
    handler.register(messages.PING, lambda params: {"pong": True, "timestamp": time.time()})
    handler.register(messages.SIMULATE_DEMO, lambda params: engine.simulate_demo(params))

    # Signal handlers for graceful shutdown
    def shutdown(signum, frame):
        emit_log("Shutdown signal received", "INFO", "system")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Emit startup event
    emit_engine_status("Idle", connected=False)
    emit_log("QuantDrift Trading Engine v1.0.0 started", "INFO", "system")

    # Start the message handler (blocks on stdin)
    handler.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        engine.stop()
        emit_log("Trading engine shutting down", "INFO", "system")


if __name__ == "__main__":
    main()
