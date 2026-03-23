"""
Append-only audit log for **opening** (entry) orders.

**File path:** ``<OPT_BOT project root>/logs/trade_open_context.jsonl``

Writes are **asynchronous**: records are deep-copied and queued; a daemon thread
flushes JSON Lines so order placement never waits on disk I/O.
"""

from __future__ import annotations

import copy
import json
import logging
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

_audit_logger = logging.getLogger("trade_placement_audit")

_AUDIT_PATH = Path(__file__).resolve().parent / "logs" / "trade_open_context.jsonl"
_queue = queue.Queue()
_writer_lock = threading.Lock()
_writer_started = False


def _write_record_sync(rec: Dict[str, Any]) -> None:
    _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if "ts_utc" not in rec:
        rec["ts_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
    with open(_AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()


def _writer_loop() -> None:
    while True:
        item = _queue.get()
        try:
            if item is None:
                break
            _write_record_sync(item)
        except Exception as e:
            _audit_logger.warning("trade_open_context writer failed: %s", e, exc_info=False)
        finally:
            _queue.task_done()


def _ensure_writer_thread() -> None:
    global _writer_started
    with _writer_lock:
        if not _writer_started:
            t = threading.Thread(
                target=_writer_loop,
                name="trade-open-context-audit-writer",
                daemon=True,
            )
            t.start()
            _writer_started = True


def log_open_trade_context(record: Dict[str, Any]) -> None:
    """
    Queue a full audit record for background write (non-blocking for trading thread).
    Falls back to no-op on unexpected errors; never raises to caller.
    """
    try:
        _ensure_writer_thread()
        _queue.put(copy.deepcopy(record))
    except Exception as e:
        _audit_logger.warning("trade_open_context enqueue failed: %s", e, exc_info=False)


def flush_audit_queue(timeout_sec: float = 5.0) -> None:
    """Optional: wait until queued audit lines are written (e.g. tests / shutdown)."""
    try:
        _queue.join()
    except Exception:
        pass
