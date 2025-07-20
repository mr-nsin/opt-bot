import threading
import logging
from logging.handlers import RotatingFileHandler
import datetime
import os
from dataclasses import dataclass
from ibapi.wrapper import Contract, Order, OrderState


def getExpiry(EXPIRY):
    import datetime
    today = datetime.date.today()
    todayDate = today.strftime("%Y%m%d")
    friday = today + datetime.timedelta((4 - today.weekday()))
    fridayNext = today + datetime.timedelta((4 - today.weekday()) + 7)
    expiryCurr = friday.strftime("%Y%m%d")
    expiryNext = fridayNext.strftime("%Y%m%d")

    # Have current and next expiry

    # Only Current Expiry
    if EXPIRY.lower() in ["current", "next"]:
        tradeExpiry = [expiryCurr if EXPIRY.lower() == "current" else expiryNext][0]
    else:
        tradeExpiry = EXPIRY
    logger.info(f"expiry To Trade is = {tradeExpiry}")

    return tradeExpiry

def MarketOrder(action: str, totalQuantity: int)-> Order:
    """
    Creates a market order with the specified action and total quantity.

    Args:
        action (str): The order action ('BUY' or 'SELL').
        totalQuantity (int): The total quantity of the order.

    Returns:
        Order: The market order object.

    """
    order = Order()
    order.action = action
    order.totalQuantity = totalQuantity
    order.orderType = 'MKT'
    return order

@dataclass
class OptionOrder:
    id: int = None 
    conId: int = None
    symbol: str = None
    expiration: str = None
    strike: float = None
    right: str = None
    order_type: str = None
    order_side: str = None
    order_qty: int = None
    order_price: float = None
    order_status: str = None
    executed_qty: int = 0
    average_price: float = 0
    profit_price: float = None # calculated profit price
    stoploss_price: float = None # calculated stoploss (AuxPrice) price
    profit_trigger: bool = False
    current_profit_price: float = 0.0 # trailing profit
    profit_increment:float = 0.0 # profit increment until price reverses
    contract: Contract = None
    exit_placed: bool = False
    exit_order: bool = False
    active: bool = False # active untill position is closed or order rejected/cancelled.
    ref_order_id: int = None

    @property
    def option_symbol(self)-> str:
        return f"{self.symbol}{self.expiration}{self.right}{self.strike}"
    
@dataclass
class Tick:
    # conId: int = None
    symbol: str = None
    contract: Contract = None
    ask: float = -1
    bid: float = -1
    close: float = -1
    last: float = -1
    delta: float = -1
    volume: int = -1
    open_interest_call: float = -1
    open_interest_put: float = -1
    active_order: OptionOrder = None
    locked: bool = False
    last_trade_time: datetime = None
    busy: bool = False
    option_symbol: str = None

    @property
    def open_interest(self)-> float:
        if self.contract.right in ["C","CALL"]:
            return self.open_interest_call
        return self.open_interest_put
    
@dataclass
class Position:
    account: str = None
    symbol: str = None
    position: int = None
    strike: float = None
    right: str = None
    expiry: str = None

@dataclass
class Trade:
    orderId: int = 0
    contract: Contract = None
    order: Order = None
    orderStatus: OrderState = None
    executed_qty: float = None
    remaining_qty: float = None
    average_price: float = None
    last_fill_price: float = None
    order_status: str = None

def create_order_obj(order_id: int, symbol: str, contract: Contract, orderType: str, action: str, 
                        totalQuantity: float, lmtPrice:float, order_status: str,
                        profitPrice: float = 0, auxPrice: float = 0)-> OptionOrder:
    return OptionOrder(
            id= order_id, 
            symbol=symbol, 
            expiration=contract.lastTradeDateOrContractMonth,
            strike=contract.strike, 
            right=contract.right, 
            order_type=orderType, 
            order_side=action,
            order_qty=totalQuantity, 
            order_price=lmtPrice,
            order_status= order_status,
            contract=contract,
            profit_price=profitPrice,
            stoploss_price=auxPrice,
            )

def thread_id_filter(record):
    """Inject thread_id to log records"""
    record.thread_id = threading.get_native_id()
    return record

def setup_logger(name='log', console_handler=True):
    """
    Create and configure a logger for logging messages to a file and optionally to the console.

    Parameters:
        name (str): The name of the logger. Defaults to 'log'.
        console_handler (bool): Whether to add a console handler for logging messages to the console. Defaults to True.

    Returns:
        logger (logging.Logger): The configured logger object.

    """
    # Create a logger object with the given name
    logger = logging.getLogger(name=name)
    # Set the logging level to INFO
    logger.setLevel(logging.INFO)
    # Create a directory for storing log files if it doesn't exist
    logs_path = 'logs'
    if not os.path.exists(logs_path):    
        os.mkdir(logs_path)

    # Get the current date in the format 'YYYY-MM-DD'
    today = datetime.date.today().strftime("%Y-%m-%d")

    # Create a file handler with the log file name based on the logger name and current date
    handler_path = os.path.join(logs_path, f'{name}_{today}.log')
    # handler = logging.FileHandler(handler_path)
    handler = RotatingFileHandler(filename=handler_path, maxBytes=50*1024*1024, backupCount=2, encoding=None, delay=0)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(thread_id)s - %(message)s')
    set_handler_formatting(handler, formatter, logger)
    # If console_handler is True, add a console handler for logging messages to the console
    if console_handler == True:
        consoleHandler = logging.StreamHandler()
        set_handler_formatting(consoleHandler, formatter, logger)
    # Return the logger object
    return logger


# TODO Rename this here and in `setup_logger`
def set_handler_formatting(arg0, formatter, logger):
    arg0.setFormatter(formatter)
    arg0.addFilter(thread_id_filter)
    logger.addHandler(arg0)

logger = setup_logger('bot')