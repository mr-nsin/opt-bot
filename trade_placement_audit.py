"""
Append-only audit log for **opening** (entry) orders.

**File path:** same directory as loguru ``bot_*.log`` — :func:`common.get_logs_directory` /
``trade_open_context.jsonl`` (e.g. ``~/QuantDrift/logs`` when the sidecar is frozen, or
``trading-engine/logs`` / repo ``logs/`` in dev). Not next to this module (that breaks PyInstaller).

Writes are **asynchronous**: records are deep-copied and queued; a daemon thread
flushes JSON Lines so order placement never waits on disk I/O.

Each line is one JSON object. Typical ``open_order_placed`` record includes:

- **Identity:** ``event``, ``ts_utc``, ``order_id``, ``symbol``, ``expiry``, ``strike``, ``right``
- **Order:** ``action``, ``quantity``, ``order_type``, ``limit_price``
- **Risk targets:** ``take_profit_price``, ``stop_loss_price``, ``max_tp_trailing_cap``,
  ``min_sl_floor``, ``underlying_atr``
- **placement_context:** merged **signal** block (``_signal_entry_context``: decision_path,
  delta/volume thresholds, EMAs, ``atr``, ``config_snapshot``, algo/signal audits) plus
  **execution** block from ``takeTrade`` (bid/ask/last, ``trade_price``, TP/SL, ATR distances,
  ``option_tp_sl_*``, qty, DTE, etc.)

Call :func:`flush_audit_queue` after tests or before exit if you need every line on disk.
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

_queue = queue.Queue()
_writer_lock = threading.Lock()
_writer_started = False


def _resolve_audit_path() -> Path:
    """Align with loguru bot_*.log: frozen sidecar → ~/QuantDrift/logs; dev → trading-engine or repo logs/."""
    try:
        from common import get_logs_directory

        return Path(get_logs_directory()) / "trade_open_context.jsonl"
    except Exception:
        return Path(__file__).resolve().parent / "logs" / "trade_open_context.jsonl"


def _write_record_sync(rec: Dict[str, Any]) -> None:
    path = _resolve_audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if "ts_utc" not in rec:
        rec["ts_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
    with open(path, "a", encoding="utf-8") as f:
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
