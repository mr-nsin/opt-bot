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
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent directories to path for importing existing modules
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from protocol.emitter import (
    emit_log, emit_engine_status, emit_connection_status,
    emit_pnl, emit_position, emit_signal, emit_trade_executed,
    emit_trade_closed, emit_order_update, emit_error,
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

    def start(self, config_data: dict) -> dict:
        """Start the trading engine with the given configuration."""
        if self.running:
            return {"status": "already_running"}

        try:
            # Parse configuration
            self.config = TradingConfig.from_dict(config_data)
            emit_log(f"Configuration loaded: {len(self.config.stock_list_to_trade)} symbols")

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
                    "Please install trading-engine dependencies into a Python 3.9–3.11 virtualenv "
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

    def stop(self) -> dict:
        """Gracefully stop the trading engine."""
        if not self.running:
            return {"status": "not_running"}

        emit_log("Stopping trading engine...", "INFO", "system")
        self.running = False

        # Disconnect TWS
        if self._client and hasattr(self._client, 'disconnect'):
            try:
                self._client.disconnect()
            except Exception as e:
                emit_log(f"Error disconnecting TWS: {e}", "WARN", "system")

        emit_engine_status("Idle", connected=False)
        emit_log("Trading engine stopped", "INFO", "system")

        return {"status": "stopped"}

    def emergency_stop(self) -> dict:
        """Emergency stop: immediately halt all trading."""
        emit_log("EMERGENCY STOP triggered!", "ERROR", "system")
        self.running = False

        # Force disconnect
        if self._client:
            try:
                self._client.disconnect()
            except:
                pass

        emit_engine_status("Idle", connected=False)
        return {"status": "emergency_stopped"}

    def get_status(self) -> dict:
        """Get current engine status."""
        return {
            "running": self.running,
            "connected": self.connected,
            "config_loaded": self.config is not None,
        }

    def get_positions(self) -> list:
        """Get current positions."""
        if not self._client:
            return []

        positions = []
        if hasattr(self._client, 'positions'):
            for key, pos in self._client.positions.items():
                positions.append({
                    "symbol": getattr(pos, 'symbol', str(key)),
                    "strike": getattr(pos, 'strike', 0),
                    "right": getattr(pos, 'right', ''),
                    "expiry": getattr(pos, 'expiry', ''),
                    "quantity": getattr(pos, 'position', 0),
                    "avg_price": getattr(pos, 'avg_price', 0),
                    "current_price": 0,
                    "pnl": 0,
                    "pnl_percent": 0,
                })
        return positions

    def close_position(self, params: dict) -> dict:
        """Close a specific position by symbol."""
        symbol = params.get("symbol", "")
        emit_log(f"Close position requested for {symbol}", "INFO", "orders")
        if self._order_mgr and hasattr(self._order_mgr, 'close_position_by_symbol'):
            self._order_mgr.close_position_by_symbol(symbol)
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
            time.sleep(0.5)

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
            from datetime import datetime
            from queue import Empty

            # BOT and init_data_feed expect project root cwd (config.json, expiryStrike.json)
            orig_cwd = os.getcwd()
            try:
                if os.path.isdir(PARENT_DIR):
                    os.chdir(PARENT_DIR)
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
                return

            BOT.client = self._client
            BOT.order_mgr = self._order_mgr
            BOT.event_queue = self._event_queue
            BOT.stockList = stock_list
            BOT.fetchValue = getattr(self.config, "fetch_value", "1 D")
            BOT.candleTime = getattr(self.config, "candle_time", "5 mins")
            BOT.SUB_ACCOUNT_ID = self.config.account_id or ""
            BOT.tradeExpiry_val = getExpiry(getattr(self.config, "expiry_to_trade", "next"))
            BOT.spy_qqq_tradeExpiry = getExpiry(getattr(self.config, "spy_qqq_expiry", "0DTE"))
            BOT.signal_dict = {
                s: {"last_signal": "", "current_signal": "", "last_trade_short_strike": "", "last_trade_buy_strike": "", "right": "", "conIdDetails_short": "", "conIdDetails_buy": ""}
                for s in stock_list
            }
            BOT.trade_time_dict = {}
            for s in stock_list:
                BOT.trade_time_dict[f"{s}_CALL"] = datetime.now()
                BOT.trade_time_dict[f"{s}_PUT"] = datetime.now()

            try:
                os.chdir(PARENT_DIR)
            except Exception:
                pass

            try:
                emit_log("Initializing order requests (positions, PnL)...", "INFO", "system")
                BOT.init_order_requests()
                time.sleep(2.0)
                emit_log("Initializing data feed (historical + options)...", "INFO", "system")
                BOT.init_data_feed()
                BOT.dataStrike = BOT.fetch_all_strike_expiries()
                emit_log("Synchronizing orders...", "INFO", "system")
                BOT.synchronize_orders()
            except Exception as e:
                emit_log(f"Data feed init failed: {e}", "ERROR", "system")
                emit_error(str(e))
                return
            finally:
                try:
                    os.chdir(orig_cwd)
                except Exception:
                    pass

            # Start event processor threads (consume ticks and run strategies)
            processor_count = getattr(BOT, "PROCESSORS_COUNT", 4)
            self._event_processor_threads = []
            for i in range(processor_count):
                t = threading.Thread(target=BOT.event_processor, args=(self._event_queue, i), daemon=True)
                t.start()
                self._event_processor_threads.append(t)
            emit_log(f"Started {processor_count} strategy event processors", "INFO", "system")

            self._client.initialization_done = True
            self._data_feed_started = True
            emit_log("Data feed and strategies started", "INFO", "system")
        except Exception as e:
            emit_log(f"Start data feed/strategies failed: {e}", "ERROR", "system")
            emit_error(str(e))

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
                        emit_connection_status(True, "Reconnected to TWS")
                        emit_log("TWS connection restored", "INFO", "system")
                    elif not self._client.isConnected() and self.connected:
                        self.connected = False
                        self._data_feed_started = False
                        emit_connection_status(False, "TWS disconnected")
                        emit_log("TWS disconnected", "WARN", "system")

                # When connected, start data feed and strategy processors once
                if self.connected and not self._data_feed_started:
                    self._start_data_feed_and_strategies()

                # Process events from the TWS event queue only when BOT processors are not running
                # (when _data_feed_started, BOT event_processor threads consume the queue)
                if not self._data_feed_started and self._event_queue and not self._event_queue.empty():
                    try:
                        event = self._event_queue.get(timeout=0.1)
                        self._process_event(event)
                    except Exception:
                        pass

                # Periodic P&L update
                if self._client and self.connected:
                    self._emit_pnl_update()

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

    def _emit_pnl_update(self):
        """Send P&L update to the frontend."""
        try:
            if hasattr(self._client, 'pnl_cache') and self._client.pnl_cache:
                for account, pnl_data in self._client.pnl_cache.items():
                    if hasattr(pnl_data, 'dailyPnL'):
                        emit_pnl(
                            daily_pnl=getattr(pnl_data, 'dailyPnL', 0) or 0,
                            unrealized=getattr(pnl_data, 'unrealizedPnL', 0) or 0,
                            realized=getattr(pnl_data, 'realizedPnL', 0) or 0,
                        )
        except Exception:
            pass  # Silently skip P&L errors
