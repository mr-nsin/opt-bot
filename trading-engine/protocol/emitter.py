"""
Event emitter for sending messages back to the Rust host via stdout.
All output to stdout is JSON-formatted, one message per line.
"""

import sys
import json
import threading
from datetime import datetime
from typing import Any, Dict


_write_lock = threading.Lock()


def _send(message: dict):
    """Thread-safe write to stdout"""
    with _write_lock:
        try:
            line = json.dumps(message, default=str)
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
        except Exception as e:
            # Write error to stderr (won't interfere with protocol)
            sys.stderr.write(f"Emitter error: {e}\n")
            sys.stderr.flush()


def send_response(request_id: str, result: Any = None, error: str = None):
    """Send a response to a specific request"""
    msg = {"id": request_id}
    if error:
        msg["error"] = {"code": -1, "message": error}
    else:
        msg["result"] = result
    _send(msg)


def send_event(event_type: str, data: Dict[str, Any]):
    """Send an unsolicited event to the host"""
    _send({"event": event_type, "data": data})


def emit_tick(symbol: str, last: float, bid: float, ask: float, **kwargs):
    send_event("tick_update", {
        "symbol": symbol,
        "last": last,
        "bid": bid,
        "ask": ask,
        **kwargs,
    })


def emit_position(position_data: dict):
    send_event("position_update", position_data)


def emit_pnl(daily_pnl: float, unrealized: float, realized: float):
    send_event("pnl_update", {
        "daily_pnl": daily_pnl,
        "unrealized_pnl": unrealized,
        "realized_pnl": realized,
    })


def emit_account_metrics(metrics: Dict[str, Any]):
    """Emit IBKR account summary metrics (NetLiquidation, BuyingPower, etc.)."""
    send_event("account_metrics", metrics)


def emit_signal(symbol: str, signal_type: str, strike: float, price: float, reason: str):
    send_event("signal_detected", {
        "symbol": symbol,
        "signal_type": signal_type,
        "strike": strike,
        "price": price,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    })


def emit_trade_executed(order_data: dict):
    send_event("trade_executed", order_data)


def emit_trade_closed(order_data: dict):
    send_event("trade_closed", order_data)


def emit_order_update(order_id: int, status: str, symbol: str, **kwargs):
    send_event("order_update", {
        "order_id": order_id,
        "status": status,
        "symbol": symbol,
        **kwargs,
    })


# Log levels that are sent to the UI; DEBUG is omitted to keep UI logs informational only
_UI_LOG_LEVELS = frozenset({"INFO", "WARN", "ERROR"})

# Batched log emission: buffer logs and flush every 150ms (~80% less IPC)
_LOG_BUFFER: list = []
_LOG_BUFFER_LOCK = threading.Lock()
_LOG_FLUSH_INTERVAL_SEC = 0.15
_log_flush_timer: threading.Timer | None = None


def _flush_log_buffer():
    """Flush buffered logs as a single batched event."""
    global _log_flush_timer
    with _LOG_BUFFER_LOCK:
        if not _LOG_BUFFER:
            _log_flush_timer = None
            return
        entries = list(_LOG_BUFFER)
        _LOG_BUFFER.clear()
        _log_flush_timer = None
    if entries:
        send_event("log_message", {"entries": entries})


def flush_pending_logs():
    """Send any buffered log lines to stdout immediately (e.g. before os._exit skips atexit)."""
    global _log_flush_timer
    t = None
    with _LOG_BUFFER_LOCK:
        t = _log_flush_timer
        _log_flush_timer = None
    if t is not None:
        try:
            t.cancel()
        except Exception:
            pass
    _flush_log_buffer()


_mirror_to_loguru_warned = False


def _mirror_emit_to_loguru(message: str, level: str, category: str) -> None:
    """Duplicate UI logs to loguru file (common.setup_logger) — engine otherwise only used emit_log/stdout."""
    global _mirror_to_loguru_warned
    try:
        from common import logger
    except Exception as e:
        if not _mirror_to_loguru_warned:
            _mirror_to_loguru_warned = True
            sys.stderr.write(
                f"[emitter] log file mirror disabled (common import failed): {e}\n"
            )
            sys.stderr.flush()
        return
    text = f"[{category}] {message}"
    lv = (level or "INFO").upper()
    if lv == "ERROR":
        logger.error(text)
    elif lv == "WARN":
        logger.warning(text)
    else:
        logger.info(text)


def _schedule_log_flush():
    """Schedule a flush if not already scheduled."""
    global _log_flush_timer
    with _LOG_BUFFER_LOCK:
        if _log_flush_timer is not None:
            return
        _log_flush_timer = threading.Timer(_LOG_FLUSH_INTERVAL_SEC, _flush_log_buffer)
        _log_flush_timer.daemon = True
        _log_flush_timer.start()


def emit_log(message: str, level: str = "INFO", category: str = "trading"):
    """Emit a log message to the host. Only INFO, WARN, ERROR are sent to the UI; DEBUG is skipped.
    Logs are batched and flushed every 150ms to reduce IPC volume."""
    if level not in _UI_LOG_LEVELS:
        return
    entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "category": category,
        "message": message,
    }
    with _LOG_BUFFER_LOCK:
        _LOG_BUFFER.append(entry)
    _mirror_emit_to_loguru(message, level, category)
    _schedule_log_flush()


def emit_engine_status(status: str, connected: bool = False, **kwargs):
    send_event("engine_status", {
        "status": status,
        "connected": connected,
        **kwargs,
    })


def emit_connection_status(connected: bool, message: str = ""):
    send_event("connection_status", {
        "connected": connected,
        "message": message,
    })


def emit_error(message: str, code: int = -1):
    send_event("error", {
        "code": code,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    })


def emit_data_status(
    connected: bool,
    data_feed_started: bool,
    symbols: list,
    queue_size: int,
    tick_count: int,
    stock_ticks: list,
    bar_count: int,
):
    """Emit a periodic snapshot of what data is being fetched (every ~10s)."""
    send_event("data_status", {
        "timestamp": datetime.now().isoformat(),
        "connected": connected,
        "data_feed_started": data_feed_started,
        "symbols": symbols,
        "event_queue_size": queue_size,
        "tick_subscriptions": tick_count,
        "stock_ticks_sample": stock_ticks,
        "history_bars_count": bar_count,
    })


def emit_signal_data(signals: list, system_started_at: str):
    """
    Emit signal DataFrame (list of rows) for current and previous candles per stock.
    Each row: symbol, date, open, high, low, close, volume, signal.
    system_started_at: ISO timestamp when the system/trading engine started.
    """
    send_event("signal_data", {
        "signals": signals,
        "system_started_at": system_started_at,
        "timestamp": datetime.now().isoformat(),
    })
