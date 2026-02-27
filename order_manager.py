import datetime
from typing import List, Optional
from common import MarketOrder, OptionOrder, Tick, Trade, create_order_obj, logger, Contract
from data_access import DAL
from tws_api_client import TwsApiClient

from threading import Lock



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

    def set_client(self, client: TwsApiClient) -> None:
        """
        Sets the TwsApiClient instance for the OrderManager.

        Args:
            client (TwsApiClient): The TwsApiClient instance to be set.
        """
        self.api_client = client

    def del_entry_order(self, order: OptionOrder, option_tick: Tick) -> None:
        with self.order_lock:
            if self.orders_cache.get(order.id, None):
                self.orders_cache.pop(order.id)

            if self.entry_orders_cache.get(order.symbol, None):
                self.entry_orders_cache.pop(order.symbol)

            if self.order_id_tick_lookup.get(order.id, None):
                self.order_id_tick_lookup.pop(order.id)
        

    def add_entry_order(self, order: OptionOrder, option_tick: Tick) -> None:
        """
        Adds an entry order to the orders_cache and entry_orders_cache.

        Args:
            order (OptionOrder): The entry order to be added.
        """
        with self.order_lock:
            self.orders_cache[order.id] = order
            self.entry_orders_cache[order.symbol] = order
            self.order_id_tick_lookup[order.id] = option_tick

    def del_exit_order(self, order: OptionOrder, option_tick: Tick) -> None:
        with self.order_lock:
            if self.orders_cache.get(order.id, None):
                self.orders_cache.pop(order.id)

            if self.exit_orders_cache.get(order.symbol, None):
                self.exit_orders_cache.pop(order.symbol)
 
            if self.order_id_tick_lookup.get(order.id, None):
                self.order_id_tick_lookup.pop(order.id)

    def add_exit_order(self, order: OptionOrder, option_tick: Tick) -> None:
        """
        Adds an exit order to the orders_cache and exit_orders_cache.

        Args:
            order (OptionOrder): The exit order to be added.
        """
        with self.order_lock:
            self.orders_cache[order.id] = order
            self.exit_orders_cache[order.symbol] = order
            self.order_id_tick_lookup[order.id] = option_tick

    def get_entry_order(self, symbol: str) -> Optional[OptionOrder]:
        """
        Returns the entry order associated with the given symbol from entry_orders_cache.

        Args:
            symbol (str): The symbol for which the entry order is to be retrieved.

        Returns:
            The entry order associated with the symbol, or None if the symbol is not found.
        """
        with self.order_lock:
            return self.entry_orders_cache.get(symbol, None)


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
            logger.error(f"Order: {order_id} not found")
            return

        logger.info(f"{status} - {order_id} - {order}")

        if status == 'inactive':
            # The order was rejected by the broker.
            order.order_status = status
            order.active = False
            logger.info(f'Order ({order_id}) {order.option_symbol} {order.order_side} {order.order_type} {order.order_qty}@{trade.order.lmtPrice} was rejected')
            # self.db.delete(order=order)
            self.db.update(order=order)
        elif status in ['submitted', 'presubmitted']:
            # The order was submitted to the broker but has not been filled yet.
            order.order_status = status
            # Check for partial fills.
            if status == 'submitted' and trade.executed_qty > 0:
                order.executed_qty = trade.executed_qty
                logger.info(f'Order ({order_id}) {order.option_symbol} {order.order_side} {order.order_type} {trade.executed_qty}@{trade.last_fill_price}, Leaves: {trade.remaining_qty} was partially filled')
            self.db.update(order=order)
        elif status in ['cancelled', 'expired']:
            # The order was cancelled or has expired.
            order.order_status = status
            order.active = False
            logger.info(f'Order ({order_id}) {order.option_symbol} {order.order_side} {order.order_type} {order.order_qty}@{order.order_price} was {status}')
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
            logger.info(f'99999999999999999999999 EXIT Order ({order.id}) [{entry_order.id}] {order.option_symbol} {order.order_side} {order.order_type} {order.order_qty}@{order.order_price} was {status}')
            if entry_order is not None:
                option_tick.active_order = None
                entry_order.active = False

                # Delete both the entry order and exit order from the database
                self.db.delete(order=entry_order)
                self.db.delete(order=order)

        # If this was an entry order, log a message with its status
        else:logger.info(f'ENTRY Order ({order.id}) {order.option_symbol} {order.order_side} {order.order_type} {order.order_qty}@{order.order_price} was {status}')


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

        # Generate an order ID for the closing order and mark the current order as 'exit_placed'
        orderId = self.api_client.nextOrderId()
        order.exit_placed = True

        # Create an exit order object and set its attributes
        exit_order = create_order_obj(order_id=orderId, 
                                    symbol=order.symbol,
                                    contract=order.contract, 
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
            self.api_client.placeOrder(orderId, contract=order.contract, order=closing_order)
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
        
            order.profit_trigger = True
            order.current_profit_price = round(exit_price + order.profit_increment, 2)
            logger.info(f" Trailing Profit Updated: Next target: ${order.current_profit_price:.2f}")
            self.db.update(order=order)
            return
    
        # If trigger is active and price has fallen back, close the position
        if order.profit_trigger and exit_price < (order.current_profit_price - order.profit_increment):
            logger.info(f"✓ HIT Trailing TakeProfit: Order({order.id}) {order.option_symbol}: "
                       f"Exit: ${exit_price:.2f} < Trailing: ${order.current_profit_price:.2f}")
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
