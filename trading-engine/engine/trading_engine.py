"""
TradingEngine: Class-based refactoring of BOT.py.
Wraps the existing trading logic and provides a clean interface for the sidecar protocol.

This module bridges the legacy BOT.py globals-based approach into a class that
the JSON-RPC handler can control. It imports and delegates to the existing modules
(tws_api_client, order_manager, data_access, Indicators) to preserve proven logic.
"""

import os
import sys
import time
import json
import threading
from queue import Queue
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Add parent directories to path for importing existing modules
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from protocol.emitter import (
    emit_log, emit_engine_status, emit_connection_status,
    emit_pnl, emit_position, emit_signal, emit_trade_executed,
    emit_trade_closed, emit_order_update, emit_error,
    emit_data_status, emit_account_metrics, emit_signal_data,
)
from engine.models import TradingConfig


class TradingEngine:
    """
    Main trading engine that wraps the existing BOT.py logic.
    Controlled via the JSON-RPC protocol from the Rust host.
    """

    def __init__(self):
        self.config: Optional[TradingConfig] = None
        self.running = False
        self.connected = False
        self._client = None
        self._order_mgr = None
        self._db = None
        self._event_queue = None
        self._engine_thread: Optional[threading.Thread] = None
        self._last_tws_reconnect_attempt: float = 0
        self._tws_reconnect_interval_sec: float = 10.0
        self._data_feed_started: bool = False
        self._event_processor_threads: list = []
        self._last_data_status_time: float = 0
        self._data_status_interval_sec: float = 5.0
        self._last_account_metrics_time: float = 0
        self._account_metrics_interval_sec: float = 5.0
        self._account_metrics_first_emit_done: bool = False
        self._last_positions_time: float = 0
        self._positions_interval_sec: float = 0.25  # Overridden from config ui.positions_update_interval_ms on load
        self._last_signal_heartbeat_time: float = 0
        self._signal_heartbeat_interval_sec: float = 30.0  # Every 30s log that engine is scanning
        self._last_pnl_emit_time: float = 0
        self._pnl_throttle_sec: float = 1.0  # Align with UI throttle (~1/s); cuts IPC vs 50ms engine loop
        self._close_all_thread: Optional[threading.Thread] = None

    @contextmanager
    def _cwd_for_first_bot_import(self):
        """BOT.py reads config.json at module import time. Sidecar CWD is often not the project root.
        If TWS never connected, ``_start_data_feed_and_strategies`` never ran and BOT was never imported;
        a later ``import BOT`` (e.g. Stop Trading) would then fail with [Errno 2] config.json.
        Temporarily chdir and ensure config.json exists for that first import only."""
        import tempfile

        orig = os.getcwd()
        frozen = getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")
        try:
            if frozen:
                d = tempfile.mkdtemp(prefix="optbot_botimport_")
                path = os.path.join(d, "config.json")
                if self.config:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(self.config.to_bot_config_dict(), f, indent=2)
                else:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump({}, f)
                os.chdir(d)
            else:
                d = PARENT_DIR if os.path.isdir(PARENT_DIR) else orig
                if self.config:
                    path = os.path.join(d, "config.json")
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(self.config.to_bot_config_dict(), f, indent=2)
                os.chdir(d)
            yield
        finally:
            try:
                os.chdir(orig)
            except Exception:
                pass

    def _get_bot_module(self):
        """Return the BOT module, ensuring config.json is visible on first import (see _cwd_for_first_bot_import)."""
        mod = sys.modules.get("BOT")
        if mod is not None:
            return mod
        with self._cwd_for_first_bot_import():
            import BOT as _BOT

            return _BOT

    def start(self, config_data: dict) -> dict:
        """Start the trading engine with the given configuration."""
        if self.running:
            return {"status": "already_running"}

        try:
            # Parse configuration (symbols come from UI – sidecar subscribes to these)
            self.config = TradingConfig.from_dict(config_data)
            self._apply_positions_emit_interval()
            sym_list = list(self.config.stock_list_to_trade.keys()) if self.config.stock_list_to_trade else []
            emit_log(f"Configuration loaded: {len(sym_list)} symbols from UI: {', '.join(sym_list) or '(none)'}")

            # Initialize components
            self._event_queue = Queue()
            self._init_database()
            self._init_order_manager()
            self._init_tws_client()

            # Start engine in background thread
            self.running = True
            self._engine_thread = threading.Thread(target=self._run_engine, daemon=True)
            self._engine_thread.start()

            emit_engine_status("Running", connected=self.connected)
            emit_log("Trading engine started successfully", "INFO", "system")

            return {"status": "started"}

        except Exception as e:
            # Provide a very clear, user-friendly error message for missing IB API
            msg = str(e)
            if "No module named 'ibapi'" in msg:
                human_msg = (
                    "Python environment is missing the Interactive Brokers API package 'ibapi'. "
                    "Please install trading-engine dependencies using Python 3.13 (e.g. py -3.13) "
                    "in the 'trading-engine/.venv' folder, then restart the app."
                )
                emit_log(human_msg, "ERROR", "system")
                emit_error(human_msg)
            else:
                emit_error(f"Failed to start trading engine: {msg}")

            # Ensure engine is marked idle so the UI doesn't think it's running
            self.running = False
            emit_engine_status("Idle", connected=False)
            return {"status": "error", "reason": msg}

    def _cancel_orders_only(self):
        """Cancel all open orders. Does NOT close positions (used by Stop Trading)."""
        try:
            BOT = self._get_bot_module()
            if self._client and self._client.isConnected():
                emit_log("Cancelling all open orders...", "INFO", "system")
                BOT.cancel_all_orders()
                emit_log("All orders cancelled (positions left open)", "INFO", "system")
            else:
                emit_log("TWS not connected — cannot cancel orders", "WARN", "system")
        except Exception as e:
            emit_log(f"Error cancelling orders: {e}", "ERROR", "system")

    def _close_all_orders_and_positions(self):
        """Cancel all open orders and close all positions (used by Emergency Stop).
        Uses getAndBuyAfterMarketEnd which closes ALL TWS positions (each in its own try/except so one failure does not abort the rest)."""
        try:
            BOT = self._get_bot_module()
            if self._client and self._client.isConnected():
                emit_log("Emergency stop: cancelling all open orders...", "INFO", "system")
                BOT.cancel_all_orders()
                emit_log("Emergency stop: closing ALL TWS positions at market (one-by-one, failures logged)...", "INFO", "system")
                buf_sec = getattr(self.config, "emergency_close_buffer_seconds", 5)
                BOT.getAndBuyAfterMarketEnd(buffer_seconds=buf_sec)
                emit_log("Emergency stop: orders cancelled, close orders placed for all positions", "INFO", "system")
            else:
                emit_log("TWS not connected — cannot close orders/positions", "WARN", "system")
        except Exception as e:
            emit_log(f"Error closing orders/positions: {e}", "ERROR", "system")

    def stop(self) -> dict:
        """Gracefully stop the trading engine and fully clean up so restart works."""
        if not self.running:
            return {"status": "not_running"}

        emit_log("Stopping trading engine...", "INFO", "system")
        self.running = False

        # Signal BOT globals to stop trading loops
        try:
            BOT = self._get_bot_module()
            BOT.STOP_TRADING = True
        except Exception:
            pass

        # Cancel orders only (do NOT close positions — user may close manually)
        self._cancel_orders_only()

        # Wait for engine thread to exit (it checks self.running each iteration)
        if self._engine_thread and self._engine_thread.is_alive():
            try:
                self._engine_thread.join(timeout=5)
            except Exception:
                pass
        self._engine_thread = None

        # Stop event processor threads (BOT strategy threads)
        for t in self._event_processor_threads:
            try:
                if t.is_alive():
                    t.join(timeout=2)
            except Exception:
                pass
        self._event_processor_threads = []

        # Disconnect TWS and destroy client so next start gets a fresh connection
        if self._client:
            try:
                if hasattr(self._client, 'disconnect'):
                    self._client.disconnect()
            except Exception as e:
                emit_log(f"Error disconnecting TWS: {e}", "WARN", "system")
            time.sleep(0.5)
            self._client = None

        # Reset all state so start() can reinitialize cleanly
        self.connected = False
        self._data_feed_started = False
        self._order_mgr = None
        self._db = None
        self._event_queue = None

        emit_engine_status("Idle", connected=False)
        emit_log("Trading engine stopped", "INFO", "system")

        return {"status": "stopped"}

    def emergency_stop(self, params: dict = None) -> dict:
        """Emergency stop: close all orders/positions, then immediately halt.
        If params.reason is provided, emit only that one message (e.g. license invalidation).
        Otherwise emit a single default message."""
        params = params or {}
        reason = params.get("reason") if isinstance(params.get("reason"), str) else None
        self.running = False

        # Signal BOT globals to stop trading loops
        try:
            BOT = self._get_bot_module()
            BOT.STOP_TRADING = True
            BOT.CLOSE_ALL_ORDERS = True
        except Exception:
            pass

        # Close all orders and positions before disconnecting
        self._close_all_orders_and_positions()

        # Force disconnect and destroy client
        if self._client:
            try:
                self._client.disconnect()
            except:
                pass
            self._client = None

        self.connected = False
        self._data_feed_started = False
        self._event_processor_threads = []
        self._order_mgr = None
        self._db = None
        self._event_queue = None

        emit_engine_status("Idle", connected=False)
        # Only one log message: the reason if provided, else default
        msg = reason if reason else "Emergency stop — orders cancelled, positions closed"
        emit_log(msg, "ERROR", "system")
        return {"status": "emergency_stopped"}

    def get_status(self) -> dict:
        """Get current engine status."""
        return {
            "running": self.running,
            "connected": self.connected,
            "config_loaded": self.config is not None,
        }

    def get_positions(self) -> list:
        """Get current positions with live price and P&L from tick cache and order manager.
        Uses TWS client.positions first; falls back to order_manager.entry_orders_cache when
        TWS positions are empty but we have open trades (e.g. TWS sync delay or account mismatch).
        """
        if not self._client:
            return []

        positions = []
        account_filter = (self.config.account_id or "").strip() if self.config else ""
        if hasattr(self._client, 'positions'):
            for key, pos in list((self._client.positions or {}).items()):
                qty = getattr(pos, 'position', 0)
                if qty == 0:
                    continue
                # When account_id is configured, only show positions for that account
                pos_account = getattr(pos, 'account', None) or ""
                if account_filter and pos_account and pos_account != account_filter:
                    continue

                # avg_cost from TWS is per-share cost (for options: price * multiplier)
                avg_cost = getattr(pos, 'avg_cost', 0)
                avg_price = avg_cost / 100.0 if avg_cost > 1 else avg_cost

                # Try to get live price from order manager tick lookup, then client tick cache
                current_price = 0.0
                entry_order = None
                tick = None
                symbol = getattr(pos, 'symbol', str(key))
                strike = getattr(pos, 'strike', 0)
                right = getattr(pos, 'right', '')
                expiry = getattr(pos, 'expiry', '')

                if self._order_mgr:
                    entry_order = self._order_mgr._find_entry_order(symbol, strike=strike, right=right, expiry=expiry)
                    if entry_order:
                        # Fallback: use entry_order.average_price when TWS avg_cost is 0
                        if avg_price <= 0 and getattr(entry_order, 'average_price', 0) > 0:
                            avg_price = float(entry_order.average_price)
                        tick = self._order_mgr.order_id_tick_lookup.get(entry_order.id)
                        if tick and hasattr(tick, 'last') and tick.last > 0:
                            current_price = tick.last
                        elif tick and hasattr(tick, 'bid') and tick.bid > 0:
                            current_price = tick.bid

                # Fallback: client tick_cache (get_options_data) when order lookup has no tick
                if current_price <= 0 and hasattr(self._client, 'get_options_data'):
                    try:
                        r = str(right or "").upper()
                        r = "C" if r in ("C", "CALL") else "P" if r in ("P", "PUT") else (r[0] if r else "C")
                        tick = self._client.get_options_data(symbol, str(expiry), r, float(strike))
                        if tick and hasattr(tick, 'last') and tick.last > 0:
                            current_price = tick.last
                        elif tick and hasattr(tick, 'bid') and tick.bid > 0:
                            current_price = tick.bid
                    except Exception:
                        pass

                # Extract bid, ask, last for TP/SL logic display (matches order_manager check_take_profit/check_stop_loss)
                bid_val = float(getattr(tick, 'bid', -1) or -1) if tick else -1
                ask_val = float(getattr(tick, 'ask', -1) or -1) if tick else -1
                last_val = float(getattr(tick, 'last', -1) or -1) if tick else -1
                # Exit price used for TP/SL: bid when valid, else last (same as order_manager)
                exit_price_used = bid_val if bid_val > 0 else last_val if last_val > 0 else 0.0
                exit_price_source = "bid" if bid_val > 0 else "last" if last_val > 0 else ""

                pnl = (current_price - avg_price) * qty * 100 if current_price > 0 and avg_price > 0 else 0
                pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 and current_price > 0 else 0

                used_ib_pnl = False
                con_id_opt = int(getattr(pos, "con_id", 0) or 0)
                if con_id_opt and self._client and hasattr(self._client, "get_pnl_single_snapshot"):
                    ib_row = self._client.get_pnl_single_snapshot(con_id_opt)
                    if ib_row is not None and "unrealized" in ib_row:
                        pnl = float(ib_row["unrealized"])
                        cost_basis = avg_price * abs(qty) * 100 if avg_price > 0 and qty else 0
                        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                        used_ib_pnl = True
                        v = ib_row.get("value")
                        if v is not None and abs(qty) > 0:
                            implied = float(v) / (abs(qty) * 100.0)
                            if implied > 0:
                                current_price = implied

                pos_data = {
                    "symbol": symbol,
                    "strike": strike,
                    "right": right,
                    "expiry": expiry,
                    "quantity": qty,
                    "avg_price": round(avg_price, 4),
                    "current_price": round(current_price, 4),
                    "pnl": round(pnl, 2),
                    "pnl_percent": round(pnl_pct, 2),
                }
                if used_ib_pnl:
                    pos_data["pnl_source"] = "ib"
                # Include SL/TP from managed entry order so UI can display them
                if entry_order:
                    pos_data["stoploss_price"] = round(float(entry_order.stoploss_price or 0), 2)
                    pos_data["profit_price"] = round(float(entry_order.current_profit_price or entry_order.profit_price or 0), 2)
                    if getattr(entry_order, "profit_price", None) is not None and float(entry_order.profit_price or 0) > 0:
                        pos_data["initial_profit_price"] = round(float(entry_order.profit_price), 2)
                    sl_raw = float(entry_order.stoploss_price or 0)
                    floor_sl = getattr(entry_order, "min_sl_price", None)
                    is_long = (entry_order.order_side or "BUY").upper() == "BUY"
                    if is_long and floor_sl is not None:
                        pos_data["effective_stoploss_price"] = round(max(sl_raw, float(floor_sl)), 2)
                    elif sl_raw > 0:
                        pos_data["effective_stoploss_price"] = round(sl_raw, 2)
                        if getattr(entry_order, "profit_trigger", False):
                            pos_data["trailing_active"] = True
                        uatr = getattr(entry_order, "underlying_atr", None)
                        if uatr is not None:
                            pos_data["underlying_atr"] = round(float(uatr), 4)
                # Include bid/ask/last and exit logic for TP/SL transparency
                if bid_val not in (-1, None):
                    pos_data["bid"] = round(bid_val, 4)
                if ask_val not in (-1, None):
                    pos_data["ask"] = round(ask_val, 4)
                if last_val not in (-1, None):
                    pos_data["last"] = round(last_val, 4)
                if exit_price_used > 0:
                    pos_data["exit_price_used"] = round(exit_price_used, 4)
                    pos_data["exit_price_source"] = exit_price_source
                positions.append(pos_data)

        # Do NOT fallback to entry_orders_cache when TWS positions are empty.
        # TWS is the source of truth: if IBKR shows POS: 0, we show no positions.
        # The old fallback caused "ghost positions" (13 active when IBKR had 0) because
        # entry_orders_cache was not cleaned when positions closed via square-off or manual exit.

        # Deduplicate by (symbol, strike, right, expiry) — TWS can produce duplicates
        # when expiry format differs (e.g. 20260313 vs 2026-03-13) or multiple orders same option
        return self._deduplicate_positions(positions)

    def _deduplicate_positions(self, positions: list) -> list:
        """Deduplicate positions by (symbol, strike, right, expiry). Keep first; prefer one with current_price if duplicate."""
        if not positions:
            return []
        seen: dict[str, dict] = {}
        norm_exp = lambda e: (e or "").replace("-", "").replace(" ", "").strip()
        norm_right = lambda r: "C" if str(r or "").upper() in ("C", "CALL") else "P" if str(r or "").upper() in ("P", "PUT") else (str(r or "")[:1].upper() or "C")
        for p in positions:
            sym = str(p.get("symbol", "") or "").strip()
            strike = float(p.get("strike", 0) or 0)
            right = norm_right(p.get("right", ""))
            expiry = norm_exp(p.get("expiry", "") or "")
            key = f"{sym}_{strike:.4f}_{right}_{expiry}"
            if key in seen:
                # Duplicate: prefer the one with current_price > 0 for better P&L display
                prev = seen[key]
                if float(p.get("current_price", 0) or 0) > 0 and float(prev.get("current_price", 0) or 0) <= 0:
                    seen[key] = dict(p)
            else:
                seen[key] = dict(p)
        return list(seen.values())

    def simulate_demo(self, params: dict) -> dict:
        """Run a demo simulation that emits fake positions, trades, signals, and closes.
        Tests the full UI pipeline without needing TWS connection."""
        if self.running:
            return {"status": "error", "message": "Cannot run demo while trading engine is active"}
        demo_thread = threading.Thread(target=self._run_demo_simulation, daemon=True)
        demo_thread.start()
        return {"status": "demo_started"}

    def _run_demo_simulation(self):
        """Background thread that simulates a full trading cycle."""
        import random
        from datetime import datetime

        demo_symbols = [
            {"symbol": "AAPL", "strike": 230.0, "right": "C", "expiry": "20260306"},
            {"symbol": "TSLA", "strike": 350.0, "right": "P", "expiry": "20260306"},
            {"symbol": "SPY",  "strike": 580.0, "right": "C", "expiry": "20260306"},
        ]

        emit_log("DEMO: Starting simulation — 3 fake positions + trades", "INFO", "system")

        # Phase 1: Emit signals
        time.sleep(1)
        for s in demo_symbols:
            emit_signal(s["symbol"], s["right"], s["strike"], round(random.uniform(1.5, 5.0), 2),
                        f"DEMO SuperTrend flip → {s['right']}")
            emit_log(f"DEMO: Signal detected for {s['symbol']} {s['strike']}{s['right'][0]}", "INFO", "signal")
            time.sleep(0.5)

        # Phase 2: Emit trade_executed (entry fills)
        time.sleep(1)
        entries = {}
        for i, s in enumerate(demo_symbols):
            entry_price = round(random.uniform(1.5, 4.5), 2)
            qty = random.choice([1, 2, 3])
            trade_id = 10000 + i
            entries[s["symbol"]] = {"entry_price": entry_price, "qty": qty, "id": trade_id}
            emit_trade_executed({
                "id": trade_id,
                "symbol": s["symbol"],
                "right": s["right"],
                "strike": s["strike"],
                "expiry": s["expiry"],
                "side": "BUY",
                "quantity": qty,
                "entry_price": entry_price,
                "price": entry_price,
                "status": "open",
                "timestamp": datetime.now().isoformat(),
                "underlying_atr": round(1.2 + i * 0.15, 4),
            })
            emit_log(f"DEMO: ENTRY FILLED {s['symbol']} {s['strike']}{s['right'][0]} {qty}x @ ${entry_price:.2f}", "INFO", "order")
            time.sleep(0.5)

        # Phase 3: Emit positions with live P&L updates (every 2s for 12s)
        emit_log("DEMO: Positions open — updating P&L every 2s for 12s", "INFO", "system")
        for tick in range(6):
            for s in demo_symbols:
                e = entries[s["symbol"]]
                price_move = round(random.uniform(-0.3, 0.5), 2)
                current = round(e["entry_price"] + price_move * (tick + 1) / 3, 2)
                current = max(0.01, current)
                pnl = round((current - e["entry_price"]) * e["qty"] * 100, 2)
                pnl_pct = round((current - e["entry_price"]) / e["entry_price"] * 100, 2) if e["entry_price"] > 0 else 0
                emit_position({
                    "symbol": s["symbol"],
                    "strike": s["strike"],
                    "right": s["right"],
                    "expiry": s["expiry"],
                    "quantity": e["qty"],
                    "avg_price": e["entry_price"],
                    "current_price": current,
                    "pnl": pnl,
                    "pnl_percent": pnl_pct,
                    "underlying_atr": round(1.2 + demo_symbols.index(s) * 0.15, 4),
                })
            # Emit fake P&L
            total_pnl = sum(
                round((entries[s["symbol"]]["entry_price"] + random.uniform(-0.2, 0.4)) - entries[s["symbol"]]["entry_price"], 2) * entries[s["symbol"]]["qty"] * 100
                for s in demo_symbols
            )
            emit_pnl(daily_pnl=round(total_pnl, 2), unrealized=round(total_pnl * 0.7, 2), realized=round(total_pnl * 0.3, 2))
            time.sleep(2)

        # Phase 4: Close positions one by one
        emit_log("DEMO: Closing positions one by one", "INFO", "system")
        for s in demo_symbols:
            e = entries[s["symbol"]]
            exit_price = round(e["entry_price"] + random.uniform(-0.5, 1.0), 2)
            exit_price = max(0.01, exit_price)
            trade_pnl = round((exit_price - e["entry_price"]) * e["qty"] * 100, 2)
            emit_trade_closed({
                "symbol": s["symbol"],
                "right": s["right"],
                "strike": s["strike"],
                "expiry": s["expiry"],
                "quantity": e["qty"],
                "pnl": trade_pnl,
                "entry_price": e["entry_price"],
                "exit_price": exit_price,
                "timestamp": datetime.now().isoformat(),
            })
            emit_log(f"DEMO: EXIT FILLED {s['symbol']} {s['strike']}{s['right'][0]} @ ${exit_price:.2f} | P&L: ${trade_pnl:+.2f}", "INFO", "order")
            time.sleep(1.5)

        emit_log("DEMO: Simulation complete — all positions closed", "INFO", "system")
        emit_log("DEMO: Check Positions page (active → blotter → closed), Analytics, and Dashboard", "INFO", "system")
        if not self.running:
            emit_engine_status("Idle", connected=False)

    def close_position(self, params: dict) -> dict:
        """Close a specific position by symbol (and optionally strike/right/expiry for options)."""
        symbol = params.get("symbol", "")
        strike = params.get("strike")
        right = params.get("right")
        expiry = params.get("expiry")
        if strike is not None:
            strike = float(strike)
        emit_log(f"Close position requested for {symbol}" + (f" strike={strike} right={right} expiry={expiry}" if strike or right or expiry else ""), "INFO", "orders")
        if self._order_mgr and hasattr(self._order_mgr, 'close_position_by_symbol'):
            self._order_mgr.close_position_by_symbol(symbol, strike=strike, right=right, expiry=expiry)
        return {"status": "close_requested", "symbol": symbol}

    def close_all(self) -> dict:
        """Cancel all open orders, then flatten TWS positions; repeat until flat. Blocks new entries while running."""
        if self._close_all_thread and self._close_all_thread.is_alive():
            emit_log("Close All already running — ignored duplicate request", "WARN", "orders")
            return {"status": "close_all_already_running"}

        def _nonzero_positions_count() -> int:
            try:
                if not self._client or not self._client.isConnected():
                    return -1
                raw = list(self._client.get_all_positions())
                return len(
                    [p for p in raw if p and int(abs(getattr(p, "position", 0) or 0)) > 0]
                )
            except Exception:
                return -1

        def run_close_all():
            BOT = self._get_bot_module()

            try:
                BOT.CLOSE_ALL_IN_PROGRESS = True
                emit_log("Close All: new entries blocked — cancelling orders and flattening positions", "WARN", "orders")
                if not self._client or not self._client.isConnected():
                    emit_log("Close All: TWS not connected", "ERROR", "orders")
                    return
                buf = getattr(self.config, "emergency_close_buffer_seconds", 5) if self.config else 5
                try:
                    buf = max(0, int(buf))
                except (TypeError, ValueError):
                    buf = 5
                max_rounds = 15
                for r in range(max_rounds):
                    BOT.cancel_all_orders()
                    time.sleep(0.35)
                    BOT.getAndBuyAfterMarketEnd(buffer_seconds=buf)
                    n = _nonzero_positions_count()
                    if n == 0:
                        emit_log("Close All: no open positions remaining", "INFO", "orders")
                        break
                    if n < 0:
                        emit_log("Close All: could not read positions from TWS — stopping rounds", "ERROR", "orders")
                        break
                    emit_log(
                        f"Close All: round {r + 1}/{max_rounds} — {n} position(s) still open, repeating cancel + MKT close",
                        "WARN",
                        "orders",
                    )
                    time.sleep(max(0.5, float(buf)))
                else:
                    n = _nonzero_positions_count()
                    emit_log(
                        f"Close All: stopped after {max_rounds} rounds — {n} position(s) may still be open (check TWS)",
                        "ERROR",
                        "orders",
                    )
            except Exception as e:
                emit_log(f"Close All error: {e}", "ERROR", "orders")
            finally:
                BOT.CLOSE_ALL_IN_PROGRESS = False
                emit_log("Close All: finished — new entries allowed again", "INFO", "orders")

        self._close_all_thread = threading.Thread(target=run_close_all, daemon=True, name="close_all")
        self._close_all_thread.start()
        return {"status": "close_all_started"}

    def close_calls(self) -> dict:
        """Close all CALL positions."""
        emit_log("Close ALL CALLS requested", "WARN", "orders")
        count = 0
        if self._order_mgr and hasattr(self._order_mgr, 'close_positions_by_right'):
            count = self._order_mgr.close_positions_by_right("CALL")
        return {"status": "close_calls_requested", "count": count}

    def close_puts(self) -> dict:
        """Close all PUT positions."""
        emit_log("Close ALL PUTS requested", "WARN", "orders")
        count = 0
        if self._order_mgr and hasattr(self._order_mgr, 'close_positions_by_right'):
            count = self._order_mgr.close_positions_by_right("PUT")
        return {"status": "close_puts_requested", "count": count}

    def update_config(self, params: dict) -> dict:
        """Update configuration at runtime. Syncs BOT globals so cooldown and other params take effect immediately."""
        config_data = params.get("config", {})
        self.config = TradingConfig.from_dict(config_data)
        self._apply_positions_emit_interval()
        try:
            BOT = self._get_bot_module()
            BOT.TRADE_COOLDOWN_SECONDS = int(getattr(self.config, "distance_between_trade", 610))
        except Exception:
            pass
        emit_log("Configuration updated", "INFO", "system")
        return {"status": "config_updated"}

    # ==========================================
    # Internal methods
    # ==========================================

    def _apply_positions_emit_interval(self) -> None:
        if self.config:
            self._positions_interval_sec = float(self.config.positions_emit_interval_sec)

    def _init_database(self):
        """Initialize the database layer."""
        try:
            from data_access import DAL
            self._db = DAL()
            emit_log("Database initialized", "INFO", "system")
        except Exception as e:
            emit_log(f"Database init failed: {e}", "WARN", "system")

    def _init_order_manager(self):
        """Initialize the order manager."""
        try:
            from order_manager import OrderManager
            self._order_mgr = OrderManager(db=self._db)
            emit_log("Order manager initialized", "INFO", "system")
        except Exception as e:
            emit_log(f"Order manager init failed: {e}", "ERROR", "system")
            raise

    def _init_tws_client(self):
        """Initialize and connect the TWS API client. Never raises: on failure we stay disconnected."""
        try:
            from tws_api_client import TwsApiClient

            self._client = TwsApiClient(
                host=self.config.ip,
                port=self.config.port,
                clientId=self.config.client_id,
                event_queue=self._event_queue,
                callback=self._order_mgr.process_trade if self._order_mgr else None,
                account_id=getattr(self.config, "account_id", "") or "",
            )
            # Let engine handle reconnects only (avoids duplicate connections from client's connectionClosed)
            self._client.reconnect_handled_externally = True
            # Grace period: don't treat "not yet connected" as disconnected and reconnect immediately
            self._last_tws_reconnect_attempt = time.time()
            self._try_connect_tws()
        except Exception as e:
            self.connected = False
            emit_connection_status(False, str(e))
            emit_log(f"TWS client init failed (engine will run disconnected): {e}", "WARN", "system")
            # Do not raise: keep engine running so the UI shows "Running" and user sees "TWS Disconnected"

    def _try_connect_tws(self):
        """Attempt to connect to TWS (used at init and for periodic reconnection)."""
        if not self._client or not self.config:
            return
        try:
            self._client.connect(
                host=self.config.ip,
                port=self.config.port,
                clientId=self.config.client_id,
            )
            self._order_mgr.set_client(client=self._client)
            # isConnected() often flips true only after connectAck + API thread start; 0.2s was too tight on some Macs/TWS loads.
            deadline = time.time() + 8.0
            while time.time() < deadline and not self._client.isConnected():
                time.sleep(0.1)

            if self._client.isConnected():
                self.connected = True
                emit_connection_status(True, "Connected to TWS")
                emit_log(f"Connected to TWS at {self.config.ip}:{self.config.port} (clientId={self.config.client_id})", "INFO", "system")
            else:
                self.connected = False
                emit_connection_status(False, "Failed to connect to TWS")
                emit_log(
                    "TWS connection failed — socket/API did not become ready. "
                    f"Using host={self.config.ip!r} port={self.config.port} clientId={self.config.client_id}. "
                    "Confirm TWS or IB Gateway is running, “Enable ActiveX and Socket Clients” is on, and port matches "
                    "(paper TWS often 7497, live 7496; IB Gateway paper often 4002). Use a unique clientId if another app is connected.",
                    "WARN",
                    "system",
                )
        except Exception as e:
            self.connected = False
            emit_connection_status(False, str(e))
            emit_log(
                f"TWS connect error: {e} — check host/port/clientId, API enabled in TWS, and no duplicate clientId.",
                "WARN",
                "system",
            )

    def _try_reconnect_tws_if_needed(self):
        """If disconnected, try to reconnect to TWS periodically so starting TWS later is detected."""
        if self.connected or not self._client or not self.config:
            return
        now = time.time()
        if now - self._last_tws_reconnect_attempt < self._tws_reconnect_interval_sec:
            return
        self._last_tws_reconnect_attempt = now
        try:
            if hasattr(self._client, "disconnect"):
                try:
                    self._client.disconnect()
                except Exception:
                    pass
                time.sleep(0.3)
            self._try_connect_tws()
        except Exception as e:
            emit_log(f"TWS reconnection attempt failed: {e}", "DEBUG", "system")

    def _start_data_feed_and_strategies(self):
        """Start BOT data feed (TWS subscriptions) and strategy event processors. Run once when connected."""
        if self._data_feed_started or not self._client or not self.connected or not self.config:
            return
        try:
            import os
            import tempfile
            from datetime import datetime
            from queue import Empty

            # BOT.py opens config.json at import time. When running as frozen sidecar (e.g. Windows),
            # CWD is not the project root, so we must write config.json and chdir before importing BOT.
            orig_cwd = os.getcwd()
            frozen = getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")
            if frozen:
                config_dir = tempfile.mkdtemp(prefix="optbot_sidecar_")
                config_path = os.path.join(config_dir, "config.json")
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config.to_bot_config_dict(), f, indent=2)
                os.chdir(config_dir)
            else:
                config_dir = PARENT_DIR if os.path.isdir(PARENT_DIR) else orig_cwd
                config_path = os.path.join(config_dir, "config.json")
                # Always overwrite so BOT reads current config at import (user may have changed settings in UI)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config.to_bot_config_dict(), f, indent=2)
                try:
                    os.chdir(config_dir)
                except Exception:
                    pass

            try:
                import BOT
                from common import getExpiry
            except Exception as e:
                emit_log(f"Failed to import BOT/common: {e}", "ERROR", "system")
                emit_error(str(e))
                try:
                    os.chdir(orig_cwd)
                except Exception:
                    pass
                return

            # Set BOT globals so init_data_feed and event_processor use our client/queue/config
            stock_list = list(self.config.stock_list_to_trade.keys()) if self.config.stock_list_to_trade else []
            if not stock_list:
                emit_log("No symbols in stock_list_to_trade; skipping data feed", "WARN", "system")
                try:
                    os.chdir(orig_cwd)
                except Exception:
                    pass
                return
            exchanges = list(self.config.stock_list_to_trade.values()) if self.config.stock_list_to_trade else []
            all_futures = len(exchanges) > 0 and all(e == "CME" for e in exchanges)
            mode = "FUT (futures only)" if all_futures else "OPT (stocks + options chain)"
            emit_log(f"Trading mode: {mode} for symbols: {', '.join(stock_list)}", "INFO", "system")

            BOT.client = self._client
            BOT.order_mgr = self._order_mgr
            BOT.event_queue = self._event_queue
            BOT.stockList = stock_list
            BOT.stock_list_to_trade = getattr(self.config, "stock_list_to_trade", None) or {s: "SMART" for s in stock_list}
            BOT.fetchValue = getattr(self.config, "fetch_value", "1 D")
            BOT.candleTime = getattr(self.config, "candle_time", "5 mins")
            BOT.SUB_ACCOUNT_ID = self.config.account_id or ""
            if BOT.SUB_ACCOUNT_ID:
                emit_log(f"Orders will be routed to account: {BOT.SUB_ACCOUNT_ID}", "INFO", "system")
            BOT.tradeExpiry_val = getExpiry(getattr(self.config, "expiry_to_trade", "next"))
            BOT.spy_qqq_tradeExpiry = getExpiry(getattr(self.config, "spy_qqq_expiry", "0DTE"))
            # Required by BOT.checkConditionsAndTrade (delta/volume thresholds)
            BOT.CALL_DELTA_CHECK = float(getattr(self.config, "call_delta_check", 0.35))
            BOT.PUT_DELTA_CHECK = float(getattr(self.config, "put_delta_check", -0.35))
            BOT.VOLUME_CHECK = int(getattr(self.config, "volume_check", 100))
            # Required by BOT.checkAlgoAndTrade -> timeCheckAndCloseProgram (PnL limits)
            # loss_amount_day MUST be negative (comparison is pnlData <= loss_amount_day)
            raw_profit = float(getattr(self.config, "profit_amount_day", 200.0))
            raw_loss = float(getattr(self.config, "loss_amount_day", 200.0))
            BOT.profit_amount_day = abs(raw_profit)
            BOT.loss_amount_day = -abs(raw_loss)
            BOT.signal_dict = {
                s: {"last_signal": "", "current_signal": "", "last_trade_short_strike": "", "last_trade_buy_strike": "", "right": "", "conIdDetails_short": "", "conIdDetails_buy": ""}
                for s in stock_list
            }
            # Cooldown keys are symbol+right+expiry; empty at startup (first trade per combo allowed)
            BOT.trade_time_dict = {}

            # --- Required for checkAlgoAndTrade, checkConditionsAndTrade, takeTrade, placeOrder (same as main_call) ---
            # Without these, BOT hits NameError or wrong behavior when processing signals/trades.
            BOT.TRADE_COOLDOWN_SECONDS = int(getattr(self.config, "distance_between_trade", 610))
            BOT.PROFIT_INCREMENT = float(getattr(self.config, "profit_increment", 0.03))
            BOT.ATR_CHECKS = float(getattr(self.config, "atr_checks", 0.047))
            BOT.ATR_VALUE = float(getattr(self.config, "atr_value", 0.99))
            BOT.ORDER_EXPIRY_TIMER = int(getattr(self.config, "order_expiry_timer", 15))
            BOT.USE_TIMER_IN_ORDER = str(getattr(self.config, "use_timer_in_order", "ON"))
            BOT.MAX_CONTRACT_AMOUNT = float(getattr(self.config, "max_contract_amount", 350.0))
            BOT.VWAP_ON_OFF = str(getattr(self.config, "vwap_on_off", "ON"))
            BOT.MARKET_START_TIME = str(getattr(self.config, "market_start_time", "19:00:00"))
            BOT.startTime = str(getattr(self.config, "script_start_time", "0935"))
            BOT.endTime = str(getattr(self.config, "script_end_time", "1545"))
            BOT.stockListDict = getattr(self.config, "stock_list_to_trade", None) or {s: "SMART" for s in stock_list}
            BOT.dataInFile = len(stock_list)
            BOT.EXPIRY = str(getattr(self.config, "expiry_to_trade", "next"))
            BOT.useAmount = getattr(self.config, "stock_data", None) or {k: {"amount": getattr(self.config, "max_contract_amount", 350)} for k in stock_list}
            BOT.ACTIVE_VOLUME = int(getattr(self.config, "active_volume", 5))
            BOT.SHARE_VOLUME = int(getattr(self.config, "share_volume", 1))
            BOT.BODY = float(getattr(self.config, "body", 2.0))
            BOT.perDayTrades = int(getattr(self.config, "per_day_trades", 3))
            BOT.USE_DIFF_EXPIRY_INDEX = str(getattr(self.config, "use_diff_expiry_index", "yes"))
            BOT.TRANSMIT = getattr(self.config, "order_transmit", True)

            # Ensure expiryStrike.json exists in CWD before BOT runs (avoids "[Errno 2] No such file or directory").
            # When frozen: copy from bundled resource (_MEIPASS); otherwise create empty or copy from sidecar dir.
            cwd = os.getcwd()
            expiry_strike_path = os.path.join(cwd, "expiryStrike.json")
            try:
                if not os.path.isfile(expiry_strike_path):
                    bundled = None
                    if frozen:
                        base = getattr(sys, "_MEIPASS", "")
                        if base:
                            bundled = os.path.join(base, "expiryStrike.json")
                    if bundled and os.path.isfile(bundled):
                        import shutil
                        shutil.copy2(bundled, expiry_strike_path)
                        emit_log("Copied bundled expiryStrike.json to working dir (will be filled when TWS connects).", "INFO", "system")
                    else:
                        with open(expiry_strike_path, "w", encoding="utf-8") as f:
                            json.dump({}, f)
                        emit_log("Created empty expiryStrike.json (will be filled when TWS connects).", "INFO", "system")
            except Exception as e:
                emit_log(f"Could not create/copy expiryStrike.json: {e}", "WARN", "system")

            try:
                emit_log("Initializing order requests (positions, PnL)...", "INFO", "system")
                BOT.init_order_requests()
                time.sleep(2.0)
                emit_log("Initializing data feed (historical + options)...", "INFO", "system")
                BOT.init_data_feed()
                self._log_tws_underlyings_received()
                BOT.dataStrike = BOT.fetch_all_strike_expiries()
                emit_log("Synchronizing positions (TWS positions → managed orders)...", "INFO", "system")
                BOT.synchronize_positions()
                emit_log("Synchronizing orders...", "INFO", "system")
                BOT.synchronize_orders()
                # Re-sync positions after delay so DB queue insert_order ops complete (avoids race with get_filled_orders)
                def _delayed_sync():
                    time.sleep(3.0)
                    if self.running and getattr(BOT, "STOP_TRADING", True) is False:
                        try:
                            emit_log("Re-syncing positions (DB queue drained)...", "INFO", "system")
                            BOT.synchronize_positions()
                        except Exception as ex:
                            emit_log(f"Delayed sync failed: {ex}", "WARN", "system")
                threading.Thread(target=_delayed_sync, daemon=True).start()
            except Exception as e:
                emit_log(f"Data feed init failed: {e}", "ERROR", "system")
                emit_error(str(e))
                if not frozen:
                    try:
                        os.chdir(orig_cwd)
                    except Exception:
                        pass
                return
            finally:
                if not frozen:
                    try:
                        os.chdir(orig_cwd)
                    except Exception:
                        pass

            # --- P0b: Adjust PnL limits by existing realized P&L (same as standalone main_call) ---
            try:
                account_id = BOT.SUB_ACCOUNT_ID
                pnl_data, realized_start_pnl = self._client.get_pnl(account_id)
                emit_log(f"Starting realized P&L: ${realized_start_pnl:.2f}, current day P&L: ${pnl_data:.2f}", "INFO", "system")
                if realized_start_pnl < 0:
                    starting_loss = realized_start_pnl
                    BOT.profit_amount_day = BOT.profit_amount_day - starting_loss
                    BOT.loss_amount_day = BOT.loss_amount_day + starting_loss
                elif realized_start_pnl > 0:
                    starting_profit = realized_start_pnl
                    BOT.profit_amount_day = BOT.profit_amount_day + starting_profit
                    BOT.loss_amount_day = BOT.loss_amount_day - starting_profit
                emit_log(f"Adjusted PnL limits: profit_target=${BOT.profit_amount_day:.2f}, loss_limit=${BOT.loss_amount_day:.2f}", "INFO", "system")
            except Exception as e:
                emit_log(f"Could not adjust PnL by starting realized: {e}", "WARN", "system")

            # Start event processor threads only if we don't already have running ones (reconnect case)
            alive = [t for t in self._event_processor_threads if t and t.is_alive()]
            if not alive:
                processor_count = getattr(BOT, "PROCESSORS_COUNT", 4)
                self._event_processor_threads = []
                BOT.arm_trading_session_gates()
                for i in range(processor_count):
                    t = threading.Thread(target=BOT.event_processor, args=(self._event_queue, i), daemon=True)
                    t.start()
                    self._event_processor_threads.append(t)
                emit_log(f"Started {processor_count} strategy event processors", "INFO", "system")

                # --- P1a: Start pnl_watchdog_thread (same as standalone main_call) ---
                BOT.STOP_TRADING = False
                BOT.DAY_LOCKED = False
                BOT.CLOSE_ALL_ORDERS = False
                BOT.CLOSE_ALL_IN_PROGRESS = False
                try:
                    pnl_t = threading.Thread(
                        target=BOT.pnl_watchdog_thread,
                        args=(BOT.SUB_ACCOUNT_ID, BOT.profit_amount_day, BOT.loss_amount_day),
                        daemon=True,
                    )
                    pnl_t.start()
                    self._event_processor_threads.append(pnl_t)
                    emit_log("PnL watchdog thread started", "INFO", "system")
                except Exception as e:
                    emit_log(f"Failed to start pnl_watchdog_thread: {e}", "WARN", "system")

                # --- P1b: Start monitor_positions_loop (same as standalone) ---
                try:
                    pos_t = threading.Thread(target=BOT.monitor_positions_loop, daemon=True)
                    pos_t.start()
                    self._event_processor_threads.append(pos_t)
                    emit_log("Position monitor thread started", "INFO", "system")
                except Exception as e:
                    emit_log(f"Failed to start monitor_positions_loop: {e}", "WARN", "system")
            else:
                emit_log(f"Reconnect: {len(alive)} processor threads still running, not starting new ones", "INFO", "system")

            self._client.initialization_done = True
            self._data_feed_started = True
            self._last_signal_heartbeat_time = time.time()
            emit_log("Data feed and strategies started", "INFO", "system")

            # Initial signal scan: get DataFrame of signals for current + previous candles per stock
            # Returns signals from the time system started (current candle at start + previous candles)
            self._signal_scan_start_time = datetime.now()
            def _emit_initial_signal_data():
                try:
                    time.sleep(2.0)  # Allow bars to populate
                    signals = BOT.scan_all_stocks_signals(system_start_time=None, limit=21)  # All candles; UI can filter by system_started_at
                    emit_signal_data(signals, self._signal_scan_start_time.isoformat())
                    emit_log(f"Initial signal scan: {len(signals)} candle signals for {len(stock_list)} stocks", "INFO", "signal")
                except Exception as e:
                    emit_log(f"Initial signal scan failed: {e}", "WARN", "signal")
            threading.Thread(target=_emit_initial_signal_data, daemon=True).start()

            emit_log(
                f"IBKR data + signal scanner started: monitoring {', '.join(stock_list)}. "
                "Logs will show 'Signal scan', 'IBKR bars', 'Trade check', and 'IBKR data' (every 10s) when data is flowing.",
                "INFO", "signal"
            )
        except Exception as e:
            emit_log(f"Start data feed/strategies failed: {e}", "ERROR", "system")
            emit_error(str(e))

    def _log_tws_underlyings_received(self):
        """Log each underlying (STK/FUT) and its price from TWS tick cache so user sees data was fetched (OPT bot: underlyings feed options)."""
        if self._client is None:
            return
        try:
            raw_cache = getattr(self._client, "tick_cache", None) or {}
            lock = getattr(self._client, "_lock", None)
            rows = []

            def collect():
                for tick in raw_cache.values():
                    c = getattr(tick, "contract", None)
                    if not c:
                        continue
                    stype = getattr(c, "secType", "") or ""
                    if stype not in ("STK", "FUT"):
                        continue
                    sym = getattr(c, "localSymbol", "") or getattr(c, "symbol", "") or ""
                    last = getattr(tick, "last", -1)
                    bid = getattr(tick, "bid", -1)
                    ask = getattr(tick, "ask", -1)
                    rows.append((sym, last, bid, ask))

            if lock is not None:
                with lock:
                    collect()
            else:
                collect()

            if rows:
                emit_log("TWS data received (underlyings for OPT):", "INFO", "system")
                for sym, last, bid, ask in rows:
                    l = last if last not in (-1, None) else "—"
                    b = bid if bid not in (-1, None) else "—"
                    a = ask if ask not in (-1, None) else "—"
                    emit_log(f"  {sym}: last={l} bid={b} ask={a}", "INFO", "system")
            else:
                emit_log("TWS data: no underlyings in cache yet; prices may arrive in a few seconds.", "INFO", "system")
        except Exception as e:
            emit_log(f"Log TWS underlyings failed: {e}", "WARN", "system")

    def _run_engine(self):
        """Main trading loop -- processes events from the TWS client."""
        emit_log("Trading engine loop started", "INFO", "system")

        while self.running:
            try:
                # When disconnected, periodically try to connect so starting TWS later is detected
                self._try_reconnect_tws_if_needed()

                # Sync connection state: client may have reconnected or disconnected
                if self._client and getattr(self._client, "isConnected", None):
                    if self._client.isConnected() and not self.connected:
                        self.connected = True
                        self._account_metrics_first_emit_done = False  # Emit account metrics as soon as we have data
                        emit_connection_status(True, "Reconnected to TWS")
                        emit_log("TWS connection restored", "INFO", "system")
                    elif not self._client.isConnected() and self.connected:
                        self.connected = False
                        self._data_feed_started = False
                        self._account_metrics_first_emit_done = False
                        emit_connection_status(False, "TWS disconnected")
                        emit_log("TWS disconnected", "WARN", "system")

                # When connected, start data feed and strategy processors once
                if self.connected and not self._data_feed_started:
                    self._start_data_feed_and_strategies()

                # Do NOT consume the event queue when _data_feed_started is False.
                # Ticks that arrive during init_data_feed (20+ seconds) must accumulate so that
                # when BOT event_processor threads start, they process them. Draining here would
                # discard ticks and lose signals (see SIGNAL_FLOW_BOT_VS_ENGINE.md).

                # Periodic P&L update
                if self._client and self.connected:
                    self._emit_pnl_update()

                now = time.time()
                # Emit account metrics: first time as soon as we have data, then every 5s (avoids up-to-5s delay after Start Trading)
                if self._client and self.connected:
                    has_cache = (
                        getattr(self._client, "account_summary_cache", None)
                        and len(getattr(self._client, "account_summary_cache", {})) > 0
                    )
                    if has_cache:
                        if not self._account_metrics_first_emit_done:
                            self._account_metrics_first_emit_done = True
                            self._last_account_metrics_time = now
                            self._emit_account_metrics()
                        elif now - self._last_account_metrics_time >= self._account_metrics_interval_sec:
                            self._last_account_metrics_time = now
                            self._emit_account_metrics()

                # Every 10s: emit data status so user can see what is being fetched
                if now - self._last_data_status_time >= self._data_status_interval_sec:
                    self._last_data_status_time = now
                    self._emit_data_status()

                # Every 5s: emit current positions so UI Positions page stays in sync
                if self._client and self.connected and now - self._last_positions_time >= self._positions_interval_sec:
                    self._last_positions_time = now
                    self._emit_positions()

                # Every 30s: re-scan signal DataFrame, emit to UI, and heartbeat log
                if self._data_feed_started and now - self._last_signal_heartbeat_time >= self._signal_heartbeat_interval_sec:
                    self._last_signal_heartbeat_time = now
                    try:
                        BOT = self._get_bot_module()
                        signals = BOT.scan_all_stocks_signals(system_start_time=None, limit=21)
                        emit_signal_data(signals, getattr(self, "_signal_scan_start_time", datetime.now()).isoformat())
                    except Exception as e:
                        emit_log(f"Signal scan failed: {e}", "WARN", "signal")
                    try:
                        stock_list = getattr(BOT, "stockList", []) or []
                        active_threads = len([t for t in self._event_processor_threads if t and t.is_alive()])
                        queue_size = self._event_queue.qsize() if self._event_queue else 0
                        emit_log(
                            f"Signal scanner active: {len(stock_list)} symbols, {active_threads} processors, queue={queue_size}",
                            "INFO", "signal"
                        )
                    except Exception:
                        emit_log("Signal scanner active", "INFO", "signal")

                    # Every 30s: check end-of-day time and close all positions if past EOD
                    if self._data_feed_started and self.connected:
                        if not hasattr(self, "_last_eod_check_time"):
                            self._last_eod_check_time = 0.0
                        if now - self._last_eod_check_time >= 30.0:
                            self._last_eod_check_time = now
                            self._check_eod_time()

                time.sleep(0.05)  # 50ms loop

            except Exception as e:
                emit_error(f"Engine loop error: {e}")
                time.sleep(1)

        emit_log("Trading engine loop ended", "INFO", "system")

    def _process_event(self, event):
        """Process an event from the TWS event queue."""
        try:
            event_type = event.get("type", "") if isinstance(event, dict) else str(type(event))
            emit_log(f"Processing event: {event_type}", "DEBUG", "trading")
        except Exception as e:
            emit_log(f"Event processing error: {e}", "ERROR", "trading")

    def _check_eod_time(self):
        """Periodically check if market end time has passed and close all positions."""
        try:
            BOT = self._get_bot_module()
            if getattr(BOT, "STOP_TRADING", False) or getattr(BOT, "DAY_LOCKED", False):
                return
            result = BOT.timeCheckAndCloseProgram(
                BOT.SUB_ACCOUNT_ID,
                BOT.profit_amount_day,
                BOT.loss_amount_day,
            )
            if result:
                emit_log("EOD time/PnL limit reached — positions closed, trading locked", "WARN", "system")
        except Exception as e:
            emit_log(f"EOD time check error: {e}", "WARN", "system")

    def _emit_pnl_update(self):
        """Send P&L update to the frontend. TWS pnl_cache is a flat dict: daily, unrealized, realized.
        Throttled to 1s to reduce IPC volume (~95% fewer emissions)."""
        try:
            if not self.running:
                return  # Do not emit P&L after emergency_stop
            if not self._client or not hasattr(self._client, "pnl_cache") or not self._client.pnl_cache:
                return
            now = time.time()
            if now - self._last_pnl_emit_time < self._pnl_throttle_sec:
                return
            cache = self._client.pnl_cache
            daily = unrealized = realized = 0.0
            # Support both flat dict (current TWS) and per-account objects
            if isinstance(cache.get("daily"), (int, float)) or "daily" in cache:
                daily = float(cache.get("daily") or 0)
                unrealized = float(cache.get("unrealized") or 0)
                realized = float(cache.get("realized") or 0)
            else:
                for _account, pnl_data in cache.items():
                    if hasattr(pnl_data, "dailyPnL"):
                        daily = getattr(pnl_data, "dailyPnL", 0) or 0
                        unrealized = getattr(pnl_data, "unrealizedPnL", 0) or 0
                        realized = getattr(pnl_data, "realizedPnL", 0) or 0
                    break
            emit_pnl(daily_pnl=daily, unrealized=unrealized, realized=realized)
            self._last_pnl_emit_time = now
        except Exception:
            pass  # Silently skip P&L errors

    def _emit_positions(self):
        """Emit current positions to the UI so the Positions page shows active positions."""
        try:
            positions = self.get_positions()
            for pos in positions:
                payload = {
                    "symbol": pos.get("symbol", ""),
                    "strike": float(pos.get("strike", 0)),
                    "right": pos.get("right", ""),
                    "expiry": pos.get("expiry", ""),
                    "quantity": int(pos.get("quantity", 0)),
                    "qty": int(pos.get("quantity", 0)),
                    "avg_price": float(pos.get("avg_price", 0)),
                    "current_price": float(pos.get("current_price", 0)),
                    "pnl": float(pos.get("pnl", 0)),
                    "pnl_percent": float(pos.get("pnl_percent", 0)),
                }
                if pos.get("stoploss_price") is not None:
                    payload["stoploss_price"] = float(pos["stoploss_price"])
                if pos.get("profit_price") is not None:
                    payload["profit_price"] = float(pos["profit_price"])
                if pos.get("initial_profit_price") is not None:
                    payload["initial_profit_price"] = float(pos["initial_profit_price"])
                if pos.get("effective_stoploss_price") is not None:
                    payload["effective_stoploss_price"] = float(pos["effective_stoploss_price"])
                if pos.get("trailing_active") is True:
                    payload["trailing_active"] = True
                if pos.get("bid") is not None:
                    payload["bid"] = float(pos["bid"])
                if pos.get("ask") is not None:
                    payload["ask"] = float(pos["ask"])
                if pos.get("last") is not None:
                    payload["last"] = float(pos["last"])
                if pos.get("exit_price_used") is not None and pos.get("exit_price_used") > 0:
                    payload["exit_price_used"] = float(pos["exit_price_used"])
                    payload["exit_price_source"] = str(pos.get("exit_price_source", ""))
                if pos.get("pnl_source"):
                    payload["pnl_source"] = str(pos["pnl_source"])
                emit_position(payload)
        except Exception as e:
            emit_log(f"Emit positions failed: {e}", "WARN", "system")

    def _emit_account_metrics(self):
        """Read TWS account_summary_cache and emit account_metrics event (P0: continuous IBKR metrics)."""
        try:
            if not hasattr(self._client, "account_summary_cache") or not self._client.account_summary_cache:
                return
            cache = getattr(self._client, "account_summary_cache", {})
            lock = getattr(self._client, "_lock", None)
            if lock:
                with lock:
                    cache = dict(cache)
            else:
                cache = dict(cache)
            # Parse numeric values for frontend; keep raw string for non-numeric
            metrics = {}
            for tag, value in cache.items():
                if value is None or value == "":
                    continue
                try:
                    metrics[tag] = float(value)
                except (TypeError, ValueError):
                    metrics[tag] = value
            if metrics:
                emit_account_metrics(metrics)
        except Exception:
            pass

    def _emit_data_status(self):
        """Emit a snapshot of what data is being fetched (every ~10s) so the user can see if anything is running."""
        try:
            symbols = []
            if self.config and self.config.stock_list_to_trade:
                symbols = list(self.config.stock_list_to_trade.keys())

            queue_size = 0
            if self._event_queue is not None:
                try:
                    queue_size = self._event_queue.qsize()
                except Exception:
                    pass

            tick_count = 0
            stk_count = 0
            fut_count = 0
            opt_count = 0
            stock_ticks = []
            symbol_last = {}  # symbol -> last price (or absent); used for log line
            stk_full = []     # full TWS data per STK/FUT symbol for logging
            opt_sample = []   # sample of OPT (options) data received for logging (OPT bot)
            bar_count = 0

            if self._client is not None:
                try:
                    # Snapshot tick data under lock (TWS updates tick_cache from another thread)
                    raw_cache = getattr(self._client, "tick_cache", None) or {}
                    tick_count = len(raw_cache)
                    stk_snapshot = []  # list of (symbol, last, bid, ask, close, volume) for STK/FUT
                    lock = getattr(self._client, "_lock", None)

                    def capture_stk(tick):
                        c = getattr(tick, "contract", None)
                        if not c:
                            return
                        stype = getattr(c, "secType", None) or ""
                        if stype not in ("STK", "FUT"):
                            return
                        # Use localSymbol for display (e.g. MNQU5) when present, else symbol
                        sym = getattr(c, "localSymbol", "") or getattr(c, "symbol", "") or getattr(tick, "symbol", "")
                        last = getattr(tick, "last", -1)
                        bid = getattr(tick, "bid", -1)
                        ask = getattr(tick, "ask", -1)
                        close = getattr(tick, "close", -1)
                        vol = getattr(tick, "volume", -1)
                        stk_snapshot.append((sym, last, bid, ask, close, vol))
                        stk_full.append({
                            "symbol": sym,
                            "last": last, "bid": bid, "ask": ask, "close": close, "volume": vol,
                        })

                    def capture_opt(tick):
                        c = getattr(tick, "contract", None)
                        if not c:
                            return
                        if getattr(c, "secType", "") != "OPT":
                            return
                        # Readable OPT label: symbol expiry right strike (e.g. SPY 20250221C450)
                        sym = getattr(c, "symbol", "") or ""
                        exp = getattr(c, "lastTradeDateOrContractMonth", "") or ""
                        right = getattr(c, "right", "") or ""
                        strike = getattr(c, "strike", 0) or 0
                        label = f"{sym} {exp}{right[0] if right else ''}{strike}"
                        last = getattr(tick, "last", -1)
                        bid = getattr(tick, "bid", -1)
                        ask = getattr(tick, "ask", -1)
                        opt_sample.append({"label": label, "last": last, "bid": bid, "ask": ask})

                    if lock is not None:
                        with lock:
                            for tick in raw_cache.values():
                                try:
                                    stype = getattr(getattr(tick, "contract", None), "secType", "") or ""
                                    if stype == "STK":
                                        stk_count += 1
                                    elif stype == "OPT":
                                        opt_count += 1
                                        capture_opt(tick)
                                    elif stype == "FUT":
                                        fut_count += 1
                                    capture_stk(tick)
                                except Exception:
                                    pass
                    else:
                        for tick in raw_cache.values():
                            try:
                                stype = getattr(getattr(tick, "contract", None), "secType", "") or ""
                                if stype == "STK":
                                    stk_count += 1
                                elif stype == "OPT":
                                    opt_count += 1
                                    capture_opt(tick)
                                elif stype == "FUT":
                                    fut_count += 1
                                capture_stk(tick)
                            except Exception:
                                pass
                    # Limit OPT sample so log is readable (OPT bot: show options data is flowing)
                    opt_sample = opt_sample[:15]
                    # Build symbol -> price; use bid/ask when last not set (TWS often sends bid/ask before last)
                    symbol_last = {}
                    for sym, last, bid, ask, _close, _vol in stk_snapshot:
                        if not sym:
                            continue
                        price = None
                        if last != -1 and last is not None:
                            price = round(float(last), 2)
                        elif bid not in (-1, None) and ask not in (-1, None):
                            price = round((float(bid) + float(ask)) / 2, 2)
                        elif ask not in (-1, None):
                            price = round(float(ask), 2)
                        elif bid not in (-1, None):
                            price = round(float(bid), 2)
                        if price is not None:
                            symbol_last[sym] = price
                        elif sym not in symbol_last:
                            symbol_last[sym] = None
                    # Build full tick payload (symbol, last, bid, ask, volume) for UI grid
                    def _entry(sym, last_val):
                        e = {"symbol": sym, "last": last_val}
                        for d in stk_full:
                            if d.get("symbol") == sym:
                                bid, ask, vol = d.get("bid"), d.get("ask"), d.get("volume")
                                if bid not in (-1, None): e["bid"] = round(float(bid), 2)
                                if ask not in (-1, None): e["ask"] = round(float(ask), 2)
                                if vol not in (-1, None): e["volume"] = int(vol)
                                break
                        return e
                    # Ordered: config symbols first, then any extra from cache
                    for sym in symbols:
                        if sym in symbol_last and symbol_last[sym] is not None:
                            stock_ticks.append(_entry(sym, symbol_last[sym]))
                    for sym, last in symbol_last.items():
                        if last is not None and sym not in symbols:
                            stock_ticks.append(_entry(sym, last))
                    stock_ticks = stock_ticks[:15]
                except Exception:
                    pass
                try:
                    history_cache = getattr(self._client, "history_cache", None) or {}
                    bar_count = len(history_cache)
                except Exception:
                    pass

            emit_data_status(
                connected=self.connected,
                data_feed_started=self._data_feed_started,
                symbols=symbols,
                queue_size=queue_size,
                tick_count=tick_count,
                stock_ticks=stock_ticks,
                bar_count=bar_count,
            )

            # Log one-line summary: IBKR data received so user can see if something is going
            # trading_symbols = config symbols (e.g. 9); tick_subs = total cache including options (e.g. 15)
            feed = "yes" if self._data_feed_started else "no"
            stk_opt = f" ({stk_count} STK, {fut_count} FUT, {opt_count} OPT)" if (stk_count or opt_count or fut_count) else ""
            summary = (
                f"IBKR data: TWS={self.connected}, feed={feed}, trading_symbols={len(symbols)}, "
                f"tick_subs={tick_count}{stk_opt}, bar_series={bar_count}"
            )
            if symbols:
                price_parts = [f"{sym}={symbol_last.get(sym) if symbol_last.get(sym) is not None else '—'}" for sym in symbols[:12]]
                summary += " | Latest prices: " + ", ".join(price_parts)
            elif stock_ticks:
                sample = ", ".join(f"{t['symbol']}={t['last']}" for t in stock_ticks[:10])
                summary += f" | Latest prices: {sample}"
            else:
                summary += " | Latest prices: (waiting for ticks)"
            emit_log(summary, "INFO", "system")

            # Single-line summary of TWS data (avoid flooding UI with per-symbol lines)
            if stk_full:
                sample = ", ".join(f"{d['symbol']}={d['last']}" for d in stk_full[:5])
                if len(stk_full) > 5:
                    sample += f" (+{len(stk_full) - 5} more)"
                emit_log(f"TWS underlyings: {sample}", "INFO", "system")
            if opt_sample:
                emit_log(f"TWS options: {len(opt_sample)} contracts in sample (data flowing)", "INFO", "system")
            if not stk_full and not opt_sample:
                if stk_count == 0 and fut_count == 0 and opt_count == 0:
                    emit_log(
                        f"TWS data: no subscriptions in cache (ticks={tick_count}). "
                        "Ensure Symbols to trade were sent from UI (e.g. SPY, QQQ for OPT; MNQU5, NQU5 for FUT).",
                        "INFO", "system"
                    )
                elif stk_count == 0 and fut_count == 0:
                    emit_log(
                        f"TWS data: {opt_count} OPT subscribed but no underlyings (STK/FUT) in cache. "
                        "OPT bot needs underlyings (stocks) for options chain; add symbols like SPY, QQQ.",
                        "INFO", "system"
                    )
                else:
                    emit_log(
                        f"TWS data: {stk_count} STK, {fut_count} FUT subscribed but no prices received yet (bid/ask/last still -1). TWS may send them shortly.",
                        "INFO", "system"
                    )
        except Exception as e:
            emit_log(f"Data status error: {e}", "WARN", "system")
