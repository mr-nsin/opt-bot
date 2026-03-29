"""
JSON-RPC message handler.
Reads requests from stdin, dispatches to the trading engine, sends responses.
"""

import os
import sys
import json
import threading
from typing import Callable, Dict, Any

from protocol.emitter import send_response, emit_log, emit_error, flush_pending_logs
from protocol import messages


class MessageHandler:
    """Handle incoming JSON-RPC messages from the Rust host."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._running = False

    def register(self, method: str, handler: Callable):
        """Register a handler for a specific method."""
        self._handlers[method] = handler

    def start(self):
        """Start the message loop in a separate thread."""
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the message loop."""
        self._running = False

    def _message_loop(self):
        """Main loop: read JSON messages from stdin, dispatch to handlers."""
        emit_log("Message handler started", "INFO", "system")

        for line in sys.stdin:
            if not self._running:
                break

            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                emit_error(f"Invalid JSON received: {e}")
                continue

            request_id = request.get("id", "unknown")
            method = request.get("method", "")
            params = request.get("params", {})

            if method == messages.STOP_TRADING:
                emit_log("Received STOP_TRADING — stopping engine and exiting", "INFO", "system")
            emit_log(f"Received request: {method} (id={request_id})", "DEBUG", "protocol")

            handler = self._handlers.get(method)
            if not handler:
                send_response(request_id, error=f"Unknown method: {method}")
                continue

            # Execute handler in a separate thread to not block the message loop
            threading.Thread(
                target=self._execute_handler,
                args=(request_id, method, handler, params),
                daemon=True,
            ).start()

    def _execute_handler(self, request_id: str, method: str, handler: Callable, params: dict):
        """Execute a handler and send the response."""
        try:
            result = handler(params)
            send_response(request_id, result=result)
            if method == messages.STOP_TRADING:
                flush_pending_logs()
                os._exit(0)
        except Exception as e:
            emit_error(f"Handler error for {method}: {e}")
            send_response(request_id, error=str(e))
            if method == messages.STOP_TRADING:
                flush_pending_logs()
                os._exit(1)
