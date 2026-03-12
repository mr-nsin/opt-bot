import datetime
from typing import List, Optional
from common import MarketOrder, OptionOrder, Tick, Trade, create_order_obj, logger, Contract
from data_access import DAL
from tws_api_client import TwsApiClient

from threading import Lock

# ---- Frontend log emitter (sends logs to Tauri UI via JSON-RPC stdout) ----
try:
    from protocol.emitter import (
        emit_log as _emit_log,
        emit_order_update as _emit_order_update,
        emit_trade_executed as _emit_trade_executed,
        emit_trade_closed as _emit_trade_closed,
    )
except ImportError:
    def _emit_log(message, level="INFO", category="trading"):
        pass
    def _emit_order_update(*args, **kwargs):
        pass
    def _emit_trade_executed(*args, **kwargs):
        pass
    def _emit_trade_closed(*args, **kwargs):
        pass



class OrderManager:
    """
    OrderManager is a class that manages orders and their caches.

    Attributes:
        api_client (TwsApiClient): An instance of TwsApiClient that communicates with the API server.
        orders_cache (dict): A dictionary that stores all orders with their IDs as keys and the orders themselves as values.
        entry_orders_cache (dict): A dictionary that stores entry orders keyed by option_symbol (symbol+expiry+right+strike) to support multiple positions per underlying.
        exit_orders_cache (dict): A dictionary that stores exit orders with their symbols as keys and the orders themselves as values.
    """
    
    def __init__(self, db: DAL) -> None:
        """
        Initializes a new instance of the OrderManager class.
        """
        self.db = db
        self.api_client = None
        self.orders_cache = {}
        self.entry_orders_cache = {}
        self.exit_orders_cache = {}
        self.order_id_tick_lookup = {}
        self.recent_trade_closures = {}  # Track cooldowns
        self.order_lock = Lock()

    def set_client(self, client: TwsApiClient) -> None:
        """
        Sets the TwsApiClient instance for the OrderManager.

        Args:
            client (TwsApiClient): The TwsApiClient instance to be set.
        """
        self.api_client = client

    def _option_key(self, order: OptionOrder) -> str:
        """Composite key for option orders (symbol+expiry+right+strike) to support multiple positions per underlying."""
        return getattr(order, "option_symbol", None) or f"{order.symbol}{order.expiration}{order.right}{order.strike}"

    def close_position_by_symbol(self, symbol: str, strike: float = None, right: str = None, expiry: str = None, reason: str = "manual") -> None:
        """
        Close an open position by symbol (and optionally strike/right/expiry for options).
        Used by Tauri/sidecar when user clicks Close, and by monitor_positions_loop.
        """
        if not self.api_client or not self.api_client.isConnected():
            logger.warning("Cannot close position: TWS not connected")
            return
        order = self._find_entry_order(symbol, strike=strike, right=right, expiry=expiry)
        if not order:
            logger.warning(f"No managed position found for symbol {symbol}" + (f" strike={strike} right={right}" if strike or right else ""))
            return
        option_tick = self.order_id_tick_lookup.get(order.id)
        if option_tick is None:
            option_tick = Tick(symbol=order.symbol, last=-1, bid=-1, ask=-1)
        logger.info(f"CLOSE POSITION REQUEST: {order.option_symbol} — reason={reason}")
        self.close_position(order=order, option_tick=option_tick)

    def close_positions_by_right(self, right: str) -> int:
        """
        Close all managed positions matching the given right (CALL or PUT).
        Returns the number of positions closed.
        """
        if not self.api_client or not self.api_client.isConnected():
            logger.warning("Cannot close positions: TWS not connected")
            return 0
        right_norm = (right or "").upper()
        if right_norm not in ("CALL", "PUT", "C", "P"):
            logger.warning(f"Invalid right for close_positions_by_right: {right}")
            return 0
        r_match = "C" if right_norm in ("CALL", "C") else "P"
        with self.order_lock:
            orders = [o for o in self.entry_orders_cache.values() if o and (o.right or "")[0:1].upper() == r_match]
        count = 0
        for order in orders:
            try:
                option_tick = self.order_id_tick_lookup.get(order.id)
                if option_tick is None:
                    option_tick = Tick(symbol=order.symbol, last=-1, bid=-1, ask=-1)
                self.close_position(order=order, option_tick=option_tick)
                count += 1
            except Exception as ex:
                logger.error(f"Error closing position {order.option_symbol}: {ex}", exc_info=True)
        logger.info(f"Close {right_norm} positions: {count} closed")
        return count

    def close_all_positions(self) -> None:
        """
        Close all managed open positions (used by Tauri/sidecar when user clicks Close All).
        """
        if not self.api_client or not self.api_client.isConnected():
            logger.warning("Cannot close all positions: TWS not connected")
            return
        with self.order_lock:
            orders = list(self.entry_orders_cache.values())
        for order in orders:
            if not order:
                continue
            try:
                option_tick = self.order_id_tick_lookup.get(order.id)
                if option_tick is None:
                    option_tick = Tick(symbol=order.symbol, last=-1, bid=-1, ask=-1)
                self.close_position(order=order, option_tick=option_tick)
            except Exception as ex:
                logger.error(f"Error closing position {order.option_symbol}: {ex}", exc_info=True)

    def _norm_expiry(self, exp: str) -> str:
        """Normalize expiry to YYYYMMDD for matching (e.g. 2026-03-06 -> 20260306)."""
        if not exp:
            return ""
        s = str(exp).replace("-", "").replace("/", "").strip()
        if len(s) == 8 and s.isdigit():
            return s
        if len(s) == 10 and s[4] == "0" and s[7] == "0":
            return s.replace("-", "")[:8]
        return s[:8] if len(s) >= 8 else s

    def _norm_right(self, r: str) -> str:
        """Normalize right to C or P."""
        if not r:
            return ""
        r = str(r).upper()
        if r in ("C", "CALL"):
            return "C"
        if r in ("P", "PUT"):
            return "P"
        return r[0] if r else ""

    def _find_entry_order(self, symbol: str, strike: float = None, right: str = None, expiry: str = None) -> Optional[OptionOrder]:
        """Find entry order matching position (symbol, strike, right, expiry)."""
        if not symbol:
            return None
        pos_exp = self._norm_expiry(expiry or "")
        pos_right = self._norm_right(right or "")
        pos_strike = float(strike) if strike is not None else None
        with self.order_lock:
            for order in self.entry_orders_cache.values():
                if not order:
                    continue
                if (order.symbol or "").upper() != (symbol or "").upper():
                    continue
                if pos_strike is not None and order.strike is not None:
                    if abs(float(order.strike) - pos_strike) > 0.01:
                        continue
                if pos_right and order.right:
                    if self._norm_right(order.right) != pos_right:
                        continue
                if pos_exp and order.expiration:
                    if self._norm_expiry(order.expiration) != pos_exp:
                        continue
                return order
        return None

    def check_exit_conditions(self, pos) -> None:
        """
        For a TWS position, find matching entry order and tick, then run TP/SL check.
        Used by monitor_positions_loop as backup when ticks are sparse.
        """
        if not pos or getattr(pos, "position", 0) == 0:
            return
        symbol = getattr(pos, "symbol", "") or ""
        strike = getattr(pos, "strike", None)
        right = getattr(pos, "right", None)
        expiry = getattr(pos, "expiry", None) or getattr(pos, "lastTradeDateOrContractMonth", None)
        entry_order = self._find_entry_order(symbol, strike=strike, right=right, expiry=expiry)
        if not entry_order:
            logger.debug(
                f"Position {symbol} {strike} {right} {expiry}: no matching entry order "
                f"(entry_orders={len(self.entry_orders_cache)}, ticks={len(self.order_id_tick_lookup)})"
            )
            return
        option_tick = self.order_id_tick_lookup.get(entry_order.id)
        if option_tick is None:
            logger.debug(f"Position {symbol} {strike} {right}: matched order but NO TICK")
            return
        option_tick.active_order = entry_order
        self.check_and_close_position(tick=option_tick)

    def del_entry_order(self, order: OptionOrder, option_tick: Tick) -> None:
        key = self._option_key(order)
        with self.order_lock:
            if self.orders_cache.get(order.id, None):
                self.orders_cache.pop(order.id)
            if self.entry_orders_cache.get(key, None):
                self.entry_orders_cache.pop(key)
            if self.order_id_tick_lookup.get(order.id, None):
                self.order_id_tick_lookup.pop(order.id)

    def add_entry_order(self, order: OptionOrder, option_tick: Tick) -> None:
        """
        Adds an entry order to the orders_cache and entry_orders_cache.
        Keyed by option_symbol to support multiple positions per underlying.
        """
        with self.order_lock:
            self.orders_cache[order.id] = order
            self.entry_orders_cache[self._option_key(order)] = order
            self.order_id_tick_lookup[order.id] = option_tick

    def del_exit_order(self, order: OptionOrder, option_tick: Tick) -> None:
        key = self._option_key(order)
        with self.order_lock:
            if self.orders_cache.get(order.id, None):
                self.orders_cache.pop(order.id)
            if self.exit_orders_cache.get(key, None):
                self.exit_orders_cache.pop(key)
            if self.order_id_tick_lookup.get(order.id, None):
                self.order_id_tick_lookup.pop(order.id)

    def add_exit_order(self, order: OptionOrder, option_tick: Tick) -> None:
        """
        Adds an exit order to the orders_cache and exit_orders_cache.
        Keyed by option_symbol for consistency with entry_orders_cache.
        """
        with self.order_lock:
            self.orders_cache[order.id] = order
            self.exit_orders_cache[self._option_key(order)] = order
            self.order_id_tick_lookup[order.id] = option_tick

    def get_entry_order(self, symbol: str, right: str = None, strike: float = None, expiry: str = None) -> Optional[OptionOrder]:
        """
        Returns the first matching entry order for symbol (and optionally right/strike/expiry).
        """
        return self._find_entry_order(symbol, strike=strike, right=right, expiry=expiry)


    def process_trade(self, trade: Trade) -> None:
        """
        Updates the state of an order based on a trade.

        Args:
            trade (Trade): The trade to process.
        """
        order_id = trade.order.orderId
        status = trade.order_status
        order: OptionOrder = self.orders_cache.get(order_id, None)

        if order is None:
            # Untracked order (e.g. squareOff / close-all MKT orders placed directly via placeOrder).
            # If it filled, emit trade_closed so the UI removes the position and records the close.
            if status == 'filled' and trade.contract is not None:
                contract = trade.contract
                logger.info(f"Untracked order {order_id} filled — emitting trade_closed for {contract.symbol}")
                exp_raw = getattr(contract, 'lastTradeDateOrContractMonth', '') or ""
                exp = str(exp_raw).replace("-", "").replace(" ", "").strip()
                sym = contract.symbol or ""
                rgt = getattr(contract, 'right', '') or ""
                key = f"{sym}_{rgt}_{exp}" if exp else f"{sym}_{rgt}"
                try:
                    import BOT
                    BOT.trade_time_dict[key] = datetime.datetime.now()
                    logger.info(f"Cooldown recorded for {key} (untracked exit)")
                except Exception:
                    pass
                _emit_trade_closed({
                    "symbol": sym,
                    "right": rgt,
                    "strike": float(getattr(contract, 'strike', 0) or 0),
                    "expiry": exp_raw,
                    "quantity": int(trade.executed_qty or 0),
                    "pnl": 0,
                    "entry_price": 0,
                    "exit_price": float(trade.average_price or 0),
                    "timestamp": datetime.datetime.now().isoformat(),
                })
            else:
                logger.error(f"Order: {order_id} not found")
            return

        logger.info(f"{status} - {order_id} - {order}")

        # Notify UI of order status change (order tracking)
        _emit_order_update(
            order_id=order_id,
            status=status,
            symbol=order.option_symbol or order.symbol or "",
            filled=trade.executed_qty,
            remaining=trade.remaining_qty,
            avg_fill_price=trade.average_price,
        )

        if status == 'inactive':
            # The order was rejected by the broker.
            order.order_status = status
            order.active = False
            logger.info(f'Order ({order_id}) {order.option_symbol} {order.order_side} {order.order_type} {order.order_qty}@{trade.order.lmtPrice} was rejected')
            _emit_log(f"ORDER REJECTED: {order.option_symbol} {order.order_side} {order.order_qty}x @ ${trade.order.lmtPrice}", "ERROR", "order")
            # self.db.delete(order=order)
            self.db.update(order=order)
        elif status in ['submitted', 'presubmitted']:
            # The order was submitted to the broker but has not been filled yet.
            order.order_status = status
            # Check for partial fills.
            if status == 'submitted' and trade.executed_qty > 0:
                order.executed_qty = trade.executed_qty
                logger.info(f'Order ({order_id}) {order.option_symbol} {order.order_side} {order.order_type} {trade.executed_qty}@{trade.last_fill_price}, Leaves: {trade.remaining_qty} was partially filled')
                _emit_log(f"PARTIAL FILL: {order.option_symbol} {trade.executed_qty}x @ ${trade.last_fill_price:.2f} (remaining: {trade.remaining_qty})", "INFO", "order")
            else:
                _emit_log(f"ORDER {status.upper()}: {order.option_symbol} {order.order_side} {order.order_qty}x @ ${order.order_price:.2f}", "INFO", "order")
            self.db.update(order=order)
        elif status in ['cancelled', 'expired']:
            # The order was cancelled or has expired.
            order.order_status = status
            order.active = False
            logger.info(f'Order ({order_id}) {order.option_symbol} {order.order_side} {order.order_type} {order.order_qty}@{order.order_price} was {status}')
            _emit_log(f"ORDER {status.upper()}: {order.option_symbol} {order.order_side} {order.order_qty}x @ ${order.order_price:.2f}", "WARN", "order")
            # self.db.delete(order=order)
            self.db.update(order=order)
        elif status == 'filled':
            # The order was filled.
            self.process_fill(trade=trade, order=order, status=status)
        else:
            logger.info(f'Unhandled message, OrderId: {order_id} - {status}')
            
    def process_fill(self, trade: Trade, order: OptionOrder, status: str) -> None:
        """
        Update an OptionOrder object with information from a Trade object and perform any necessary actions based on the order status.

        Args:
        - trade: A Trade object representing the executed trade.
        - order: An OptionOrder object representing the order to be updated.
        - status: A string representing the status of the order execution.

        Returns:
        - None

        Raises:
        - None
        """

        # Look up the corresponding Tick object for this order
        option_tick: Tick = self.order_id_tick_lookup.get(order.id, None)

        # Update the OptionOrder object with information from the Trade object
        order.order_status = status
        order.executed_qty = trade.executed_qty
        order.average_price = trade.average_price

        # Update the order in the database
        self.db.update(order=order)

        # If this was an exit order, deactivate the corresponding entry order
        if order.exit_order == True:
            # Find the corresponding entry order first (needed for cooldown key with expiry)
            entry_order: OptionOrder = self.orders_cache.get(order.ref_order_id, None)

            # Assign last trade time and record cooldown with symbol+right+expiry (matches BOT._cooldown_key)
            option_tick.last_trade_time = datetime.datetime.now()
            exp_raw = (entry_order.expiration if entry_order else None) or getattr(order, "expiration", None) or ""
            exp = str(exp_raw).replace("-", "").replace(" ", "").strip()
            key = f"{order.symbol}_{order.right}_{exp}" if exp else f"{order.symbol}_{order.right}"
            self.recent_trade_closures[key] = option_tick.last_trade_time
            logger.info(f"Cooldown recorded for {key} at {self.recent_trade_closures[key]}")

            import BOT
            BOT.trade_time_dict[key] = option_tick.last_trade_time

            # entry_order already looked up above
            logger.info(f'EXIT Order ({order.id}) [{entry_order.id if entry_order else "?"}] {order.option_symbol} {order.order_side} {order.order_type} {order.order_qty}@{order.order_price} was {status}')
            # Calculate P&L for the closed trade
            entry_avg = entry_order.average_price if entry_order else 0
            exit_avg = order.average_price if order.average_price else 0
            trade_pnl = (exit_avg - entry_avg) * order.executed_qty * 100 if entry_avg > 0 else 0
            _emit_log(
                f"EXIT FILLED: {order.option_symbol} {order.order_qty}x @ ${exit_avg:.2f} | Entry: ${entry_avg:.2f} | P&L: ${trade_pnl:+.2f}",
                "INFO", "order"
            )
            if entry_order is not None:
                option_tick.active_order = None
                entry_order.active = False

                # Notify UI that position was closed (trade_closed). Use underlying symbol to match UI positions.
                _emit_trade_closed({
                    "symbol": entry_order.symbol or entry_order.option_symbol or "",
                    "right": entry_order.right or "",
                    "strike": float(entry_order.strike or 0),
                    "expiry": entry_order.expiration or "",
                    "quantity": int(order.executed_qty or 0),
                    "pnl": float(trade_pnl),
                    "entry_price": float(entry_avg),
                    "exit_price": float(exit_avg),
                    "timestamp": datetime.datetime.now().isoformat(),
                })

                # Delete both the entry order and exit order from the database
                self.db.delete(order=entry_order)
                self.db.delete(order=order)

        # If this was an entry order, log a message with its status and notify UI
        else:
            logger.info(f'ENTRY Order ({order.id}) {order.option_symbol} {order.order_side} {order.order_type} {order.order_qty}@{order.order_price} was {status}')
            _emit_log(
                f"ENTRY FILLED: {order.option_symbol} {order.order_side} {order.order_qty}x @ ${order.average_price:.2f} | TP=${order.profit_price:.2f} SL=${order.stoploss_price:.2f}",
                "INFO", "order"
            )
            _emit_trade_executed({
                "id": int(order.id) if order.id is not None else 0,
                "symbol": order.symbol or "",
                "right": order.right or "",
                "strike": float(order.strike or 0),
                "expiry": order.expiration or "",
                "side": order.order_side or "BUY",
                "quantity": int(order.executed_qty or 0),
                "entry_price": float(order.average_price or 0),
                "price": float(order.average_price or 0),
                "status": "open",
                "timestamp": datetime.datetime.now().isoformat(),
            })


    def close_position(self, order: OptionOrder, option_tick: Tick) -> None:
        """
        Close the given position using a market order.

        Args:
            order (OptionOrder): The current position to be closed.

        Returns:
            None

        Raises:
            N/A

        Example:
            close_position(my_order)

        Notes:
            - The method determines whether to 'BUY' or 'SELL' the position based on the current order's 'order_side'.
            - The closing order is created with the given order's executed quantity and a market order type.
            - The closing order is set with a reference to the parent order that opened the position.
            - An exit order object is created and set with the closing order's details.
            - The exit order is added to the current position's exit orders.
            - The closing order details are logged and the order is placed using the API client.
        """

        # Determine whether to 'BUY' or 'SELL' the position based on the current order's 'order_side'
        action = 'BUY' if order.order_side == 'SELL' else 'SELL' 

        # Create a market order object to close the current position
        closing_order = MarketOrder(action=action, totalQuantity=order.executed_qty)
        # Route exit orders to the configured sub-account when available
        try:
            import BOT  # Imported at call time to avoid circular import issues
            sub_acct = getattr(BOT, "SUB_ACCOUNT_ID", None)
            if sub_acct:
                closing_order.account = sub_acct
        except Exception:
            # If BOT or SUB_ACCOUNT_ID is unavailable, fall back to TWS default account
            pass

        # Set unsupported attributes to False
        closing_order.eTradeOnly = False # ERROR - Id: 180, Code: 10268, Msg: The 'EtradeOnly' order attribute is not supported.
        closing_order.firmQuoteOnly = False # ERROR - Id: 178, Code: 10269, Msg: The 'FirmQuoteOnly' order attribute is not supported.

        # Set a reference to the parent order that opened the position
        closing_order.orderRef = order.id 

        # Generate an order ID for the closing order and mark the current order as 'exit_placed'
        orderId = self.api_client.nextOrderId()
        order.exit_placed = True

        # Rebuild contract if missing (e.g. order loaded from DB); required for placeOrder
        contract = order.contract
        if contract is None and self.api_client:
            contract = self.api_client.get_options_contract(
                symbol=order.symbol, expiry=order.expiration, right=order.right, strike=order.strike
            )
        if contract is None:
            logger.error(f"Close position failed: cannot get contract for order {order.id} {order.symbol}")
            return

        # Create an exit order object and set its attributes
        exit_order = create_order_obj(order_id=orderId, 
                                    symbol=order.symbol,
                                    contract=contract, 
                                    orderType=closing_order.orderType, 
                                    action=action,
                                    totalQuantity=order.executed_qty, 
                                    lmtPrice=0, 
                                    order_status="Pending")
        
        exit_order.exit_order = True
        exit_order.ref_order_id = order.id # reference to entry order
        
        try:
            # Add the exit order to the current position's exit orders
            self.add_exit_order(order=exit_order, option_tick=option_tick)

            # Log the closing order details and place the order
            logger.info(f"Close Position: ({orderId}) [{order.id}] {exit_order.option_symbol} {closing_order.orderType} {action} {closing_order.totalQuantity}@MKT")
            _emit_log(
                f"CLOSING: {exit_order.option_symbol} {action} {closing_order.totalQuantity}x @ MKT",
                "INFO", "order"
            )
            self.api_client.placeOrder(orderId, contract=contract, order=closing_order)
            self.save_order(order=exit_order)
        except Exception as ex:
            self.del_exit_order(order=exit_order, options_tick=option_tick)
            option_tick.busy = False
            logger.error(f"Placing Exit order failed: {ex}", exc_info=True)

    def check_and_close_position(self, tick: Tick) -> None:
        """
        Check if the current position should be closed based on the given tick data.

        Args:
            tick (Tick): The latest tick data for the position's underlying instrument.

        Returns:
            None

        Raises:
            N/A

        Example:
            check_and_close_position(my_tick)

        Notes:
            - The function checks if an exit order has already been placed for the current position.
            - If an exit order has already been placed, the function logs a message and returns.
            - If the current position is filled, the function checks if the take profit or stop loss conditions have been met.
            - If the take profit condition is met, the position is closed using a market order.
            - If the stop loss condition is met, the position is closed using a market order.
        """

        if tick.busy:
            return
        
        tick.busy = True
        
        try:
            order = tick.active_order
            
            # check if exit order is not already placed.
            if order is None:
                tick.busy = False
                return 

            if order.exit_placed == True:
                logger.info(f"{order.option_symbol} EXIT order already placed.")
                tick.busy = False
                return

            # check if order is already filled
            if order.order_status != "filled":
                logger.info(f"{order.option_symbol} Order not filled yet: {order.order_status}")
                tick.busy = False
                return
                
            # Valdate we have valid price data
            if tick.last <= 0 and tick.bid <= 0:
                logger.warning(f"{order.option_symbol} No valid price data available")
                tick.busy = False
                return
                
            # ✓ ADD THIS: Log comprehensive status every time we check
            self.log_order_status(order=order, tick=tick)
            
            self.check_take_profit(tick=tick, order=order, option_tick=tick)


            """if tick.active_order.order_status == "filled":
                # check take profit
                self.check_take_profit(tick=tick, order=order, option_tick=tick)"""
            
            # check stoploss
            if not order.exit_placed:
                self.check_stop_loss(last_price=tick.last, order=order, option_tick=tick)
                
        except Exception as ex:
            logger.error(f"Error in check_and_close_position for {tick.symbol}: {ex}", exc_info=True)
        finally:
            tick.busy = False

    def check_take_profit(self, tick: Tick, order: OptionOrder, option_tick: Tick) -> None:
        """
        Check if the take profit condition for the given order is met, and close the position if it is.
        Supports both Long (BUY) and Short (SELL) positions with correct exit price and conditions.

        Args:
            tick (Tick): The latest tick data for the order's underlying instrument.
            order (OptionOrder): The order to check for the take profit condition.
            option_tick (Tick): Option tick (bid/ask/last for the option contract).

        Returns:
            None

        Notes:
            - Long: exit_price = max(bid, last) — price we receive when selling. TP when price rises.
            - Short: exit_price = ask (or last) — price we pay to buy back. TP when price falls.
        """
        order_side = (order.order_side or "BUY").upper()
        is_long = order_side == "BUY"

        bid_val = option_tick.bid if option_tick.bid > 0 else -1
        ask_val = option_tick.ask if option_tick.ask > 0 else -1
        last_val = option_tick.last if option_tick.last > 0 else -1

        # Exit price: Long = what we receive (sell at bid); Short = what we pay (buy at ask)
        if is_long:
            if bid_val > 0 and last_val > 0:
                exit_price = max(bid_val, last_val)
            elif last_val > 0:
                exit_price = last_val
            elif bid_val > 0:
                exit_price = bid_val
            else:
                exit_price = -1
        else:
            if ask_val > 0 and last_val > 0:
                exit_price = min(ask_val, last_val)  # Best price we might pay to buy back
            elif ask_val > 0:
                exit_price = ask_val
            elif last_val > 0:
                exit_price = last_val
            else:
                exit_price = -1

        if exit_price <= 0:
            logger.warning(f"Invalid exit price for {order.option_symbol}: bid={bid_val}, ask={ask_val}, last={last_val}")
            return

        # 10% profit target: close when profit >= 10% of investment (whichever comes first: 10% or ATR trailing)
        try:
            inv_amount = float(order.average_price or 0) * float(order.executed_qty or 0) * 100.0
            if inv_amount > 0:
                if order_side == "BUY":
                    unrealized_profit = (exit_price - float(order.average_price or 0)) * float(order.executed_qty or 0) * 100.0
                else:
                    unrealized_profit = (float(order.average_price or 0) - exit_price) * float(order.executed_qty or 0) * 100.0
                profit_target_10pct = inv_amount * 0.10
                if unrealized_profit >= profit_target_10pct:
                    logger.info(f"✓ HIT 10% PROFIT TARGET: {order.option_symbol} — profit ${unrealized_profit:.2f} >= 10% of ${inv_amount:.2f}")
                    _emit_log(f"HIT 10% PROFIT: {order.option_symbol} — ${unrealized_profit:.2f} profit (≥10% of ${inv_amount:.2f}) — CLOSING", "INFO", "order")
                    self.close_position(order=order, option_tick=option_tick)
                    return
        except (TypeError, ValueError) as e:
            logger.debug(f"10% profit calc skipped for {order.option_symbol}: {e}")

        # Validate prices (Long: bid/last; Short: ask/last)
        if is_long and (option_tick.last == -1 or option_tick.bid == -1):
            logger.warning(f"Invalid price data for {order.option_symbol} (long): last={option_tick.last}, bid={option_tick.bid}")
            return
        if not is_long and (option_tick.last == -1 or option_tick.ask == -1):
            logger.warning(f"Invalid price data for {order.option_symbol} (short): last={option_tick.last}, ask={option_tick.ask}")
            return

        # Log current state with condition values for debugging
        if is_long:
            cond1 = exit_price >= order.current_profit_price  # Activate trailing / raise target
            close_threshold = order.current_profit_price - order.profit_increment
            cond2 = order.profit_trigger and exit_price < close_threshold  # Close on pullback
            cond1_str = f"exit>=current → trail: {cond1}"
            cond2_str = f"trigger & exit<close → close: {cond2}"
        else:
            cond1 = exit_price <= order.current_profit_price  # Activate trailing (price fell, we can buy cheap)
            close_threshold = order.current_profit_price + order.profit_increment
            cond2 = order.profit_trigger and exit_price >= close_threshold  # Close when price rose back
            cond1_str = f"exit<=current → trail: {cond1}"
            cond2_str = f"trigger & exit>=close → close: {cond2}"
        logger.info(f"TAKE PROFIT CHECK - Order({order.id}) {order.option_symbol} [{order_side}]: "
            f"Exit: ${exit_price:.2f}, Bid: ${option_tick.bid:.2f}, Ask: ${option_tick.ask:.2f}, Last: ${option_tick.last:.2f}, "
            f"Initial: ${order.profit_price:.2f}, Current: ${order.current_profit_price:.2f}, Incr: ${order.profit_increment:.2f}, "
            f"Trigger: {order.profit_trigger} | {cond1_str} | {cond2_str}")
        
        # Use the higher price, bid or last price
        #exit_price = tick.last if tick.last >= tick.bid else tick.bid
        #exit_price = option_tick.bid if option_tick.bid <= option_tick.last else option_tick.last
        
        # Log information about the exit price and the order's take profit settings
        #logger.info(f"TAKE PROFIT check_take_profit  Order({order.id}) {order.option_symbol}: Last Price: {tick.last}, Bid Price : {tick.bid}, profitPrice : {order.profit_price}, current profit price:{order.current_profit_price}, profit trigger: {order.profit_trigger}")
            
        """"if order.profit_trigger == True and exit_price <= order.current_profit_price:    
            # If the take profit condition is met, log information about the trigger and close the position
            logger.info(f"HIT TakeProfit: Order({order.id}) {order.option_symbol}: Exit Px: {exit_price}, profitPrice : {order.profit_price}, current profit price:{order.current_profit_price}, profit trigger: {order.profit_trigger}")
            self.close_position(order=order, option_tick=option_tick)
            return
            
        # Calculate next profit target
        next_profit_target = round(order.current_profit_price + order.profit_increment, 2)
            
        if exit_price >= next_profit_target:
            # If the exit price is above the current profit price, update the profit trigger and profit price settings
            order.profit_trigger = True
            old_target = order.current_profit_price
            order.current_profit_price = next_profit_target
            logger.info(f"00000000000000000000000000000 TakeProfit Triggered: Order({order.id}) {order.option_symbol}: Exit Px: {exit_price}, profitPrice : {order.profit_price}, current profit price:{order.current_profit_price}, profit trigger: {order.profit_trigger}")"""
        
        # Trailing profit: Long = price rises then trails down; Short = price falls then trails up
        if is_long:
            # Long: trigger when exit_price >= target; trail up; close when exit_price < (target - increment)
            if exit_price >= order.current_profit_price:
                if not order.profit_trigger:
                    logger.info(f" Profit Trigger ACTIVATED: Order({order.id}) {order.option_symbol}: "
                               f"${exit_price:.2f} >= ${order.current_profit_price:.2f}")
                    _emit_log(
                        f"TP TRIGGER: {order.option_symbol} — price ${exit_price:.2f} ≥ target ${order.current_profit_price:.2f} (trailing activated)",
                        "INFO", "position"
                    )
                order.profit_trigger = True
                order.current_profit_price = round(exit_price + order.profit_increment, 2)
                logger.info(f" Trailing Profit Updated: Next target: ${order.current_profit_price:.2f}")
                _emit_log(
                    f"TP TRAIL: {order.option_symbol} — new target ${order.current_profit_price:.2f} (increment ${order.profit_increment:.2f})",
                    "DEBUG", "position"
                )
                self.db.update(order=order)
                return
            if order.profit_trigger and exit_price < (order.current_profit_price - order.profit_increment):
                logger.info(f"✓ HIT Trailing TakeProfit: Order({order.id}) {order.option_symbol}: "
                           f"Exit: ${exit_price:.2f} < Trailing: ${order.current_profit_price:.2f}")
                _emit_log(
                    f"HIT TAKE PROFIT: {order.option_symbol} — exit ${exit_price:.2f} < trail ${order.current_profit_price:.2f} — CLOSING",
                    "INFO", "order"
                )
                self.close_position(order=order, option_tick=option_tick)
                return
        else:
            # Short: trigger when exit_price <= target (price fell, we can buy cheap); trail down; close when exit_price >= (target + increment)
            if exit_price <= order.current_profit_price:
                if not order.profit_trigger:
                    logger.info(f" Profit Trigger ACTIVATED: Order({order.id}) {order.option_symbol} [SHORT]: "
                               f"${exit_price:.2f} <= ${order.current_profit_price:.2f}")
                    _emit_log(
                        f"TP TRIGGER: {order.option_symbol} — price ${exit_price:.2f} ≤ target ${order.current_profit_price:.2f} (trailing activated)",
                        "INFO", "position"
                    )
                order.profit_trigger = True
                order.current_profit_price = round(exit_price - order.profit_increment, 2)
                logger.info(f" Trailing Profit Updated [SHORT]: Next target: ${order.current_profit_price:.2f}")
                _emit_log(
                    f"TP TRAIL: {order.option_symbol} — new target ${order.current_profit_price:.2f} (increment ${order.profit_increment:.2f})",
                    "DEBUG", "position"
                )
                self.db.update(order=order)
                return
            if order.profit_trigger and exit_price >= (order.current_profit_price + order.profit_increment):
                logger.info(f"✓ HIT Trailing TakeProfit: Order({order.id}) {order.option_symbol} [SHORT]: "
                           f"Exit: ${exit_price:.2f} >= Trailing: ${order.current_profit_price:.2f}")
                _emit_log(
                    f"HIT TAKE PROFIT: {order.option_symbol} — exit ${exit_price:.2f} ≥ trail ${order.current_profit_price:.2f} — CLOSING",
                    "INFO", "order"
                )
                self.close_position(order=order, option_tick=option_tick)
                return

    def check_stop_loss(self, last_price: float, order: OptionOrder, option_tick: Tick) -> None:
        """
        Checks if the stop loss condition is met for the given order.
        Long: close when exit <= SL (price fell). Short: close when exit >= SL (price rose).

        Args:
            last_price (float): The last traded price for the security.
            order (OptionOrder): The option order for which stop loss needs to be checked.
            option_tick (Tick): Option tick (bid/ask/last).

        Notes:
            - Long: exit_price = bid (sell price); close when price fell (exit <= SL).
            - Short: exit_price = ask (buy-back price); close when price rose (exit >= SL).
        """
        order_side = (order.order_side or "BUY").upper()
        is_long = order_side == "BUY"

        # Exit price: Long = bid (sell); Short = ask (buy to close)
        if is_long:
            exit_price = option_tick.bid if option_tick.bid > 0 else option_tick.last
        else:
            exit_price = option_tick.ask if option_tick.ask > 0 else option_tick.last

        if exit_price <= 0:
            logger.warning(f"Invalid exit price for {order.option_symbol}: bid={option_tick.bid}, ask={option_tick.ask}, last={option_tick.last}")
            return

        # Validate prices
        if is_long and (option_tick.last == -1 or option_tick.bid == -1):
            logger.warning(f"Invalid price data for {order.option_symbol} (long): last={option_tick.last}, bid={option_tick.bid}")
            return
        if not is_long and (option_tick.last == -1 or option_tick.ask == -1):
            logger.warning(f"Invalid price data for {order.option_symbol} (short): last={option_tick.last}, ask={option_tick.ask}")
            return

        # Long: close when exit <= SL. Short: close when exit >= SL
        sl_hit = exit_price <= order.stoploss_price if is_long else exit_price >= order.stoploss_price
        cond_str = f"exit<=SL" if is_long else f"exit>=SL"
        logger.info(f"STOPLOSS CHECK - Order({order.id}) {order.option_symbol} [{order_side}]: "
            f"Exit: ${exit_price:.2f}, Bid: ${option_tick.bid:.2f}, Ask: ${option_tick.ask:.2f}, Last: ${option_tick.last:.2f}, "
            f"StopLoss: ${order.stoploss_price:.2f} | "
            f"CONDITION ({cond_str} → close): {sl_hit} [${exit_price:.2f} {'<=' if is_long else '>='} ${order.stoploss_price:.2f}]")
        
        # Use the higher price, bid or last price
        #exit_price = option_tick.last if option_tick.last >= option_tick.bid else option_tick.bid
        #exit_price = option_tick.bid if option_tick.bid <= option_tick.last else option_tick.last
        
        # Log the current state of the order and the last traded price
        #logger.info(f"STOPLOSS check_stop_loss Order({order.id}) {order.option_symbol}: Exit Price: {exit_price}, Last Price: {option_tick.last}, Bid Price: {option_tick.bid}AuxPrice : {order.stoploss_price}")
        
        # Execute stop loss when condition is met
        if sl_hit:
            op = "≤" if is_long else "≥"
            logger.info(f"✓ HIT STOPLOSS: Order({order.id}) {order.option_symbol}: Exit ${exit_price:.2f} {op} SL ${order.stoploss_price:.2f} — CLOSING")
            _emit_log(
                f"HIT STOP LOSS: {order.option_symbol} — exit ${exit_price:.2f} {op} SL ${order.stoploss_price:.2f} — CLOSING",
                "WARN", "order"
            )
            self.close_position(order=order, option_tick=option_tick)

        # Show distance to stoploss for monitoring (positive = safe for long, negative = safe for short)
        distance_to_sl = (exit_price - order.stoploss_price) if is_long else (order.stoploss_price - exit_price)
        distance_pct = (distance_to_sl / order.order_price) * 100 if order.order_price > 0 else 0
        logger.info(f"Distance to StopLoss: ${distance_to_sl:.2f} ({distance_pct:.1f}% of entry)")

    def save_order(self, order: OptionOrder)-> None:
        self.db.put({"item_type": "new", "order": order})

    def get_orders(self)-> List[OptionOrder]:
        return self.db.orders
    
    def get_filled_orders(self, order_side: str)-> List[OptionOrder]:
        logger.info(f"get {order_side} filled order")
        filled_orders = []
        for order in self.db.orders:
            if order.order_status == 'filled' and order.order_side == order_side:
                logger.info(f"Filled Order: {order}")
                filled_orders.append(order)

        return filled_orders
        
        
    # Additional helper function for debugging
    def log_order_status(self, order: OptionOrder, tick: Tick) -> None:
        """Helper function to log comprehensive order status for debugging"""
        logger.info(f"""
        ═══════════════════════════════════════════════════════
        ORDER STATUS: {order.option_symbol}
        ═══════════════════════════════════════════════════════
        Order ID: {order.id}
        Status: {order.order_status}
        Side: {order.order_side}
        Entry Price: ${order.order_price:.2f}
        Quantity: {order.order_qty}
        Executed: {order.executed_qty}
        Avg Price: ${order.average_price:.2f}
        ───────────────────────────────────────────────────────
        CURRENT MARKET:
        Last: ${tick.last:.2f}
        Bid: ${tick.bid:.2f}
        Ask: ${tick.ask:.2f}
        Volume: {tick.volume}
        ───────────────────────────────────────────────────────
        PROFIT/LOSS TARGETS:
        Initial Profit: ${order.profit_price:.2f}
        Current Profit: ${order.current_profit_price:.2f}
        Profit Increment: ${order.profit_increment:.2f}
        Profit Trigger: {order.profit_trigger}
        StopLoss: ${order.stoploss_price:.2f}
        ───────────────────────────────────────────────────────
        P&L:
        Unrealized: ${(tick.bid - order.average_price) * order.executed_qty * 100:.2f}
        Unrealized %: {((tick.bid - order.average_price) / order.average_price * 100) if order.average_price > 0 else 0:.2f}%
        ═══════════════════════════════════════════════════════
        """)
