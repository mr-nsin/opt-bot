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


def emit_log(message: str, level: str = "INFO", category: str = "trading"):
    """Emit a log message to the host. Only INFO, WARN, ERROR are sent to the UI; DEBUG is skipped."""
    if level not in _UI_LOG_LEVELS:
        return
    send_event("log_message", {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "category": category,
        "message": message,
    })


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
