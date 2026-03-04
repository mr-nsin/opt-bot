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

# Add parent directories to path for importing existing modules
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from protocol.emitter import (
    emit_log, emit_engine_status, emit_connection_status,
    emit_pnl, emit_position, emit_signal, emit_trade_executed,
    emit_trade_closed, emit_order_update, emit_error,
    emit_data_status, emit_account_metrics,
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
        self._positions_interval_sec: float = 2.0
        self._last_signal_heartbeat_time: float = 0
        self._signal_heartbeat_interval_sec: float = 30.0  # Every 30s log that engine is scanning
        self._last_pnl_emit_time: float = 0
        self._pnl_throttle_sec: float = 1.0  # Emit PnL at most once per second (~95% less IPC)

    def start(self, config_data: dict) -> dict:
        """Start the trading engine with the given configuration."""
        if self.running:
            return {"status": "already_running"}

        try:
            # Parse configuration (symbols come from UI – sidecar subscribes to these)
            self.config = TradingConfig.from_dict(config_data)
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
            import BOT
            if self._client and self._client.isConnected():
                emit_log("Cancelling all open orders...", "INFO", "system")
                BOT.cancel_all_orders()
                emit_log("All orders cancelled (positions left open)", "INFO", "system")
            else:
                emit_log("TWS not connected — cannot cancel orders", "WARN", "system")
        except Exception as e:
            emit_log(f"Error cancelling orders: {e}", "ERROR", "system")

    def _close_all_orders_and_positions(self):
        """Cancel all open orders and close all positions (used by Emergency Stop)."""
        try:
            import BOT
            if self._client and self._client.isConnected():
                emit_log("Cancelling all open orders...", "INFO", "system")
                BOT.cancel_all_orders()
                emit_log("Closing all open positions at market price...", "INFO", "system")
                BOT.getAndBuyAfterMarketEnd()
                emit_log("All orders cancelled and positions closed", "INFO", "system")
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
            import BOT
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

    def emergency_stop(self) -> dict:
        """Emergency stop: close all orders/positions, then immediately halt."""
        emit_log("EMERGENCY STOP triggered!", "ERROR", "system")
        self.running = False

        # Signal BOT globals to stop trading loops
        try:
            import BOT
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
        emit_log("Emergency stop complete — all orders cancelled, positions closed", "ERROR", "system")
        return {"status": "emergency_stopped"}

    def get_status(self) -> dict:
        """Get current engine status."""
        return {
            "running": self.running,
            "connected": self.connected,
            "config_loaded": self.config is not None,
        }

    def get_positions(self) -> list:
        """Get current positions with live price and P&L from tick cache and order manager."""
        if not self._client:
            return []

        positions = []
        if hasattr(self._client, 'positions'):
            for key, pos in self._client.positions.items():
                qty = getattr(pos, 'position', 0)
                if qty == 0:
                    continue

                # avg_cost from TWS is per-share cost (for options: price * multiplier)
                avg_cost = getattr(pos, 'avg_cost', 0)
                avg_price = avg_cost / 100.0 if avg_cost > 1 else avg_cost

                # Try to get live price from order manager tick lookup, then client tick cache
                current_price = 0.0
                symbol = getattr(pos, 'symbol', str(key))
                strike = getattr(pos, 'strike', 0)
                right = getattr(pos, 'right', '')
                expiry = getattr(pos, 'expiry', '')

                if self._order_mgr:
                    entry_order = self._order_mgr._find_entry_order(symbol, strike=strike, right=right)
                    if entry_order:
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

                pnl = (current_price - avg_price) * qty * 100 if current_price > 0 and avg_price > 0 else 0
                pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 and current_price > 0 else 0

                positions.append({
                    "symbol": symbol,
                    "strike": strike,
                    "right": right,
                    "expiry": expiry,
                    "quantity": qty,
                    "avg_price": round(avg_price, 4),
                    "current_price": round(current_price, 4),
                    "pnl": round(pnl, 2),
                    "pnl_percent": round(pnl_pct, 2),
                })
        return positions

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
        """Close a specific position by symbol (and optionally strike/right for options)."""
        symbol = params.get("symbol", "")
        strike = params.get("strike")
        right = params.get("right")
        if strike is not None:
            strike = float(strike)
        emit_log(f"Close position requested for {symbol}" + (f" strike={strike} right={right}" if strike or right else ""), "INFO", "orders")
        if self._order_mgr and hasattr(self._order_mgr, 'close_position_by_symbol'):
            self._order_mgr.close_position_by_symbol(symbol, strike=strike, right=right)
        return {"status": "close_requested", "symbol": symbol}

    def close_all(self) -> dict:
        """Close all positions."""
        emit_log("Close ALL positions requested", "WARN", "orders")
        if self._order_mgr and hasattr(self._order_mgr, 'close_all_positions'):
            self._order_mgr.close_all_positions()
        return {"status": "close_all_requested"}

    def update_config(self, params: dict) -> dict:
        """Update configuration at runtime."""
        config_data = params.get("config", {})
        self.config = TradingConfig.from_dict(config_data)
        emit_log("Configuration updated", "INFO", "system")
        return {"status": "config_updated"}

    # ==========================================
    # Internal methods
    # ==========================================

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
            time.sleep(0.2)  # Brief pause for TWS to register connection (was 0.5s; reduced for faster startup)

            if self._client.isConnected():
                self.connected = True
                emit_connection_status(True, "Connected to TWS")
                emit_log(f"Connected to TWS at {self.config.ip}:{self.config.port}", "INFO", "system")
            else:
                self.connected = False
                emit_connection_status(False, "Failed to connect to TWS")
                emit_log("TWS connection failed", "WARN", "system")
        except Exception as e:
            self.connected = False
            emit_connection_status(False, str(e))
            emit_log(f"TWS connect attempt failed: {e}", "DEBUG", "system")

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
            BOT.trade_time_dict = {}
            past_time = datetime.now() - timedelta(seconds=int(getattr(self.config, "distance_between_trade", 610)) + 60)
            for sym in stock_list:
                BOT.trade_time_dict[f"{sym}_CALL"] = past_time
                BOT.trade_time_dict[f"{sym}_PUT"] = past_time

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
                for i in range(processor_count):
                    t = threading.Thread(target=BOT.event_processor, args=(self._event_queue, i), daemon=True)
                    t.start()
                    self._event_processor_threads.append(t)
                emit_log(f"Started {processor_count} strategy event processors", "INFO", "system")

                # --- P1a: Start pnl_watchdog_thread (same as standalone main_call) ---
                BOT.STOP_TRADING = False
                BOT.DAY_LOCKED = False
                BOT.CLOSE_ALL_ORDERS = False
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

                # Every 30s: heartbeat to show the engine is alive and scanning for signals
                if self._data_feed_started and now - self._last_signal_heartbeat_time >= self._signal_heartbeat_interval_sec:
                    self._last_signal_heartbeat_time = now
                    try:
                        import BOT
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
            import BOT
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
            if not hasattr(self._client, "pnl_cache") or not self._client.pnl_cache:
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
