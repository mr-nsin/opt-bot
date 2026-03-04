import datetime
from typing import List, Optional
from common import MarketOrder, OptionOrder, Tick, Trade, create_order_obj, logger, Contract, Position
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
        entry_orders_cache (dict): A dictionary that stores entry orders with their symbols as keys and the orders themselves as values.
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
        self._log_status_last = {}  # order_id -> last log time (throttle full status dump)
        self._LOG_STATUS_INTERVAL = 30.0  # seconds between full status logs per order

    def set_client(self, client: TwsApiClient) -> None:
        """
        Sets the TwsApiClient instance for the OrderManager.

        Args:
            client (TwsApiClient): The TwsApiClient instance to be set.
        """
        self.api_client = client

    def close_position_by_symbol(self, symbol: str, strike: float = None, right: str = None) -> None:
        """
        Close an open position by symbol (and optionally strike/right for options).
        Looks up the entry order and optional tick, then calls close_position(order, option_tick).
        """
        if not self.api_client or not self.api_client.isConnected():
            logger.warning("Cannot close position: TWS not connected")
            return
        order = self._find_entry_order(symbol, strike, right)
        if not order:
            logger.warning(f"No managed position found for symbol {symbol}" + (f" strike={strike} right={right}" if strike or right else ""))
            return
        option_tick = self.order_id_tick_lookup.get(order.id)
        if option_tick is None:
            option_tick = Tick(symbol=order.symbol, last=-1, bid=-1, ask=-1)
        self.close_position(order=order, option_tick=option_tick)

    def _find_entry_order(self, symbol: str, strike: float = None, right: str = None) -> Optional[OptionOrder]:
        """Find entry order matching symbol (and strike/right if provided). Uses 0.01 tolerance for strike."""
        def _nr(r):
            return "C" if r in ("C", "CALL") else "P" if r in ("P", "PUT") else (r or "")
        with self.order_lock:
            for o in self.entry_orders_cache.values():
                if not o or not getattr(o, "active", True):
                    continue
                if str(o.symbol or "") != str(symbol):
                    continue
                if strike is not None and abs(float(o.strike or 0) - float(strike)) >= 0.01:
                    continue
                if right is not None and right != "" and _nr(o.right) != _nr(right):
                    continue
                return o
        return None

    def close_all_positions(self) -> None:
        """
        Close all managed open positions (used by Tauri/sidecar when user clicks Close All).
        """
        if not self.api_client or not self.api_client.isConnected():
            logger.warning("Cannot close all positions: TWS not connected")
            return
        with self.order_lock:
            orders = [o for o in self.entry_orders_cache.values() if o and getattr(o, "active", True)]
        for order in orders:
            try:
                self.close_position_by_symbol(order.symbol, strike=order.strike, right=order.right)
            except Exception as ex:
                logger.error(f"Error closing position {order.option_symbol}: {ex}", exc_info=True)

    def del_entry_order(self, order: OptionOrder, option_tick: Tick) -> None:
        with self.order_lock:
            if self.orders_cache.get(order.id, None):
                self.orders_cache.pop(order.id)
            key = getattr(order, "option_symbol", None) or f"{order.symbol}{order.expiration}{order.right}{order.strike}"
            if self.entry_orders_cache.get(key, None):
                self.entry_orders_cache.pop(key)
            if self.order_id_tick_lookup.get(order.id, None):
                self.order_id_tick_lookup.pop(order.id)
            if order.id in self._log_status_last:
                self._log_status_last.pop(order.id)
        

    def add_entry_order(self, order: OptionOrder, option_tick: Tick) -> None:
        """
        Adds an entry order to the orders_cache and entry_orders_cache.
        Keyed by option_symbol to support multiple positions per underlying.
        """
        with self.order_lock:
            self.orders_cache[order.id] = order
            key = getattr(order, "option_symbol", None) or f"{order.symbol}{order.expiration}{order.right}{order.strike}"
            self.entry_orders_cache[key] = order
            self.order_id_tick_lookup[order.id] = option_tick

    def del_exit_order(self, order: OptionOrder, option_tick: Tick) -> None:
        with self.order_lock:
            if self.orders_cache.get(order.id, None):
                self.orders_cache.pop(order.id)
            key = getattr(order, "option_symbol", None) or f"{order.symbol}{order.expiration}{order.right}{order.strike}"
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
            key = getattr(order, "option_symbol", None) or f"{order.symbol}{order.expiration}{order.right}{order.strike}"
            self.exit_orders_cache[key] = order
            self.order_id_tick_lookup[order.id] = option_tick

    def get_entry_order(self, symbol: str, right: str = None) -> Optional[OptionOrder]:
        """
        Returns the first matching entry order for symbol (and right if provided).
        """
        return self._find_entry_order(symbol, right=right)


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
                _emit_trade_closed({
                    "symbol": contract.symbol or "",
                    "right": getattr(contract, 'right', '') or "",
                    "strike": float(getattr(contract, 'strike', 0) or 0),
                    "expiry": getattr(contract, 'lastTradeDateOrContractMonth', '') or "",
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
            # Assign last trade time
            option_tick.last_trade_time = datetime.datetime.now()
            key = f"{order.symbol}_{order.right}"
            self.recent_trade_closures[key] = option_tick.last_trade_time
            logger.info(f"Cooldown recorded for {key} at {self.recent_trade_closures[key]}")
            
            import BOT
            BOT.trade_time_dict[key] = option_tick.last_trade_time

            # Find the corresponding entry order and deactivate it
            entry_order: OptionOrder = self.orders_cache.get(order.ref_order_id, None)
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

        # Set unsupported attributes to False
        closing_order.eTradeOnly = False # ERROR - Id: 180, Code: 10268, Msg: The 'EtradeOnly' order attribute is not supported.
        closing_order.firmQuoteOnly = False # ERROR - Id: 178, Code: 10269, Msg: The 'FirmQuoteOnly' order attribute is not supported.

        # Set a reference to the parent order that opened the position
        closing_order.orderRef = order.id 

        if not order.executed_qty or order.executed_qty <= 0:
            logger.warning(f"Cannot close {order.option_symbol}: executed_qty={order.executed_qty} (invalid)")
            return

        orderId = self.api_client.nextOrderId()
        order.exit_placed = True

        contract = order.contract
        if contract is None and self.api_client:
            exp_norm = self._norm_expiry(order.expiration)
            contract = self.api_client.get_options_contract(
                symbol=order.symbol, expiry=exp_norm or order.expiration, right=order.right, strike=order.strike
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
            order.exit_placed = False
            self.del_exit_order(order=exit_order, options_tick=option_tick)
            option_tick.busy = False
            logger.error(f"Placing Exit order failed: {ex} — will retry on next monitor cycle", exc_info=True)

    def _norm_expiry(self, s: str) -> str:
        """Normalize expiry for matching: 2026-03-06, 20260306, 202603 6 -> 20260306."""
        if not s:
            return ""
        return str(s).replace("-", "").replace(" ", "").strip()

    def check_exit_conditions(self, pos: Position) -> None:
        """
        Check TP/SL for a TWS position. Finds the matching managed entry order and its tick,
        then delegates to check_and_close_position. Matches standalone monitor_positions_loop behavior.
        """
        if not pos or pos.position == 0:
            return
        option_tick = None
        matched_order = None
        pos_exp_norm = self._norm_expiry(pos.expiry)
        pos_strike = float(pos.strike or 0)
        pos_r = "C" if (pos.right or "").upper() in ("C", "CALL") else "P"

        with self.order_lock:
            for order in self.entry_orders_cache.values():
                if not order or order.exit_order or not getattr(order, "active", True):
                    continue
                if str(order.symbol or "") != str(pos.symbol or ""):
                    continue
                if abs(float(order.strike or 0) - pos_strike) >= 0.01:
                    continue
                right = (order.right or "").upper()
                ord_r = "C" if right in ("C", "CALL") else "P"
                if ord_r != pos_r:
                    continue
                ord_exp = self._norm_expiry(order.expiration)
                if ord_exp and pos_exp_norm and ord_exp != pos_exp_norm:
                    continue
                option_tick = self.order_id_tick_lookup.get(order.id)
                if option_tick is not None:
                    matched_order = order
                    if getattr(option_tick, "active_order", None) != order:
                        option_tick.active_order = order
                    break

        if option_tick is not None and matched_order is not None:
            try:
                self.check_and_close_position(tick=option_tick)
            except Exception as ex:
                logger.error(f"check_exit_conditions error for {pos.symbol} {pos.right}{pos.strike}: {ex}", exc_info=True)
        else:
            logger.debug(
                f"Position {pos.symbol} {pos.right} {pos.strike} {pos_exp_norm}: no matching entry order or tick "
                f"(entry_orders={len(self.entry_orders_cache)}, tick_lookup={len(self.order_id_tick_lookup)})"
            )

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

            if order is None:
                tick.busy = False
                return

            if order.exit_placed:
                logger.debug(f"{order.option_symbol} EXIT already placed — skipping")
                tick.busy = False
                return

            if order.order_status != "filled":
                logger.debug(f"{order.option_symbol} Order status={order.order_status} — waiting for fill")
                tick.busy = False
                return

            if tick.last <= 0 and tick.bid <= 0:
                logger.warning(f"{order.option_symbol} No valid price (last={tick.last} bid={tick.bid}) — skipping TP/SL check")
                tick.busy = False
                return

            # Throttled status log (every 30s per order to avoid flood with 10+ positions)
            import time as _time
            now = _time.time()
            last = self._log_status_last.get(order.id, 0)
            if now - last >= self._LOG_STATUS_INTERVAL:
                self._log_status_last[order.id] = now
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

        Args:
            tick (Tick): The latest tick data for the order's underlying instrument.
            order (OptionOrder): The order to check for the take profit condition.

        Returns:
            None

        Raises:
            N/A

        Example:
            check_take_profit(my_tick, my_order)

        Notes:
            - The function uses the higher price of the bid or last price as the exit price.
            - The function logs information about the exit price and the order's take profit settings.
            - If the take profit condition is met, the function logs information about the trigger and closes the position using the `close_position` method.
            - If the exit price is above the current profit price, the function updates the order's profit trigger and profit price settings.
        """
        
        # For SELL orders (closing longs), use BID price if available, else LAST
        # BID is what you can actually sell at RIGHT NOW
        if tick.bid > 0 and tick.bid <= tick.last:
            exit_price = tick.bid
        else:
            exit_price = tick.last

        if exit_price <= 0:
            logger.warning(f"Invalid exit price for {order.option_symbol}: bid={tick.bid}, last={tick.last}")
            return
        
        # Validate prices
        if option_tick.last == -1 or option_tick.bid == -1:
            logger.warning(f"@@@@@@@@@@@@@@@@@@@@@@@@@@@ Invalid price data for {order.option_symbol}: last={option_tick.last}, bid={option_tick.bid}")
            return
            
        # Log current state
        logger.info(f"TAKE PROFIT CHECK - Order({order.id}) {order.option_symbol}: "
            f"Exit Price: ${exit_price:.2f}, "
            f"Bid: ${tick.bid:.2f}, "
            f"Last: ${tick.last:.2f}, "
            f"Initial Profit: ${order.profit_price:.2f}, "
            f"Current Profit: ${order.current_profit_price:.2f}, "
            f"Trigger Active: {order.profit_trigger}")
        
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
        
        # OPTION 2: Trailing profit (your current approach, fixed)
        # Check if we've reached the profit target
        if exit_price >= order.current_profit_price:
            # Price is at or above profit target - set trigger and raise target
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
    
        # If trigger is active and price has fallen back, close the position
        if order.profit_trigger and exit_price < (order.current_profit_price - order.profit_increment):
            logger.info(f"✓ HIT Trailing TakeProfit: Order({order.id}) {order.option_symbol}: "
                       f"Exit: ${exit_price:.2f} < Trailing: ${order.current_profit_price:.2f}")
            _emit_log(
                f"HIT TAKE PROFIT: {order.option_symbol} — exit ${exit_price:.2f} < trail ${order.current_profit_price:.2f} — CLOSING",
                "INFO", "order"
            )
            self.close_position(order=order, option_tick=option_tick)
            return

    def check_stop_loss(self, last_price: float, order: OptionOrder, option_tick: Tick) -> None:
        """
        Checks if the last traded price has fallen below the stoploss price for the given order.
        If so, closes the position by placing a market order to exit the position.

        Args:
            last_price (float): The last traded price for the security.
            order (OptionOrder): The option order for which stop loss needs to be checked.

        Returns:
            None

        Notes:
            The function checks if the last traded price has fallen below the stoploss price for the given order. 
            If so, it closes the position by placing a market order to exit the position. The function takes in the last 
            traded price as well as the option order for which stop loss needs to be checked as arguments.
        """
        
        exit_price = option_tick.bid if option_tick.bid > 0 else option_tick.last
        
        if exit_price <= 0:
            logger.warning(f"Invalid exit price for {order.option_symbol}: bid={option_tick.bid}, last={option_tick.last}")
            return
        
        # Validate prices
        if option_tick.last == -1 or option_tick.bid == -1:
            logger.warning(f"Invalid price data for {order.option_symbol}: last={option_tick.last}, bid={option_tick.bid}")
            return
            
        # Log current state
        logger.info(f"STOPLOSS CHECK - Order({order.id}) {order.option_symbol}: "
            f"Exit Price: ${exit_price:.2f}, "
            f"Bid: ${option_tick.bid:.2f}, "
            f"Last: ${option_tick.last:.2f}, "
            f"StopLoss: ${order.stoploss_price:.2f}")
        
        # Use the higher price, bid or last price
        #exit_price = option_tick.last if option_tick.last >= option_tick.bid else option_tick.bid
        #exit_price = option_tick.bid if option_tick.bid <= option_tick.last else option_tick.last
        
        # Log the current state of the order and the last traded price
        #logger.info(f"STOPLOSS check_stop_loss Order({order.id}) {order.option_symbol}: Exit Price: {exit_price}, Last Price: {option_tick.last}, Bid Price: {option_tick.bid}AuxPrice : {order.stoploss_price}")
        
        # If the last traded price is less than or equal to the stoploss price, execute stop loss
        if exit_price <= order.stoploss_price:
            logger.info(f"11111111111111111111111111 HIT Stoploss: Order({order.id}) {order.option_symbol}: Exit Price: {exit_price}, AuxPrice: {order.stoploss_price}")
            _emit_log(
                f"HIT STOP LOSS: {order.option_symbol} — exit ${exit_price:.2f} ≤ SL ${order.stoploss_price:.2f} — CLOSING",
                "WARN", "order"
            )
            # close position
            self.close_position(order=order, option_tick=option_tick)
        
        # Show distance to stoploss for monitoring
        distance_to_sl = exit_price - order.stoploss_price
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
        
        
    def log_order_status(self, order: OptionOrder, tick: Tick) -> None:
        """Log comprehensive order status (throttled to every 30s per order; use DEBUG level to avoid flood)."""
        logger.debug(f"""
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
