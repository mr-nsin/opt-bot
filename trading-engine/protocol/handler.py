"""
JSON-RPC message handler.
Reads requests from stdin, dispatches to the trading engine, sends responses.
"""

import os
import sys
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Any, Optional

from protocol.emitter import send_response, emit_log, emit_error
from protocol import messages

# Bounded pool avoids thread exhaustion if Rust spams concurrent RPCs (e.g. rapid UI actions).
_DEFAULT_RPC_WORKERS = 8
_ENV_RPC_WORKERS = "QUANTDRIFT_RPC_MAX_WORKERS"


def _rpc_max_workers() -> int:
    raw = os.environ.get(_ENV_RPC_WORKERS, "").strip()
    if not raw:
        return _DEFAULT_RPC_WORKERS
    try:
        n = int(raw, 10)
        return max(1, min(32, n))
    except ValueError:
        return _DEFAULT_RPC_WORKERS


class MessageHandler:
    """Handle incoming JSON-RPC messages from the Rust host."""

    def __init__(self, max_workers: Optional[int] = None):
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        workers = max_workers if max_workers is not None else _rpc_max_workers()
        self._executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="jsonrpc",
        )

    def register(self, method: str, handler: Callable):
        """Register a handler for a specific method."""
        self._handlers[method] = handler

    def start(self):
        """Start the message loop in a separate thread."""
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the message loop and release the RPC thread pool."""
        self._running = False
        try:
            # wait=False: do not block shutdown; cancel pending tasks not yet running (3.9+)
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                self._executor.shutdown(wait=False)
        except Exception:
            pass

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

            # Bounded pool: same non-blocking stdin loop, without unbounded thread creation
            self._executor.submit(self._execute_handler, request_id, method, handler, params)

    def _execute_handler(self, request_id: str, method: str, handler: Callable, params: dict):
        """Execute a handler and send the response."""
        try:
            result = handler(params)
            send_response(request_id, result=result)
            if method == messages.STOP_TRADING:
                os._exit(0)
        except Exception as e:
            emit_error(f"Handler error for {method}: {e}")
            send_response(request_id, error=str(e))
            if method == messages.STOP_TRADING:
                os._exit(1)
