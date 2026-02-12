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
            emit_error(f"Failed to start trading engine: {e}")
            self.running = False
            raise

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
        """Close a specific position."""
        symbol = params.get("symbol", "")
        emit_log(f"Close position requested for {symbol}", "INFO", "orders")
        # Delegate to order manager
        if self._order_mgr and hasattr(self._order_mgr, 'close_position'):
            self._order_mgr.close_position(symbol)
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
        """Initialize and connect the TWS API client."""
        try:
            from tws_api_client import TwsApiClient

            self._client = TwsApiClient(
                host=self.config.ip,
                port=self.config.port,
                clientId=self.config.client_id,
                event_queue=self._event_queue,
                callback=self._order_mgr.process_trade if self._order_mgr else None,
            )
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
                emit_log("TWS connection failed", "ERROR", "system")

        except Exception as e:
            self.connected = False
            emit_connection_status(False, str(e))
            emit_log(f"TWS client init failed: {e}", "ERROR", "system")
            raise

    def _run_engine(self):
        """Main trading loop -- processes events from the TWS client."""
        emit_log("Trading engine loop started", "INFO", "system")

        while self.running:
            try:
                # Process events from the TWS event queue
                if self._event_queue and not self._event_queue.empty():
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
