import datetime
import os
import sys
import threading
from dataclasses import dataclass
from ibapi.wrapper import Contract, Order, OrderState
from loguru import logger


def getExpiry(EXPIRY):
    import datetime
    today = datetime.date.today()
    todayDate = today.strftime("%Y%m%d")

    friday = today + datetime.timedelta((4 - today.weekday()))
    fridayNext = today + datetime.timedelta((4 - today.weekday()) + 7)
    expiryCurr = friday.strftime("%Y%m%d")
    expiryNext = fridayNext.strftime("%Y%m%d")

    if today.weekday() == 4:  # Friday
        next_trade_date = today + datetime.timedelta(days=3)  # Monday
    elif today.weekday() == 5:  # Saturday
        next_trade_date = today + datetime.timedelta(days=2)  # Monday
    else:  # Sunday to Thursday
        next_trade_date = today + datetime.timedelta(days=1)

    logger.debug(f"today - {todayDate}")
    logger.debug(f"next_trade_date - {next_trade_date}")

    # Have current and next expiry

    # Only Current Expiry
    if EXPIRY.lower() in ["current", "next"]:
        tradingExpiry = [expiryCurr if EXPIRY.lower() == "current" else expiryNext][0]
    elif "0DTE" in EXPIRY:
        tradingExpiry = todayDate
    elif "1DTE" in EXPIRY:
        tradingExpiry = next_trade_date.strftime("%Y%m%d")
    else:
        tradingExpiry = EXPIRY
    logger.info(f"expiry To Trade [config={EXPIRY}] = {tradingExpiry}")

    return tradingExpiry


def normalize_option_expiry_for_ticker(exp: str) -> str:
    """Normalize option expiry to YYYYMMDD for tick cache keys and IB contract month (no separators)."""
    if not exp:
        return ""
    raw = str(exp).strip()
    if len(raw) >= 10 and raw[4:5] == "-" and raw[7:8] == "-":
        return raw.replace("-", "").replace("/", "")[:8]
    s = raw.replace("-", "").replace("/", "").strip()
    if len(s) == 8 and s.isdigit():
        return s
    return s[:8] if len(s) >= 8 else s


def normalize_option_strike_for_ticker_key(strike) -> str:
    if strike is None:
        return ""
    try:
        return str(float(strike))
    except (TypeError, ValueError):
        return str(strike)


def normalize_option_right_for_ticker_key(right: str) -> str:
    if not right:
        return "C"
    u = str(right).strip().upper()
    if u in ("CALL", "C"):
        return "C"
    if u in ("PUT", "P"):
        return "P"
    return u[0] if u else "C"


def option_ticker_key(symbol: str, expiry: str, right: str, strike) -> str:
    sym = (symbol or "").strip()
    exp = normalize_option_expiry_for_ticker(expiry or "")
    rk = normalize_option_right_for_ticker_key(right or "")
    sk = normalize_option_strike_for_ticker_key(strike)
    return f"{sym}{exp}{rk}{sk}"


def option_ticker_key_from_contract(contract: Contract) -> str:
    if getattr(contract, "secType", "") != "OPT":
        return (getattr(contract, "symbol", None) or "").strip()
    return option_ticker_key(
        getattr(contract, "symbol", None) or "",
        getattr(contract, "lastTradeDateOrContractMonth", None) or "",
        getattr(contract, "right", None) or "",
        getattr(contract, "strike", None),
    )


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
    placed_at: str = None  # ISO timestamp when order was placed

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
    avg_cost: float = 0.0
    con_id: int = None

@dataclass
class PNL:
    account: str = None
    dailyPnL: float = None
    unrealizedPnL: float = None
    realizedPnL: float = None

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

def _loguru_patch(record):
    """Inject thread_id into loguru record (optional; format no longer requires it to avoid KeyError)."""
    extra = record.get("extra") or {}
    extra["thread_id"] = threading.get_native_id()
    record["extra"] = extra
    return record


def setup_logger(name='log', console_handler=True):
    """
    Configure loguru for file + optional console. Returns the loguru logger.
    Kept for compatibility with code that imports setup_logger.
    Logs path: when frozen (exe), use %APPDATA%\\QuantDrift\\logs on Windows for user-accessible logs.
    """
    logger.remove()
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    logs_path = os.path.join(base, "QuantDrift", "logs")
    os.makedirs(logs_path, exist_ok=True)
    today = datetime.date.today().strftime("%Y-%m-%d")
    # Format without thread_id to avoid KeyError when record comes from stdlib logging bridge
    log_format = "{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}"
    logger.patch(_loguru_patch)
    logger.add(
        os.path.join(logs_path, f'{name}_{today}.log'),
        rotation="50 MB",
        retention=2,
        level="INFO",
        format=log_format,
    )
    if console_handler:
        logger.add(sys.stderr, format=log_format, level="INFO")
    return logger


setup_logger(name='bot', console_handler=True)