import os, sys
import time, copy
import io, json
import time
import random
from typing import Optional
# import scanner
import Indicators as indi
import pandas as pd
from threading import Timer
from multiprocessing import Pool
from pathlib import Path
import base64
import signal

from concurrent.futures import ThreadPoolExecutor, as_completed

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract, ComboLeg
from ibapi.ticktype import TickTypeEnum
from ibapi.order import *
from bisect import bisect_left
# from datetime import date
import datetime
import pytz
# import MySQLdb
from datetime import datetime, timedelta
from threading import Thread, Lock
from queue import Queue, Empty
from common import OptionOrder, logger, Tick, getExpiry
from tws_api_client import TwsApiClient
from order_manager import OrderManager
from data_access import DAL
from trade_placement_audit import log_open_trade_context
from option_targets import targets_from_config

# ---- Frontend log emitter (sends logs to Tauri UI via JSON-RPC stdout) ----
# Imported conditionally because BOT.py can run standalone (legacy) or inside the sidecar.
try:
    from protocol.emitter import emit_log as _emit_log, emit_signal as _emit_signal
except ImportError:
    # Running outside sidecar (legacy mode) — stub to no-op
    def _emit_log(message, level="INFO", category="trading"):
        pass
    def _emit_signal(symbol, signal_type, strike, price, reason):
        pass

from multiprocessing import Process

_process = None

PROCESSORS_COUNT = 4

global client, client_thread, NY_TZ, event_queue, order_mgr, reconnect_time, dataStrike, signal_dict
global trade_time_dict, recent_trade_times, TRADE_COOLDOWN_SECONDS, tradeExpiry_val
global starting_profit, starting_loss
starting_profit = 0
starting_loss = 0

STOP_TRADING = False
CLOSE_ALL_IN_PROGRESS = False  # True while UI Close All runs — block new entries
DAILY_LIMIT_HIT = False
DAY_LOCKED = False
CLOSE_ALL_ORDERS = False
START_DAY_PNL = None
_signal_emit_times = {}  # throttle UI signal popups: {symbol_direction: last_emit_epoch}

import threading
_globals_lock = threading.Lock()

# Trade cooldown tracking (entry or exit)
recent_trade_times = {}  # key = f"{symbol}_{right}" → datetime
#TRADE_COOLDOWN_SECONDS = 300  # 5 minutes

client = None
client_thread = None
NY_TZ = pytz.timezone("America/New_York")
event_queue = None
order_mgr = None
reconnect_time = 10

db = None
trade_time_dict = {}
signal_dict = {}
# Per underlying + side (CALL/PUT): last close time — cooldown runs only after that side is closed, never at session start
# Per underlying: last (signal_active, direction) seen — first tick after arm is baseline only; trade on later *change* into a signal
_post_start_last_sig = {}

#def get_file_data()
filePath = os.getcwd() + "\\config.json"
with open("config.json", "r",  encoding="utf-8") as fopen:
    fileDataGet = fopen.read()
    ####### GET DATA FROM CONFIG FILE #######
    fileData = json.loads(fileDataGet)

# Connection Details - IP, PORT, ClientID
global IP, PORT, CLIENTID, SUB_ACCOUNT_ID, fetchValue, candleTime, stockListDict, stockList, dataInFile, EXPIRY, useAmount, MARKET_START_TIME, startTime, endTime, VWAP_ON_OFF, TRANSMIT, ORDER_EXPIRY_TIMER, USE_TIMER_IN_ORDER, CALL_DELTA_CHECK, PUT_DELTA_CHECK, VOLUME_CHECK, ATR_CHECKS
global ACTIVE_VOLUME, MAX_CONTRACT_AMOUNT, ATR_VALUE, SHARE_VOLUME, BODY, perDayTrades, USE_DIFF_EXPIRY_INDEX, spy_qqq_tradeExpiry, PROFIT_INCREMENT, TRADE_COOLDOWN_SECONDS, EXPIRY, tradeExpiry_val, profit_amount_day, loss_amount_day
global ADX_ON_OFF, ADX_THRESHOLD, RSI_DIVERGENCE_ON_OFF, VOLUME_DIVERGENCE_ON_OFF, LIQUIDITY_SWAP_ON_OFF, LIQUIDITY_CHECK_ON_OFF, LIQUIDITY_MIN_VOLUME, LIQUIDITY_MAX_SPREAD_PCT


# -- LICENSE SYSTEM --
LICENSE_FILE = "license.json"
LICENSE_KEY = "TraderNova_987_90_1"

def hard_exit():
    global STOP_TRADING, DAY_LOCKED, CLOSE_ALL_ORDERS
    logger.error("HARD EXIT: Daily limit hit — locking trading for the day")
    STOP_TRADING = True
    DAY_LOCKED = True
    CLOSE_ALL_ORDERS = True
    try:
        _emit_log("Daily P&L limit hit — trading locked for the day", "ERROR", "system")
    except Exception:
        pass
    
def init_day_pnl(account_id):
    global START_DAY_PNL
    START_DAY_PNL, START_REALI_DAILY_PNL = client.get_pnl(account_id)
    logger.info(f"Day PnL baseline captured: {START_REALI_DAILY_PNL}")



def encrypt_string(plain_text):
    return base64.b64encode(plain_text.encode()).decode()
    
def decrypt_string(encoded_text):
    return base64.b64decode(encoded_text.encode()).decode()

def is_license_valid(file_path: str = LICENSE_FILE) -> bool:
    try:
        if not Path(file_path).exists():
            print("License file not found/Deleted.\nPlease Contact Support Team at 'quantdrift@gmail.com'")
            time.sleep(10)
            sys.exit()
            sys.exit(0)
            sys.exit(1)
        elif Path(file_path).exists():
            print("License file present, Validating it")

        with open(file_path, "r",  encoding="utf-8") as f:
            license_data = json.load(f)

        issued_str = base64.b64decode(license_data["issued"]).decode()
        issued_date = datetime.fromisoformat(issued_str)

        now = datetime.now()
        delta = now - issued_date
        if delta.days <= 90:
            print("License is valid.")
            return True
        else:
            print("Your License has expired.\nPlease Contact Support Team at 'quantdrift@gmail.com'")
            time.sleep(20)
            sys.exit(1)

    except Exception as e:
        print("License validation error:", e)
        return False


def init_api_client(_event_queue: Queue, _order_mgr: OrderManager):
    print("calling init_api_client")
    #_client = TwsApiClient(event_queue=_event_queue, callback=_order_mgr.process_trade)
    _client = TwsApiClient(
        host=IP, port=PORT, clientId=CLIENTID,
        event_queue=_event_queue,
        callback=_order_mgr.process_trade,
        account_id=SUB_ACCOUNT_ID or "",
    )
    _client.connect(host=IP, port=PORT, clientId=CLIENTID)
    _order_mgr.set_client(client=_client)
    time.sleep(0.5)
    if _client is None or not _client.isConnected():
        logger.error("TWS not connected")
        return
    return _client
    
"""def init_api_client(_event_queue: Queue, _order_mgr: OrderManager):
    global client
    if client and client.isConnected():
        logger.info("TWS already connected.")
        return client
    
    _client = TwsApiClient(event_queue=_event_queue, callback=_order_mgr.process_trade)
    try:
        _client.connect(host=IP, port=PORT, clientId=CLIENTID)
    except Exception as e:
        logger.error(f"TWS connection failed: {e}")
        return None

    _order_mgr.set_client(client=_client)
    time.sleep(0.5)
    if not _client.isConnected():
        logger.error("TWS not connected.")
        return None

    client = _client
    return _client"""


def start_client(_client: TwsApiClient)-> None:
    print("calling start_client")
    print("_client value is = {}".format(_client))
    if _client is None or not _client.isConnected():
        logger.error("TWS not connected")
        return
    
    client_thread = Thread(target=_client.run, daemon=True)
    client_thread.start()

def getOrderExpiryTime():
    # now = datetime.datetime.now()
    now = datetime.now()
    expiryTime = now + timedelta(seconds=ORDER_EXPIRY_TIMER)
    rtnTimer = expiryTime.strftime("%H:%M:%S")

    return str(rtnTimer)

###################################################################################
############ CHANGE DB DETAILS HERE ###############################################


data = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close'])

def wwma(values, n):
    return values.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()

def _norm_right_side(right: str) -> str:
    """CALL/C → C, PUT/P → P for cooldown keys."""
    r = (right or "").strip().upper()
    if r.startswith("C"):
        return "C"
    if r.startswith("P"):
        return "P"
    return r[:1] if r else ""


def _side_cooldown_key(symbol: str, right: str) -> str:
    """Cooldown is per underlying + side only (no expiry). Timer starts when that side is closed."""
    sym = (symbol or "").strip().upper()
    return f"{sym}_{_norm_right_side(right)}"


def _cooldown_key(symbol: str, right: str, expiry: str = None) -> str:
    """Lock key: symbol+right+expiry (serializes placement per contract). Not used for trade_time_dict cooldown."""
    r = _norm_right_side(right)
    norm_exp = (expiry or "").replace("-", "").replace(" ", "").strip()
    if norm_exp:
        return f"{symbol}_{r}_{norm_exp}"
    return f"{symbol}_{r}"


# Per-key locks to prevent race: multiple event processors placing same symbol+right+expiry
_entry_placement_locks: dict = {}
_entry_placement_locks_guard = Lock()


def _get_entry_placement_lock(key: str) -> Lock:
    """Get or create a lock for the given cooldown key (symbol_right_expiry)."""
    with _entry_placement_locks_guard:
        if key not in _entry_placement_locks:
            _entry_placement_locks[key] = Lock()
        return _entry_placement_locks[key]


def arm_trading_session_gates():
    """When event processors start: reset post-start signal baselines only (cooldown is not started at session start)."""
    global _post_start_last_sig
    _post_start_last_sig.clear()
    logger.info("Session arm: per-symbol signal baseline reset (cooldown applies only after a close on that stock+side)")
    try:
        _emit_log(
            "Session start: no cooldown clock until a position closes on that stock+side; stale signals ignored until next change",
            "INFO",
            "signal",
        )
    except Exception:
        pass


def _post_start_signal_blocks_trade(sym: str, data_engulf_tuple) -> bool:
    """
    First evaluation per symbol after session arm records baseline only (no trade).
    Later, allow trading only when state *changes* into an active CALL/PUT (skips persistent pre-start patterns).
    Returns True if this tick should NOT run trade checks.
    """
    global _post_start_last_sig
    sym_u = (sym or "").upper()
    matched = bool(data_engulf_tuple[0])
    direction = (data_engulf_tuple[1] or "").upper() if matched else ""
    cur = (matched, direction)
    if sym_u not in _post_start_last_sig:
        _post_start_last_sig[sym_u] = cur
        try:
            _emit_log(
                f"{sym_u}: post-start baseline = {'none' if not matched else direction} — waiting for next signal change before trading",
                "INFO",
                "signal",
            )
        except Exception:
            pass
        return True
    prev = _post_start_last_sig[sym_u]
    if cur == prev:
        return True
    _post_start_last_sig[sym_u] = cur
    if not matched:
        try:
            _emit_log(f"{sym_u}: signal cleared — still waiting for next directional signal", "DEBUG", "signal")
        except Exception:
            pass
        return True
    try:
        _emit_log(f"{sym_u}: new signal after baseline → {direction}", "INFO", "signal")
    except Exception:
        pass
    return False


def check_TRADE_COOLDOWN_SECONDS(stockName, rightMatch, expiry: str = None) -> bool:
    """
    Check if cooldown is still active for symbol+side (CALL/PUT). Key is set only when an order on that side closes.
    Returns True if still in cooldown (should NOT place order), False if OK to trade.
    """
    key = _side_cooldown_key(stockName, rightMatch)
    last_trade_time = trade_time_dict.get(key)
    if last_trade_time is not None:
        time_since_last_trade = datetime.now() - last_trade_time
        seconds_since = int(time_since_last_trade.total_seconds())
        if seconds_since < TRADE_COOLDOWN_SECONDS:
            logger.info(f"COOLDOWN ACTIVE [{key}]: {seconds_since}s since last trade (need {TRADE_COOLDOWN_SECONDS}s)")
            try:
                _emit_log(f"Cooldown: {key} — {seconds_since}s elapsed, need {TRADE_COOLDOWN_SECONDS}s", "INFO", "signal")
            except Exception:
                pass
            return True
        return False
    return False


def getATR(df, n=21):
    dataatr = df.copy()
    high = dataatr["high"]
    low = dataatr["low"]
    close = dataatr["close"]
    dataatr["tr0"] = abs(high - low)
    dataatr["tr1"] = abs(high - close.shift())
    dataatr["tr2"] = abs(low - close.shift())
    tr = dataatr[['tr0', 'tr1', 'tr2']].max(axis=1)
    return wwma(tr, n)

def take_closest(myList, myNumber):
    pos = bisect_left(myList, myNumber)
    if pos == 0:
        return myList[0]
    if pos == len(myList):
        return myList[-1]
    before = myList[pos - 1]
    after = myList[pos]
    return after if after - myNumber < myNumber - before else before

def returnLowHigh(stirkeList, CurrentPrice):
    low = 0
    high = 0
    for _ in range(1, len(stirkeList) + 1):
        fv = take_closest(sorted(stirkeList), CurrentPrice)
        if low == 0 and fv < CurrentPrice:
            low = fv
            stirkeList.remove(low)
        elif high == 0 and fv > CurrentPrice:
            high = fv
            stirkeList.remove(high)
        elif low == 0 or high == 0:
            stirkeList.remove(fv)
        else:
            break
    return low, high

def placeOrder(symbol, expiry=None, strike=None, right=None, action=None,
                totalQuantity=None, orderType=None, lmtPrice=0, auxPrice=0, 
                profitPrice=0, conIdDetails=None, legPrices=None, 
                options_tick: Tick = None,
                stock_tick:Tick = None, placement_context=None,
                closing_order: bool = False, is_sqare_off=False,
                max_tp_price=None, min_sl_price=None, underlying_atr=None):
                    
    if DAY_LOCKED and CLOSE_ALL_ORDERS and not (closing_order or is_sqare_off):
        logger.warning("Trading blocked: DAY LOCK active (PnL limit hit)")
        return "DayLocked"
    if globals().get("CLOSE_ALL_IN_PROGRESS", False) and not (closing_order or is_sqare_off):
        logger.warning("Trading blocked: Close All in progress")
        return "CloseAllInProgress"

    option_order = None

    logger.info("Checking for Order Place condition")

    logger.info("Order Data 1 ")
    
    if not (closing_order or is_sqare_off):
        open_order = order_mgr.get_entry_order(symbol=symbol, right=right, expiry=expiry)
        norm_right = right[0].upper() if right else right
        if open_order is not None and open_order.active and (open_order.right or "")[0:1].upper() == norm_right:
            logger.info(f"Order already present for Stock TTT = {symbol} Get Right is = {right} and open_order right is = {open_order.right}")
            logger.info(f"Open Order data is = {open_order}")
            return "OrderAlreadyPresent"

    logger.info("Enter order")
    logger.info("\n\nOrder Details\n\n")
    logger.info(f"LOGS:ORDER_PLACE -> Stock = {symbol}\nAction = {action}\nOrderType = {orderType}\nQuantity = {totalQuantity}\nLMT Price = {lmtPrice}\nProfit Price = {profitPrice}\nSL Price = {auxPrice}\n\n")

    # orderExryTimer = getOrderExpiryTime()
    contract = client.get_options_contract(symbol, expiry, right, strike)
    order = Order()
    order.action = action
    order.totalQuantity = int(totalQuantity)
    order.orderType = orderType
    order.lmtPrice = str(lmtPrice)
    # Route orders explicitly to the configured sub-account when provided
    try:
        if SUB_ACCOUNT_ID:
            order.account = SUB_ACCOUNT_ID
    except NameError:
        # SUB_ACCOUNT_ID not initialized yet; fall back to TWS default account
        pass
    if str(auxPrice) != "0":
        order.auxPrice = str(auxPrice)
    if USE_TIMER_IN_ORDER.lower() == "on" and not closing_order:
        logger.info(f"\n USE_TIMER_IN_ORDER is ON for stock = {symbol}\n")
        orderExryTimer = getOrderExpiryTime()
        order.tif = "GTD"
        #order.tif = "DAY"
        order.goodTillDate = orderExryTimer
    nextorderId = client.nextOrderId()
    order.orderId = nextorderId
    nextorderId += 1
    order.eTradeOnly = False
    order.firmQuoteOnly = False

    if not closing_order:
        option_order = OptionOrder(
            id= order.orderId, 
            symbol=symbol, 
            expiration=expiry,
            strike=strike, 
            right=right, 
            order_type=orderType, 
            order_side=action,
            order_qty=totalQuantity, 
            order_price=lmtPrice,
            order_status="Pending",
            contract=contract,
            profit_price=profitPrice,
            stoploss_price=auxPrice,
            current_profit_price=profitPrice,
            profit_increment=PROFIT_INCREMENT,
            profit_trigger=False,
            active=True,
            max_tp_price=max_tp_price,
            min_sl_price=min_sl_price,
            underlying_atr=underlying_atr)

        logger.info(f"Created option_order: {option_order}")
        logger.info(f"Profit settings - Target: ${profitPrice:.2f}, Increment: ${PROFIT_INCREMENT:.2f}, StopLoss: ${auxPrice:.2f}")


    """if not client.isConnected():
        # raise ConnectionError("Some Error in API connection. Closing Scripts. Please Look Manually for the placed order.")
        logger.error("Some Error in API connection.")
        return "TWS API connection error"""
        
    if not client.isConnected():
        logger.warning("Client disconnected. Trying to reconnect...")
        client.try_reconnect()
        if not client.isConnected():
            return "TWS API connection error"
    
    try:
        if not closing_order and option_order:
            logger.info("Adding entry order")
            options_tick.active_order = option_order
            order_mgr.add_entry_order(option_order, option_tick=options_tick)

        #order_mgr.add_entry_order(option_order, option_tick=options_tick)
        logger.info("ORDER ON PLACE")

        client.placeOrder(order.orderId, contract, order)
        logger.info("\n<NEW ORDER> PLACED SUCCESSFULLY\n")
        if option_order is not None:
            order_mgr.save_order(order=option_order)
            _emit_log(
                f"ORDER PLACED: {symbol} {right} {strike} {action} {totalQuantity}x @ ${lmtPrice:.2f} ({orderType}) | TP=${profitPrice:.2f} SL=${auxPrice:.2f}",
                "INFO", "order"
            )
            _emit_signal(symbol, right or "", float(strike or 0), float(lmtPrice or 0),
                         f"{action} {orderType} — TP=${profitPrice:.2f} SL=${auxPrice:.2f}")
            try:
                audit = {
                    "event": "open_order_placed",
                    "order_id": order.orderId,
                    "symbol": symbol,
                    "expiry": expiry,
                    "strike": strike,
                    "right": right,
                    "action": action,
                    "quantity": int(totalQuantity),
                    "order_type": orderType,
                    "limit_price": float(lmtPrice) if lmtPrice is not None else None,
                    "take_profit_price": float(profitPrice) if profitPrice is not None else None,
                    "stop_loss_price": float(auxPrice) if auxPrice is not None else None,
                    "max_tp_trailing_cap": float(max_tp_price) if max_tp_price is not None else None,
                    "min_sl_floor": float(min_sl_price) if min_sl_price is not None else None,
                    "underlying_atr": float(underlying_atr) if underlying_atr is not None else None,
                }
                if placement_context is not None:
                    audit["placement_context"] = placement_context
                log_open_trade_context(audit)
            except Exception as audit_ex:
                logger.warning("trade_open_context.jsonl audit enqueue failed: {}", audit_ex)
        elif closing_order:
            _emit_log(f"EXIT ORDER: {symbol} {right} {strike} {action} {totalQuantity}x @ MKT", "INFO", "order")
        
        # FIX: Unlock the tick after successful order
        if options_tick:
            options_tick.locked = False

        return order.orderId
    except Exception as ex:
        if not closing_order and option_order:
            if options_tick:
                options_tick.active_order = None
            order_mgr.del_entry_order(order=option_order, option_tick=options_tick)
            
        # FIX: Unlock the tick after successful order
        if options_tick:
            options_tick.locked = False

        #order_mgr.del_entry_order(order=option_order, option_tick=options_tick)
        logger.error(f"Error in Placing Order: {ex}", exc_info=True)
        return None


def placeAndVerifyOrder(symbol, expiry=None, strike=None, right=None, action=None,
                        totalQuantity=None, orderType=None, lmtPrice=0, auxPrice=0, 
                        profitPrice=0, conIdDetails=None, legPrices=None,                         options_tick: Tick=None,
                        stock_tick: Tick=None, placement_context=None,
                        max_tp_price=None, min_sl_price=None, underlying_atr=None):
                            
    if DAY_LOCKED and CLOSE_ALL_ORDERS:
        logger.warning("Trading blocked: DAY LOCK active (PnL limit hit)")
        return "DayLocked"
    if globals().get("CLOSE_ALL_IN_PROGRESS", False):
        logger.warning("Trading blocked: Close All in progress")
        return "CloseAllInProgress"

    if options_tick is None:
        logger.error("placeAndVerifyOrder: options_tick is required")
        return "error"

    # Per-key lock serializes placement for same symbol+right+expiry; no need for options_tick.locked
    # (options_tick.locked caused spurious "optionsTickLocked" when multiple event processors contended)
    key = _cooldown_key(symbol, right, expiry)
    entry_lock = _get_entry_placement_lock(key)
    entry_lock.acquire()
    logger.info("Creating Orders")
    
    try:
        if options_tick.active_order != None and options_tick.active_order.order_status in ["Pending", "submitted"]:
            return "orderAlreadyPresent"
        
        side_key = _side_cooldown_key(symbol, right)
        last_trade_time = trade_time_dict.get(side_key)

        if last_trade_time:
            seconds_since = (datetime.now() - last_trade_time).total_seconds()
            if seconds_since < TRADE_COOLDOWN_SECONDS:
                logger.info(f"COOLDOWN ACTIVE [{side_key}]: Trade skipped — {int(seconds_since)}s since last close on this side (need {TRADE_COOLDOWN_SECONDS}s)")
                try:
                    _emit_log(f"Cooldown: {side_key} — {int(seconds_since)}s since close, need {TRADE_COOLDOWN_SECONDS}s — order blocked", "INFO", "order")
                except Exception:
                    pass
                return "cooldownPeriodHit"

        result =  placeOrder(symbol=symbol, 
                        expiry=expiry, 
                        strike=strike, 
                        right=right, 
                        action=action,
                        totalQuantity=totalQuantity, 
                        orderType=orderType, 
                        lmtPrice=lmtPrice, 
                        auxPrice=auxPrice, 
                        profitPrice=profitPrice, 
                        conIdDetails=conIdDetails,
                        legPrices=legPrices, 
                        options_tick=options_tick,
                        stock_tick=stock_tick,
                        placement_context=placement_context,
                        max_tp_price=max_tp_price,
                        min_sl_price=min_sl_price,
                        underlying_atr=underlying_atr)
        return result
    except Exception as ex:
        logger.error(f"Error in placeAndVerifyOrder: {ex}", exc_info=True)
        return "error"
    finally:
        entry_lock.release()

def get_signal_dataframe_for_stock(stock, limit=21, indicator="supertrend"):
    """
    Get a pandas DataFrame with signals for current and previous candles for a stock.
    Returns DataFrame with columns: symbol, date, open, high, low, close, volume, signal (ST_BUY_SELL).
    Returns None if insufficient data.
    """
    if client is None:
        return None
    getCandlesData = client.get_bars(stock=stock, barSize=candleTime, limit=limit)
    if getCandlesData is None or len(getCandlesData) < limit:
        return None
    if indicator != "supertrend":
        return None
    new_dict = {
        "Date": [x.date for x in getCandlesData],
        "Open": [getattr(x, "open", x.close) for x in getCandlesData],
        "High": [x.high for x in getCandlesData],
        "Low": [x.low for x in getCandlesData],
        "Close": [x.close for x in getCandlesData],
        "Volume": [getattr(x, "volume", 0) for x in getCandlesData],
    }
    new_df = pd.DataFrame(new_dict)
    super_trend_signal = indi.BOTSingal(new_df)
    result = super_trend_signal[["Date", "Open", "High", "Low", "Close", "Volume", "ST_BUY_SELL"]].copy()
    result.rename(columns={"ST_BUY_SELL": "signal"}, inplace=True)
    result["symbol"] = stock
    result["date"] = result["Date"].apply(lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x))
    return result[["symbol", "date", "Open", "High", "Low", "Close", "Volume", "signal"]]


def scan_all_stocks_signals(system_start_time=None, limit=21):
    """
    Scan each stock in stockList and return a combined list of signal rows (JSON-serializable).
    Each row: symbol, date, open, high, low, close, volume, signal.
    If system_start_time is set, only includes candles with date >= system_start_time
    (signals from the time system started, including current candle at start).
    """
    rows = []
    for stock in (stockList or []):
        try:
            df = get_signal_dataframe_for_stock(stock, limit=limit)
            if df is None or df.empty:
                continue
            for _, r in df.iterrows():
                candle_date = r.get("Date") or r.get("date")
                if candle_date is None:
                    continue
                if system_start_time is not None:
                    try:
                        if hasattr(candle_date, "timestamp"):
                            ts = candle_date.timestamp()
                        elif hasattr(candle_date, "replace") and hasattr(candle_date, "tzinfo"):
                            ts = candle_date.timestamp()
                        else:
                            ts = 0
                        start_ts = system_start_time.timestamp() if hasattr(system_start_time, "timestamp") else float(system_start_time or 0)
                        if ts < start_ts:
                            continue
                    except Exception:
                        pass
                date_str = candle_date.isoformat() if hasattr(candle_date, "isoformat") else str(candle_date)
                rows.append({
                    "symbol": stock,
                    "date": date_str,
                    "open": float(r.get("Open", 0)),
                    "high": float(r.get("High", 0)),
                    "low": float(r.get("Low", 0)),
                    "close": float(r.get("Close", 0)),
                    "volume": int(r.get("Volume", 0)),
                    "signal": str(r.get("signal", "NA")),
                })
        except Exception as ex:
            logger.warning(f"scan_all_stocks_signals: {stock} failed: {ex}")
            continue
    return rows


def _check_engulfing_patterns(getCandlesData, stock):
    """
    Check for bullish/bearish engulfing patterns.
    Returns (matched, right, strength, pattern_id) or (False, None, None, None).
    Used by getCallPutEngulfCheck for combined SuperTrend+Engulfing mode.
    pattern_id matches the engulf-only branch labels in getCallPutEngulfCheck (for audit logs).
    """
    if getCandlesData is None or len(getCandlesData) < 8:
        return (False, None, None, None)
    last2Candles = getCandlesData[1:8]
    candle_0, candle_1, candle_2, candle_3, candle_4, candle_5, candle_6 = (
        last2Candles[0], last2Candles[1], last2Candles[2], last2Candles[3],
        last2Candles[4], last2Candles[5], last2Candles[6])
    candle_0_vol = int(candle_0.volume)
    candle_1_vol = int(candle_1.volume)
    candle_2_vol = int(candle_2.volume)
    candle_3_vol = int(candle_3.volume)
    candle_4_vol = int(candle_4.volume)
    candle_5_vol = int(candle_5.volume)
    candle_6_vol = int(candle_6.volume)
    candle_0_close = float(candle_0.close)
    candle_1_close = float(candle_1.close)
    candle_2_close = float(candle_2.close)
    candle_3_close = float(candle_3.close)
    candle_4_close = float(candle_4.close)
    candle_5_close = float(candle_5.close)
    candle_6_close = float(candle_6.close)
    candle_0_open = float(candle_0.open)
    candle_1_open = float(candle_1.open)
    candle_3_open = float(candle_3.open)
    candle_4_open = float(candle_4.open)
    candle_5_open = float(candle_5.open)
    candle_6_open = float(candle_6.open)
    candle_1_high, candle_1_low = float(candle_1.high), float(candle_1.low)
    candle_3_high, candle_3_low = float(candle_3.high), float(candle_3.low)
    candle_4_high, candle_4_low = float(candle_4.high), float(candle_4.low)
    candle_5_high, candle_5_low = float(candle_5.high), float(candle_5.low)
    candle_6_high, candle_6_low = float(candle_6.high), float(candle_6.low)
    # Bullish (CALL) patterns
    if candle_6_close >= candle_5_close and (candle_5_close >= candle_4_open or candle_5_close >= candle_4_high or candle_5_close >= candle_4_close) and candle_4_close <= candle_3_close and candle_6_vol >= candle_5_vol*0.65 and candle_5_vol >= candle_4_vol*0.65:
        return (True, "CALL", "strongBuy", "engulf_CALL_3c_pure_bullish_A_strongBuy")
    if candle_6_close >= candle_5_close and (candle_5_close >= candle_4_open or candle_5_close >= candle_4_high or candle_5_close >= candle_4_close) and candle_4_close <= candle_3_close and candle_5_vol >= candle_4_vol*0.65 and (candle_6_vol >= candle_5_vol*1.2 or candle_6_vol >= candle_4_vol*1.2):
        return (True, "CALL", "heavyBuy", "engulf_CALL_3c_pure_bullish_A_heavyBuy")
    if (candle_6_close >= candle_5_open or candle_6_close >= candle_5_high) and (candle_5_close <= candle_4_close or (candle_5_high+candle_5_low)/2 <= candle_4_close) and (candle_4_close <= candle_3_close or (candle_4_high+candle_4_low)/2 <= candle_3_close) and candle_6_vol >= candle_5_vol*0.65:
        return (True, "CALL", "strongBuy", "engulf_CALL_4c_pure_bullish_B_strongBuy")
    if (candle_6_close >= candle_5_open or candle_6_close >= candle_5_high) and (candle_5_close <= candle_4_close or (candle_5_high+candle_5_low)/2 <= candle_4_close) and (candle_4_close <= candle_3_close or (candle_4_high+candle_4_low)/2 <= candle_3_close) and candle_6_vol >= candle_5_vol*1.25:
        return (True, "CALL", "heavyBuy", "engulf_CALL_4c_pure_bullish_B_heavyBuy")
    if candle_6_close >= candle_5_close and candle_5_close >= candle_5_open and (candle_5_open-candle_5_low >= (candle_5_close-candle_5_open)*2) and (candle_5_high-candle_5_open <= candle_5_close-candle_5_open) and (candle_6_vol >= candle_5_vol*0.65 and candle_5_vol >= candle_4_vol*0.85):
        return (True, "CALL", "strongBuy", "engulf_CALL_3c_hammer_C_strongBuy")
    if candle_6_close >= candle_5_close and candle_5_close >= candle_5_open and (candle_5_open-candle_5_low >= (candle_5_close-candle_5_open)*2) and (candle_5_high-candle_5_open <= candle_5_close-candle_5_open) and candle_5_vol >= candle_4_vol*1.05 and candle_6_vol >= candle_5_vol*0.55:
        return (True, "CALL", "heavyBuy", "engulf_CALL_3c_hammer_C_heavyBuy")
    if (candle_6_close >= candle_4_open or candle_6_close >= candle_4_high) and candle_4_open >= candle_4_close and (candle_5_vol >= candle_4_vol*0.65 and candle_6_vol >= candle_5_vol*0.55 and candle_6_vol >= candle_4_vol*0.5):
        return (True, "CALL", "normalBuy", "engulf_CALL_D_normalBuy")
    if (candle_6_close >= candle_4_open or candle_6_close >= candle_4_high) and candle_4_open >= candle_4_close and (candle_5_vol > candle_4_vol*0.55 and candle_6_vol >= candle_4_vol*0.52 and candle_6_vol >= candle_5_vol*0.55):
        return (True, "CALL", "mediumBuy", "engulf_CALL_D_hvy_vol_mediumBuy")
    if (candle_6_close >= candle_3_open or candle_6_close >= candle_3_high) and candle_3_open >= candle_3_close and (candle_4_open <= candle_3_open or candle_4_open <= candle_3_high) and (candle_5_open <= candle_3_open or candle_5_open <= candle_3_high) and (candle_6_vol >= candle_3_vol*0.6 and candle_4_vol >= candle_3_vol*0.55 and candle_5_vol <= candle_3_vol*0.6):
        return (True, "CALL", "mediumBuy", "engulf_CALL_E_mediumBuy")
    # High volume engulf (CALL): merge from main — volume surge 1.5x+
    if candle_6_close >= candle_5_close and candle_5_close >= candle_4_close and candle_4_close <= candle_3_close and candle_6_vol >= candle_5_vol*1.5 and candle_6_vol >= candle_4_vol*1.3:
        return (True, "CALL", "heavyBuy", "engulf_CALL_high_vol_super")
    recent_low = min(candle_4_low, candle_5_low)
    if candle_6_low < recent_low and candle_6_close > recent_low and candle_6_close > (candle_6_high + candle_6_low)/2 and candle_6_vol >= candle_5_vol*1.5:
        return (True, "CALL", "heavyBuy", "engulf_CALL_liquidity_swap")
    # Bearish (PUT) patterns
    if candle_6_close <= candle_4_open and candle_6_close <= candle_5_open and candle_5_high >= candle_4_high and candle_6_close <= candle_5_low and candle_6_vol >= candle_5_vol*0.85 and candle_6_vol >= candle_4_vol*0.8:
        return (True, "PUT", "mediumSell", "engulf_PUT_A_mediumSell")
    if candle_6_close <= candle_5_open and candle_6_open >= candle_5_close and candle_6_open >= candle_5_high and candle_6_close <= candle_5_low and candle_6_vol >= candle_5_vol*0.85 and candle_6_vol <= candle_5_vol*1.25:
        return (True, "PUT", "strongSell", "engulf_PUT_B_strongSell")
    if candle_6_close <= candle_5_open and candle_6_close <= candle_4_open and candle_6_close <= candle_3_open and candle_6_vol >= candle_5_vol*0.8:
        return (True, "PUT", "mediumSell", "engulf_PUT_B_hvy_vol_mediumSell")
    # High volume engulf (PUT): merge from main
    if candle_6_close <= candle_5_close and candle_5_close <= candle_4_close and candle_4_close >= candle_3_close and candle_6_vol >= candle_5_vol*1.5 and candle_6_vol >= candle_4_vol*1.3:
        return (True, "PUT", "strongSell", "engulf_PUT_high_vol_super")
    recent_high = max(candle_4_high, candle_5_high)
    if candle_6_high > recent_high and candle_6_close < recent_high and candle_6_close < (candle_6_high + candle_6_low)/2 and candle_6_vol >= candle_5_vol*1.5:
        return (True, "PUT", "strongSell", "engulf_PUT_liquidity_swap")
    if (candle_2_close <= candle_3_close or candle_2_close > candle_3_close) and (candle_1_close >= candle_2_close or candle_1_close < candle_2_close) and (candle_0_open >= candle_1_close or candle_0_open < candle_1_close) and (candle_0_close < candle_1_low) and candle_1_vol >= candle_0_vol*0.8:
        return (True, "PUT", "normalSell", "engulf_PUT_chain_normalSell")
    return (False, None, None, None)


def getCallPutEngulfCheck(stock, limit=21, indicator="engulfing"):
    from datetime import datetime
    logger.info(f"Checking BEARISH OR BULLISH Engulf Data for stock = {stock}")
    _emit_log(f"Signal check: {stock} (need {limit} bars, indicator={indicator})", "DEBUG", "signal")

    getCandlesData = client.get_bars(stock=stock, barSize=candleTime, limit=limit)
    n_bars = len(getCandlesData) if getCandlesData else 0
    if getCandlesData is None or n_bars < limit:
        _emit_log(f"IBKR bars: {stock} received {n_bars} bars (need {limit}) — {'no data' if not getCandlesData else 'insufficient'}", "INFO", "data")
    else:
        _emit_log(f"IBKR bars: {stock} received {n_bars} bars → computing {indicator}", "DEBUG", "data")
    
    #############################################################################################################################################################################
    #############################################################################################################################################################################
    if indicator == "supertrend":
        if getCandlesData is None:
            return False, "None", stock, "notrade", None

        if len(getCandlesData) < limit:
            logger.info(f"{stock} not enough candles.")
            logger.info(f"\n Received Candles for stocks= {stock} are = {getCandlesData}\n")
            return False, "None", stock, "notrade", None
            
        new_dict = {
            "Date":[x.date for x in getCandlesData],
            "Close":[x.close for x in  getCandlesData],
            "High": [x.high for x in getCandlesData], 
            "Low": [x.low for x in getCandlesData] ,
        }
        new_df = pd.DataFrame(new_dict);
        super_trend_signal = indi.BOTSingal(new_df)[["Date","Close","ST_BUY_SELL"]]
        
        logger.info("stock = {}, signal is = {}***\n".format(stock, super_trend_signal))
        logger.info("#####*********\nstock = {}, current signal is = {} and last signal is = {}***\n".format(stock, super_trend_signal["ST_BUY_SELL"][::-1].iloc[0], super_trend_signal["ST_BUY_SELL"][::-1].iloc[1]))
        
        ############################################################################################################################################################    
        ################# WE ARE UPDATING SIGNAL OF LAST CLOSED CANDLE SO CURRENT CANDLE IS DEPEND ON PREVIOUS CANDLE TO TRADE #####################################
        ############################################################################################################################################################
        
        signal_dict[stock]['last_signal'] = super_trend_signal["ST_BUY_SELL"][::-1].iloc[1]
        signal_dict[stock]['current_signal'] = super_trend_signal["ST_BUY_SELL"][::-1].iloc[0]
        logger.info("Updated signal_dict = {}".format(signal_dict))

        current_sig = signal_dict[stock]['current_signal']
        last_sig = signal_dict[stock]['last_signal']
        
        if last_sig != current_sig:
            logger.info("Signal Match for stock = {} and trade signal is = {}".format(stock, current_sig))
            _emit_log(f"SuperTrend FLIP: {stock} {last_sig}→{current_sig} (signal change detected)", "INFO", "signal")
            trade_value = "trade"
        else:
            _emit_log(f"SuperTrend: {stock} signal={current_sig} (no change)", "DEBUG", "signal")

        right = "CALL"
        if current_sig.lower() == "sell":
            right = "PUT"
        _emit_log(f"Signal result: {stock} → {right} ({indicator} OK)", "INFO", "signal")
        st_rows = _super_trend_signal_df_to_records(super_trend_signal)
        audit = _signal_path_audit_bundle(
            stock, indicator, limit, getCandlesData,
            extra={
                "mode": "supertrend_only",
                "super_trend_dataframe": st_rows,
                "botsignal_input_columns": {
                    "Date": [str(x) for x in new_dict["Date"]],
                    "Close": [float(x) for x in new_dict["Close"]],
                    "High": [float(x) for x in new_dict["High"]],
                    "Low": [float(x) for x in new_dict["Low"]],
                },
                "signal_dict_last": str(last_sig),
                "signal_dict_current": str(current_sig),
                "supertrend_flip": bool(last_sig != current_sig),
                "note": "indicator=supertrend: no engulf filter in this branch",
            },
        )
        return True, right, stock, "strongBuy", audit
    elif indicator == "both":
        # Combined: SuperTrend for direction + Engulfing as filter. Signal only when BOTH agree.
        if getCandlesData is None or len(getCandlesData) < limit:
            return False, "None", stock, "notrade", None
        if stock not in signal_dict:
            signal_dict[stock] = {"last_signal": "", "current_signal": ""}
        new_dict = {
            "Date": [x.date for x in getCandlesData],
            "Close": [x.close for x in getCandlesData],
            "High": [x.high for x in getCandlesData],
            "Low": [x.low for x in getCandlesData],
        }
        new_df = pd.DataFrame(new_dict)
        super_trend_signal = indi.BOTSingal(new_df)[["Date", "Close", "ST_BUY_SELL"]]
        signal_dict[stock]["last_signal"] = super_trend_signal["ST_BUY_SELL"][::-1].iloc[1]
        signal_dict[stock]["current_signal"] = super_trend_signal["ST_BUY_SELL"][::-1].iloc[0]
        current_sig = signal_dict[stock]["current_signal"]
        last_sig = signal_dict[stock]["last_signal"]
        if last_sig != current_sig:
            st_right = "CALL" if current_sig.lower() != "sell" else "PUT"
            engulf_matched, engulf_right, engulf_strength, engulf_pattern_id = _check_engulfing_patterns(getCandlesData, stock)
            if engulf_matched and engulf_right == st_right:
                _emit_log(f"SuperTrend+Engulfing CONFIRMED: {stock} → {st_right} ({engulf_strength})", "INFO", "signal")
                st_rows = _super_trend_signal_df_to_records(super_trend_signal)
                audit = _signal_path_audit_bundle(
                    stock, indicator, limit, getCandlesData,
                    extra={
                        "mode": "supertrend_plus_engulfing",
                        "super_trend_dataframe": st_rows,
                        "botsignal_input_columns": {
                            "Date": [str(x) for x in new_dict["Date"]],
                            "Close": [float(x) for x in new_dict["Close"]],
                            "High": [float(x) for x in new_dict["High"]],
                            "Low": [float(x) for x in new_dict["Low"]],
                        },
                        "signal_dict_last": str(last_sig),
                        "signal_dict_current": str(current_sig),
                        "supertrend_derived_right": st_right,
                        "engulfing_matched": True,
                        "engulfing_pattern_id": engulf_pattern_id,
                        "engulfing_right": engulf_right,
                        "engulfing_strength": engulf_strength,
                    },
                )
                return True, st_right, stock, engulf_strength or "strongBuy", audit
            else:
                _emit_log(f"SuperTrend flip {stock} → {st_right} but engulfing {'no match' if not engulf_matched else f'says {engulf_right}'} — skipping", "DEBUG", "signal")
                return False, "None", stock, "notrade", None
        _emit_log(f"SuperTrend: {stock} signal={current_sig} (no change)", "DEBUG", "signal")
        return False, "None", stock, "notrade", None
    else:
        if getCandlesData is None:
            return False, "None", stock, "notrade", None

        if len(getCandlesData) < 8:
            logger.info(f"{stock} not enough candles.")
            logger.info(f"\n Received Candles for stocks= {stock} are = {getCandlesData}\n")
            _emit_log(f"IBKR bars: {stock} received {len(getCandlesData) if getCandlesData else 0} bars (need 8 for engulfing)", "INFO", "data")
            return False, "None", stock, "notrade", None
        
        last2Candles = getCandlesData[1:8]
        logger.info(f"Last 7 candles data 1st is = {last2Candles}")
        
        candle_0 = last2Candles[0]
        candle_1 = last2Candles[1]
        candle_2 = last2Candles[2]
        candle_3 = last2Candles[3]
        candle_4 = last2Candles[4]
        candle_5 = last2Candles[5]
        candle_6 = last2Candles[6]
        
        # candle_0_range = round((float(candle_0.high) - float(candle_0.low)), 3)
        # candle_1_range = round((float(candle_1.high) - float(candle_1.low)), 3)
        # candle_2_range = round((float(candle_2.high) - float(candle_2.low)), 3)
        # candle_3_range = round((float(candle_3.high) - float(candle_3.low)), 3)
        
        candle_0_vol = int(candle_0.volume)
        candle_1_vol = int(candle_1.volume)
        candle_2_vol = int(candle_2.volume)
        candle_3_vol = int(candle_3.volume)
        candle_4_vol = int(candle_4.volume)
        candle_5_vol = int(candle_5.volume)
        candle_6_vol = int(candle_6.volume)
        
        candle_0_close = float(candle_0.close)
        candle_1_close = float(candle_1.close)
        candle_2_close = float(candle_2.close)
        candle_3_close = float(candle_3.close)
        candle_4_close = float(candle_4.close)
        candle_5_close = float(candle_5.close)
        candle_6_close = float(candle_6.close)
        
        candle_0_open = float(candle_0.open)
        candle_1_open = float(candle_1.open)
        candle_2_open = float(candle_2.open)
        candle_3_open = float(candle_3.open)
        candle_4_open = float(candle_4.open)
        candle_5_open = float(candle_5.open)
        candle_6_open = float(candle_6.open)
        
        candle_1_high = float(candle_1.high)
        candle_2_high = float(candle_2.high)
        candle_3_high = float(candle_3.high)
        candle_4_high = float(candle_4.high)
        candle_5_high = float(candle_5.high)
        candle_6_high = float(candle_6.high)
        
        candle_0_low = float(candle_0.low)
        candle_1_low = float(candle_1.low)
        candle_2_low = float(candle_2.low)
        candle_3_low = float(candle_3.low)
        candle_4_low = float(candle_4.low)
        candle_5_low = float(candle_5.low)
        candle_6_low = float(candle_6.low)

        def _ret_engulf_true(right_side, strength_key, pattern_id):
            audit = _signal_path_audit_bundle(
                stock, indicator, limit, getCandlesData,
                extra={
                    "mode": "engulf_only_multibar",
                    "engulfing_pattern_id": pattern_id,
                    "engulfing_right": right_side,
                    "returned_strength": strength_key,
                },
            )
            return True, right_side, stock, strength_key, audit

        #AI_function() # match the pattern
        if candle_6_close >= candle_5_close and (candle_5_close >= candle_4_open or candle_5_close >= candle_4_high or candle_5_close >= candle_4_close) and candle_4_close <= candle_3_close and \
            candle_6_vol>= candle_5_vol*0.65 and candle_5_vol >=candle_4_vol*0.65:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 3 candles Pure Bullish Engulf Condition <<<CALL-AAAAA-StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "strongBuy", "engulf_only_CALL_AAAA_strongBuy")
        elif candle_6_close >= candle_5_close and (candle_5_close >= candle_4_open or candle_5_close >= candle_4_high or candle_5_close >= candle_4_close) and candle_4_close <= candle_3_close and \
            candle_5_vol >=candle_4_vol*0.65 and (candle_6_vol >=candle_5_vol*1.2 or candle_6_vol >=candle_4_vol*1.2):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 3 candles Pure Bullish Engulf Condition <<<CALL-AAAAA_HVY_VOL-StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "heavyBuy", "engulf_only_CALL_AAAA_hvy_vol_strongBuy")
        elif (candle_6_close >= candle_5_open or candle_6_close >= candle_5_high) and (candle_5_close <= candle_4_close or (candle_5_high+candle_5_low)/2<= candle_4_close) and (candle_4_close <= candle_3_close or (candle_4_high+candle_4_low)/2<= candle_3_close) and \
            candle_6_vol >=candle_5_vol*0.65:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 4 candles Pure Bullish Engulf Condition <<<CALL-BBBBB-StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "strongBuy", "engulf_only_CALL_BBBB_strongBuy")
        elif (candle_6_close >= candle_5_open or candle_6_close >= candle_5_high) and (candle_5_close <= candle_4_close or (candle_5_high+candle_5_low)/2<= candle_4_close) and (candle_4_close <= candle_3_close or (candle_4_high+candle_4_low)/2<= candle_3_close) and \
            candle_6_vol >=candle_5_vol*1.25:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 4 candles Pure Bullish Engulf Condition <<<CALL-BBBBB_HVY_VOL_StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "heavyBuy", "engulf_only_CALL_BBBB_hvy_vol_strongBuy")
        elif candle_6_close >= candle_5_close and candle_5_close>=candle_5_open and (candle_5_open-candle_5_low>=candle_5_close-candle_5_open*2) and \
            (candle_5_high-candle_5_open<=candle_5_close-candle_5_open) and \
            (candle_6_vol >=candle_5_vol*0.65 and candle_5_vol >=candle_4_vol*0.85):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 3 candles Pure Bullish Engulf Condition <<<CALL-CCCCC-StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "strongBuy", "engulf_only_CALL_CCCC_strongBuy")
        elif candle_6_close >= candle_5_close and candle_5_close>=candle_5_open and (candle_5_open-candle_5_low>=candle_5_close-candle_5_open*2) and \
            (candle_5_high-candle_5_open<=candle_5_close-candle_5_open) and \
            candle_5_vol >=candle_4_vol*1.05 and candle_6_vol >=candle_5_vol*0.55:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 3 candles Pure Bullish Engulf Condition <<<CALL-CCCCC_HVY_VOL_StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "heavyBuy", "engulf_only_CALL_CCCC_hvy_vol_strongBuy")
        elif (candle_6_close >= candle_4_open or candle_6_close >= candle_4_high) and \
            candle_4_open >= candle_4_close and \
            (candle_5_vol >= candle_4_vol*0.65 and candle_6_vol >= candle_5_vol*0.55 and candle_6_vol >=candle_4_vol*0.5):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bullish Engulf Condition <<<CALL-DDDDD-MediumBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "normalBuy", "engulf_only_CALL_DDDD_normalBuy")
        elif (candle_6_close >= candle_4_open or candle_6_close >= candle_4_high) and \
            candle_4_open >= candle_4_close and \
            (candle_5_vol > candle_4_vol*0.55 and candle_6_vol >=candle_4_vol*0.52 and candle_6_vol >=candle_5_vol*0.55):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bullish Engulf Condition <<<CALL-DDDDD_HVY_VOL_MediumBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "mediumBuy", "engulf_only_CALL_DDDD_hvy_vol_mediumBuy")
        elif (candle_6_close >= candle_3_open or candle_6_close >= candle_3_high) and \
            candle_3_open >= candle_3_close and \
            (candle_4_open <= candle_3_open or candle_4_open <= candle_3_high) and (candle_5_open <= candle_3_open or candle_5_open <= candle_3_high) and \
            (candle_6_vol >= candle_3_vol*0.6 and candle_4_vol >= candle_3_vol*0.55 and candle_5_vol <= candle_3_vol*0.6):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bullish Engulf Condition <<<CALL-EEEEE-MediumBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return _ret_engulf_true("CALL", "mediumBuy", "engulf_only_CALL_EEEE_mediumBuy")
        elif candle_6_close <= candle_4_open and candle_6_close <= candle_5_open and candle_5_high >= candle_4_high and candle_6_close <= candle_4_open and \
            candle_6_close <= candle_5_low and candle_6_vol >= candle_5_vol * 0.85 and candle_6_vol >= candle_4_vol * 0.8:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bearish Engulf Condition <<<PUT-AAAAA_MediumSELL>> meet. Return TRUE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return _ret_engulf_true("PUT", "mediumSell", "engulf_only_PUT_AAAA_mediumSell")
        elif candle_6_close <= candle_5_open and candle_6_open >= candle_5_close and candle_6_open >= candle_5_high and candle_6_close <= candle_5_low and \
            candle_6_vol >= candle_5_vol * 0.85 and candle_6_vol <= candle_5_vol * 1.25:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bearish Engulf Condition <<<PUT-BBBBB_StrongSELL>> meet. Return TRUE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return _ret_engulf_true("PUT", "strongSell", "engulf_only_PUT_BBBB_strongSell")
        elif candle_6_close <= candle_5_open and candle_6_close <= candle_4_open and candle_6_close <= candle_3_open and \
            candle_6_vol >= candle_5_vol * 0.8:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bearish Engulf Condition <<<PUT-BBBBB_HVY_VOL_StrongSELL>> meet. Return TRUE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return _ret_engulf_true("PUT", "mediumSell", "engulf_only_PUT_BBBB_hvy_vol_mediumSell")
        elif (candle_2_close <= candle_3_close or candle_2_close > candle_3_close) and \
                (candle_1_close >= candle_2_close or candle_1_close < candle_2_close) and \
                (candle_0_open >= candle_1_close or candle_0_open < candle_1_close) and \
                (candle_0_close < candle_1_low) and \
                candle_1_vol >= candle_0_vol * 0.8:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bearish Engulf Condition <<<PUT-AAAAA>> meet. Return TRUE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return _ret_engulf_true("PUT", "normalSell", "engulf_only_PUT_chain_normalSell")
        else:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> NO CONDITION MEET. Return FALSE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}. \
                        ********************************** STOCK CHECK END ********************************************\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return False, "None", stock, "notrade", None

def checkVWAPValue(stock, Right, candlesData):
    # from datetime import datetime
    toVWAP = False
    logger.info(f"getting VWAP Value for stock = {stock}")
    getCandlesData = candlesData
    getCandleLenghtRange = len(getCandlesData)
    totalVWAP = 0
    curtVWAPList = []
    curtVWAPCum = []
    curtVWAPVol = []

    runningCandle = getCandlesData[0]
    logger.info(f"###Running Candle Value is = {runningCandle}")
    runningLast = float(runningCandle.close)
    runningOpen = float(runningCandle.open)

    for candle in getCandlesData:
        candle_0_vol = int(candle.volume) * 100
        curtCumTotal = ((candle.high + candle.low + candle.close) / 3) * candle_0_vol
        curtVWAPCum.append(curtCumTotal)
        curtVWAPVol.append(candle_0_vol)

    sumCummlative = sum(curtVWAPCum)
    sumVolume = sum(curtVWAPVol)
    if sumVolume == 0:
        logger.warning(f"VWAP: total volume is 0 for {stock}, returning False")
        return False
    intradayVWAP = sumCummlative / sumVolume

    logger.info(
        (
            "Current Time is = {} \
                Current NewYork Trade TIme is = {} \
                Current MID VWAP Value is = {} for Stock = {}".format(
                datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                datetime.now().astimezone(NY_TZ).strftime("%Y-%m-%d-%H-%M-%S"),
                intradayVWAP,
                stock,
            )
        )
    )

    if Right == "CALL":
        if runningLast >= intradayVWAP and runningOpen >= intradayVWAP:
            logger.info(f"VWAP Condition matched For CALL for stock = {stock}")
            toVWAP = True
    elif Right == "PUT":
        if runningLast < intradayVWAP:
            logger.info(f"VWAP Condition matched For PUT for stock = {stock}")
            toVWAP = True
    else:
        logger.info(f"VWAP Condition not matched for stock = {stock}")

    return toVWAP

def checkVWAPValue_OLD(stock, Right, candlesData):
    from datetime import datetime
    toVWAP = False
    logger.info(f"getting VWAP Value for stock = {stock}")
    getCandlesData = candlesData
    getCandleLenghtRange = len(getCandlesData)
    # logger.info("Candle data is = {}".format(getCandlesData))
    # exit()
    totalVWAP = 0
    curtVWAPList = []
    curtVWAPCum = []
    curtVWAPVol = []

    # logger.info("\n\n Full Candle list is = {}\n\n".format(getCandlesData))

    runningCandle = getCandlesData[0]
    logger.info(f"Running Candle Value is = {runningCandle}")
    runningHigh = float(runningCandle[2])
    # logger.info("Running Candle High is = {}".format(runningHigh))

    for eachCount in range(getCandleLenghtRange):
        candle_0 = [float(eachCount) for eachCount in getCandlesData[eachCount][1:]]

        candle_0_open = candle_0[0]
        curtHigh = candle_0[1]
        candle_0_low = candle_0[2]
        candle_0_close = candle_0[3]
        candle_0_vol = int(candle_0[4]) * 100

        curtCumTotal = ((curtHigh + candle_0_low + candle_0_close) / 3) * candle_0_vol
        curtVWAPCum.append(curtCumTotal)
        curtVWAPVol.append(candle_0_vol)

    sumCummlative = sum(curtVWAPCum)
    sumVolume = sum(curtVWAPVol)
    if sumVolume == 0:
        logger.warning(f"VWAP_OLD: total volume is 0 for {stock}, returning False")
        return False
    intradayVWAP = sumCummlative / sumVolume

    logger.info(("Current Time is = {} \
                Current NewYork Trade Time is = {} \
                Current MID VWAP Value is = {} for Stock = {}".format(
                datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                datetime.now().astimezone(NY_TZ).strftime("%Y-%m-%d-%H-%M-%S"),
                intradayVWAP,
                stock)))

    if Right == "CALL":
        if runningHigh <= intradayVWAP:
            logger.info(f"VWAP Condition matched For CALL for stock = {stock}")
            toVWAP = True
    elif Right == "PUT":
        if runningHigh > intradayVWAP:
            logger.info(f"VWAP Condition matched For PUT for stock = {stock}")
            toVWAP = True
    else:
        logger.info(f"VWAP Condition not matched for stock = {stock}")

    return toVWAP

def getATRValue(stock, candlesData, days=21):
    formatList = []
    from datetime import datetime
    logger.info(f"getting ATR Value for stock = {stock} for Time Range = {days}")
    df = client.to_df(candlesData)

    # for each in candlesData[::-1]:
    #     new = ""
    #     for eve in each:
    #         if each.index(eve) == 0:
    #             new = new + str(eve)
    #         else:
    #             new = new + "," + str(eve)
    #     formatList.append(new)
    # getCandlesData = formatList
    # getCandleLenghtRange = len(getCandlesData)

    # totalCandleString = "Date,Open,High,Low,Close,Volume\n" + '\n'.join(
    #     each for each in getCandlesData[len(getCandlesData) - 11:])
    # logger.info("Stock = {} \n data for Frame is = \n{}".format(stock, totalCandleString))

    # data = io.StringIO(totalCandleString)
    # df = pd.read_csv(data, sep=",")
    try:
        atrValue = getATR(df)
    except Exception as atr_ex:
        logger.warning(f"ATR exception: {atr_ex}; retrying up to 5 times")
        atrValue = pd.Series(dtype=float)
        for _atr_retry in range(5):
            try:
                atrValue = getATR(df)
                if len(atrValue) > 0:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if len(atrValue) == 0:
            logger.error("ATR retry exhausted — returning empty ATR")
            return (0, 0)

    logger.info(
        f"ATR value is = {atrValue} and len of list is = {len(atrValue)}\n\n"
    )
    currentAtrValue = atrValue[len(atrValue) - 1]

    logger.info(
        f'Current NewYork Trade TIme is = {datetime.now().astimezone(NY_TZ).strftime("%Y-%m-%d-%H-%M-%S")}'
    )
    logger.info(f"Current ATR value is = {currentAtrValue}")
    return currentAtrValue

def get10StrikesNearUnderlying(strikeList, undPrc, range_limit=3):
    strikes_10_low = []
    strikes_10_high = []
    for _ in range(range_limit):
        low, high = returnLowHigh(strikeList, undPrc)
        strikes_10_low.append(low)
        strikes_10_high.append(high)

    return strikes_10_low, strikes_10_high

def getStockNearStrikes(stock: str, strikesListDict: dict,tick: Tick):
    stock10Strikesmapper = {}
    strikesList = []

    dataDict = copy.deepcopy(strikesListDict) if strikesListDict else []
    #logger.info("\n\nStrikes list for stock  {} is = \n{}\n".format(stock, dataDict))

    for eachStockStrike in dataDict:
        for key, value in eachStockStrike.items():
            if key.upper() == stock.upper():
                strikesList = eachStockStrike.get(stock, {}).get("Strike", [])
                break

    if not strikesList:
        logger.info(f"No strikes found for {stock}; expiryStrike.json may be empty or not yet populated.")
        stock10Strikesmapper.update({"lowList": [], "highList": []})
        return stock10Strikesmapper

    strikesListNew = [float(each) for each in strikesList if float(each) > 0]
    
    underlying_price = tick.last
    logger.info("UNDERLYING PRICE IS = {}".format(underlying_price))
    if underlying_price is None or underlying_price <= 0:
        logger.warning(f"Invalid underlying price ({underlying_price}) for {stock} — cannot compute strikes")
        _emit_log(f"{stock}: No valid underlying price yet (last={underlying_price}) — waiting for TWS data", "WARN", "signal")
        stock10Strikesmapper.update({"lowList": [], "highList": []})
        return stock10Strikesmapper

    pct_range = 0.25
    lower_bound = underlying_price * (1 - pct_range)
    upper_bound = underlying_price * (1 + pct_range)
    strikesListNew = [s for s in strikesListNew if lower_bound <= s <= upper_bound]
    if not strikesListNew:
        logger.warning(f"No strikes within ±{int(pct_range*100)}% of {stock} underlying ${underlying_price:.2f}")
        stock10Strikesmapper.update({"lowList": [], "highList": []})
        return stock10Strikesmapper

    lowList, highList = get10StrikesNearUnderlying(strikesListNew, underlying_price)
    lowList = [s for s in lowList if s > 0]
    highList = [s for s in highList if s > 0]

    # stock10Strikesmapper.update({"lowList": highList, "highList": lowList})
    stock10Strikesmapper.update({"lowList": lowList, "highList": highList})
    logger.info("Returning Nearst Strikes Data for Stock = {}".format(stock))
    return stock10Strikesmapper

def get_delta_volume(stock, strike, right, expiry):
    """
    This function retrieves options market data for a given stock, strike, right, and expiry.
    
    Args:
    - stock (str): The symbol of the stock for which options data is needed
    - strike (float): The strike price of the options
    - right (str): The type of options, either "CALL" or "PUT"
    - expiry (str): The expiry date of the options, in the format of 'YYYY-MM-DD'
    
    Returns:
    - deltaVolData (list): A list of tuples, where each tuple contains the delta and volume of the options.
    """

    deltaVolData = []
    market_data = client.get_options_data(symbol=stock, expiry=expiry, right=right, strike=strike)

    # Check if the market data is not None, then add delta and volume of the options to deltaVolData
    # Treat delta=-1 or volume=-1 as missing/invalid options data (P3 from log analysis)
    if market_data:
        delta_val = getattr(market_data, "delta", None)
        vol_val = getattr(market_data, "volume", None)
        bid_val = getattr(market_data, "bid", None)
        ask_val = getattr(market_data, "ask", None)
        last_val = getattr(market_data, "last", None)
        # Liquidity check: skip illiquid options (wide spread, low volume) — effectively "liquidity swap" to try next strike
        liq_on = str(globals().get("LIQUIDITY_CHECK_ON_OFF", "OFF")).lower() == "on"
        if liq_on and hasattr(indi, "checkLiquidity"):
            min_vol = int(globals().get("LIQUIDITY_MIN_VOLUME", 20))
            max_spread = float(globals().get("LIQUIDITY_MAX_SPREAD_PCT", 15))
            if not indi.checkLiquidity(bid_val, ask_val, last_val, vol_val, min_volume=min_vol, max_spread_pct=max_spread):
                logger.info(f"Liquidity check failed for {stock} {right} {strike} — skipping (try next strike)")
                _emit_log(f"Liquidity: {stock} {right} {strike} illiquid — skip", "INFO", "signal")
                deltaVolData.append("NoDataPresent")
                deltaVolData.append(market_data)
                return deltaVolData
        if delta_val is not None and delta_val != -1 and vol_val is not None and vol_val != -1:
            deltaVolData = [(delta_val, vol_val)]

    # If deltaVolData is empty, then add the string "NoDataPresent" to deltaVolData
    if not deltaVolData:
        deltaVolData.append("NoDataPresent")

    # Add the market data to deltaVolData
    deltaVolData.append(market_data)
    return deltaVolData


def _bars_ohlcv_for_audit(getCandlesData):
    """OHLCV rows for the same bar list used by checkAlgoAndTrade (IBKR history order: index 0 = oldest in window)."""
    rows = []
    if not getCandlesData:
        return rows
    for o in getCandlesData:
        try:
            rows.append({
                "date": str(getattr(o, "date", "")),
                "open": float(o.open),
                "high": float(o.high),
                "low": float(o.low),
                "close": float(o.close),
                "volume": float(getattr(o, "volume", 0) or 0),
            })
        except Exception:
            rows.append({"date": str(getattr(o, "date", "")), "parse_error": True, "repr": repr(o)})
    return rows


def _ohlcv_columns_from_bars(getCandlesData):
    """Column-oriented OHLCV (rebuild with pd.DataFrame(bundle)). Same bar order as row list."""
    empty = {"date": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
    if not getCandlesData:
        return empty
    try:
        return {
            "date": [str(getattr(o, "date", "")) for o in getCandlesData],
            "open": [float(o.open) for o in getCandlesData],
            "high": [float(o.high) for o in getCandlesData],
            "low": [float(o.low) for o in getCandlesData],
            "close": [float(o.close) for o in getCandlesData],
            "volume": [float(getattr(o, "volume", 0) or 0) for o in getCandlesData],
        }
    except Exception:
        return empty


def _super_trend_signal_df_to_records(super_trend_signal_df):
    """BOTSingal output columns Date, Close, ST_BUY_SELL → JSON-safe list of rows (full series used for signal)."""
    try:
        df = super_trend_signal_df.copy()
        df["Date"] = df["Date"].astype(str)
        return df.to_dict(orient="records")
    except Exception:
        return []


def _signal_path_audit_bundle(stock, indicator_setting, limit_requested, getCandlesData, *, extra=None):
    """
    Complete bar payload + optional SuperTrend/engulf metadata for trade-open audit.
    """
    bundle = {
        "source_function": "getCallPutEngulfCheck",
        "stock": stock,
        "indicator_setting": indicator_setting,
        "bar_size": candleTime,
        "limit_requested": limit_requested,
        "bar_count_actual": len(getCandlesData) if getCandlesData else 0,
        "full_ohlcv_all_bars": _bars_ohlcv_for_audit(getCandlesData),
        "full_ohlcv_columns_dataframe_shape": _ohlcv_columns_from_bars(getCandlesData),
    }
    if getCandlesData and len(getCandlesData) >= 8:
        win = getCandlesData[1:8]
        bundle["engulfing_multibar_window_slice_1_to_7_ohlcv"] = _bars_ohlcv_for_audit(win)
        bundle["engulfing_window_ohlcv_columns_dataframe_shape"] = _ohlcv_columns_from_bars(win)
        bundle["engulfing_indexing_note"] = (
            "Slice getCandlesData[1:8] = 7 bars; in _check_engulfing_patterns these are candle_0 (oldest) … candle_6 (newest in window)."
        )
    if extra:
        bundle.update(extra)
    return bundle


def _vwap_snapshot_for_audit(getCandlesData):
    """Same VWAP level as checkVWAPValue (volume-weighted HLC/3); index-0 open/close = running candle there."""
    if not getCandlesData:
        return None
    try:
        curt_cum = []
        curt_vol = []
        for candle in getCandlesData:
            v = int(candle.volume) * 100
            typ = (float(candle.high) + float(candle.low) + float(candle.close)) / 3.0
            curt_cum.append(typ * v)
            curt_vol.append(v)
        sv = sum(curt_vol)
        if sv == 0:
            return None
        intraday = sum(curt_cum) / sv
        running = getCandlesData[0]
        return {
            "intraday_vwap": round(float(intraday), 6),
            "running_bar_index0_open": float(running.open),
            "running_bar_index0_close": float(running.close),
        }
    except Exception:
        return None


def checkAlgoAndTrade(Stock, Right, onlyAtrCheck="no"):
    """Returns (toTrade, atrVal, ema_S, algo_audit_dict). algo_audit_dict includes OHLCV bars and gate outcomes."""
    _z = ([0], [0], [0])

    if DAY_LOCKED and CLOSE_ALL_ORDERS:
        logger.warning("Trading blocked: DAY LOCK active (PnL limit hit)")
        return (False, 0.0, _z, {"failure_reason": "day_locked"})
    if globals().get("CLOSE_ALL_IN_PROGRESS", False):
        logger.warning("Trading blocked: Close All in progress")
        return (False, 0.0, _z, {"failure_reason": "close_all_in_progress"})

    # Use globals so sidecar (trading_engine) can set these; fallback if run as library without main_call
    _profit = globals().get("profit_amount_day", 200.0)
    _loss = globals().get("loss_amount_day", 200.0)
    timeCheck = timeCheckAndCloseProgram(SUB_ACCOUNT_ID, _profit, _loss)
    # When running as sidecar (Tauri app), do not exit process; just skip trading
    if timeCheck:
        logger.warning("Time/PnL check: skipping trade (day end or PnL limit); not exiting process")
        return (False, 0.0, _z, {"failure_reason": "time_or_pnl_halt"})

    from datetime import datetime
    toTrade = False
    logger.info("Current NewYork Trade Time is = {}".format(
        datetime.today().astimezone(NY_TZ).strftime("%Y-%m-%d-%H-%M-%S")))

    getCandlesData = client.get_bars(stock=Stock, barSize=candleTime, limit=21)
    logger.info("candle Data is = {}".format(getCandlesData))
    n_candles = len(getCandlesData) if getCandlesData else 0
    _emit_log(f"Algo: {Stock} IBKR bars={n_candles} (need 21 for ATR/VWAP/EMA)", "DEBUG", "signal")
    if not getCandlesData or len(getCandlesData) < 2:
        logger.warning(f"No/insufficient candle data for {Stock}; skipping algo check (historical data may not be ready)")
        _emit_log(f"Algo: {Stock} insufficient bars ({n_candles}) — skipping trade check", "INFO", "signal")
        return (False, 0.0, _z, {
            "failure_reason": "insufficient_bars",
            "stock": Stock,
            "right_requested": Right,
            "bar_size": candleTime,
            "bar_count": n_candles,
            "ohlcv_bars_used": _bars_ohlcv_for_audit(getCandlesData or []),
        })

    ohlcv_rows = _bars_ohlcv_for_audit(getCandlesData)
    algo_audit = {
        "failure_reason": None,
        "stock": Stock,
        "right_requested": Right,
        "bar_size": candleTime,
        "bar_count": len(getCandlesData),
        "bar_limit_requested": 21,
        "ny_time_at_algo": datetime.today().astimezone(NY_TZ).isoformat(),
        "ohlcv_bars_used": ohlcv_rows,
        "ohlcv_columns_dataframe_shape": _ohlcv_columns_from_bars(getCandlesData),
        "bar_order_note": "Index 0 = oldest bar in window; same ordering as get_bars(..., limit=21) and checkVWAPValue running candle.",
    }

    df_candles = client.to_df(getCandlesData)

    # ADX filter: skip sideways market (ADX < threshold)
    adx_on = str(globals().get("ADX_ON_OFF", "OFF")).lower() == "on"
    if adx_on:
        adx_threshold = float(globals().get("ADX_THRESHOLD", 25))
        adx_val = indi.getADX(df_candles, period=14) if hasattr(indi, "getADX") else None
        passed = adx_val is None or adx_val >= adx_threshold
        algo_audit["adx_filter"] = {
            "enabled": True,
            "value": float(adx_val) if adx_val is not None else None,
            "threshold": adx_threshold,
            "passed": passed,
            "condition": "trade_only_if_ADX>=threshold (skip sideways)",
        }
        if adx_val is not None and adx_val < adx_threshold:
            logger.info(f"ADX={adx_val:.1f} < {adx_threshold} (sideways market) — skipping {Stock}")
            _emit_log(f"ADX: {Stock} sideway market (ADX={adx_val:.1f}) — no trade", "INFO", "signal")
            algo_audit["failure_reason"] = "adx_too_low"
            return (False, 0.0, _z, algo_audit) if onlyAtrCheck == "no" else (False, 0.0, _z, algo_audit)  # noqa: E501
        if adx_val is not None:
            _emit_log(f"ADX: {Stock} ADX={adx_val:.1f} ≥ {adx_threshold} ✓", "DEBUG", "signal")
    else:
        algo_audit["adx_filter"] = {"enabled": False, "condition": "OFF — not applied"}

    # RSI divergence: must align with signal (CALL needs bullish or none, PUT needs bearish or none)
    rsi_div_on = str(globals().get("RSI_DIVERGENCE_ON_OFF", "OFF")).lower() == "on"
    if rsi_div_on == "on" and onlyAtrCheck == "no":
        rsi_div = indi.checkRSIDivergence(df_candles, rsi_period=14, lookback=5) if hasattr(indi, "checkRSIDivergence") else None
        algo_audit["rsi_divergence"] = {
            "enabled": True,
            "signal": rsi_div,
            "condition": "block CALL if bearish div; block PUT if bullish div",
        }
        if rsi_div == "bearish" and Right.upper() in ("CALL", "C"):
            logger.info(f"RSI bearish divergence — skip CALL for {Stock}")
            _emit_log(f"RSI divergence: {Stock} bearish — skip CALL", "INFO", "signal")
            algo_audit["failure_reason"] = "rsi_divergence_blocks_call"
            return (False, 0.0, _z, algo_audit)
        if rsi_div == "bullish" and Right.upper() in ("PUT", "P"):
            logger.info(f"RSI bullish divergence — skip PUT for {Stock}")
            _emit_log(f"RSI divergence: {Stock} bullish — skip PUT", "INFO", "signal")
            algo_audit["failure_reason"] = "rsi_divergence_blocks_put"
            return (False, 0.0, _z, algo_audit)
    else:
        algo_audit["rsi_divergence"] = {"enabled": False, "condition": "OFF — not applied"}

    # Volume divergence: must align with signal
    vol_div_on = str(globals().get("VOLUME_DIVERGENCE_ON_OFF", "OFF")).lower() == "on"
    if vol_div_on == "on" and onlyAtrCheck == "no":
        vol_div = indi.checkVolumeDivergence(df_candles, lookback=5) if hasattr(indi, "checkVolumeDivergence") else None
        algo_audit["volume_divergence"] = {
            "enabled": True,
            "signal": vol_div,
            "condition": "block CALL if bearish vol div; block PUT if bullish vol div",
        }
        if vol_div == "bearish" and Right.upper() in ("CALL", "C"):
            logger.info(f"Volume bearish divergence — skip CALL for {Stock}")
            _emit_log(f"Volume divergence: {Stock} bearish — skip CALL", "INFO", "signal")
            algo_audit["failure_reason"] = "volume_divergence_blocks_call"
            return (False, 0.0, _z, algo_audit)
        if vol_div == "bullish" and Right.upper() in ("PUT", "P"):
            logger.info(f"Volume bullish divergence — skip PUT for {Stock}")
            _emit_log(f"Volume divergence: {Stock} bullish — skip PUT", "INFO", "signal")
            algo_audit["failure_reason"] = "volume_divergence_blocks_put"
            return (False, 0.0, _z, algo_audit)
    else:
        algo_audit["volume_divergence"] = {"enabled": False, "condition": "OFF — not applied"}

    # Liquidity swap pattern: sweep and reversal — must align with signal (CALL needs bullish, PUT needs bearish)
    liq_swap_on = str(globals().get("LIQUIDITY_SWAP_ON_OFF", "OFF")).lower() == "on"
    if liq_swap_on == "on" and onlyAtrCheck == "no":
        liq_swap = indi.checkLiquiditySwapPattern(df_candles, lookback=5) if hasattr(indi, "checkLiquiditySwapPattern") else None
        algo_audit["liquidity_swap"] = {
            "enabled": True,
            "signal": liq_swap,
            "condition": "block CALL if bearish swap; block PUT if bullish swap",
        }
        if liq_swap == "bearish" and Right.upper() in ("CALL", "C"):
            logger.info(f"Liquidity swap bearish — skip CALL for {Stock}")
            _emit_log(f"Liquidity swap: {Stock} bearish sweep — skip CALL", "INFO", "signal")
            algo_audit["failure_reason"] = "liquidity_swap_blocks_call"
            return (False, 0.0, _z, algo_audit)
        if liq_swap == "bullish" and Right.upper() in ("PUT", "P"):
            logger.info(f"Liquidity swap bullish — skip PUT for {Stock}")
            _emit_log(f"Liquidity swap: {Stock} bullish sweep — skip PUT", "INFO", "signal")
            algo_audit["failure_reason"] = "liquidity_swap_blocks_put"
            return (False, 0.0, _z, algo_audit)
    else:
        algo_audit["liquidity_swap"] = {"enabled": False, "condition": "OFF — not applied"}

    logger.info("\nVWAP_ON_OFF => {}\n".format(VWAP_ON_OFF))
    if onlyAtrCheck == "no":
        atrVal = float(getATRValue(Stock, getCandlesData))
        vwap_snap = _vwap_snapshot_for_audit(getCandlesData)
        if VWAP_ON_OFF.lower() == "on":
            vwapVal = checkVWAPValue(Stock, Right, getCandlesData)
            logger.info("vwapVal Data Return for stock = {} is = {}".format(Stock, vwapVal))
            toTrade = vwapVal
            ru = Right.upper()
            algo_audit["vwap_filter"] = {
                "enabled": True,
                "gate_passed": bool(vwapVal),
                "condition_call": "last>=vwap and open>=vwap on running bar (index 0)",
                "condition_put": "last<vwap on running bar (index 0)",
                **(vwap_snap or {}),
            }
        else:
            toTrade = True
            algo_audit["vwap_filter"] = {
                "enabled": False,
                "gate_passed": None,
                "skipped": True,
                "intraday_vwap_reference": (vwap_snap or {}).get("intraday_vwap"),
                "condition": "VWAP filter OFF — not gating trade",
            }

        atr_passed = atrVal >= ATR_CHECKS
        if atr_passed:
            logger.info("ATR_CHECKS Meet the ATR value")
            _emit_log(f"{Stock}: ATR={atrVal:.4f} ≥ {ATR_CHECKS} ✓ (passed)", "DEBUG", "signal")
            toTrade = toTrade and True
        else:
            logger.info("ATR_CHECKS Not Meet the ATR value")
            _emit_log(f"{Stock}: ATR={atrVal:.4f} < {ATR_CHECKS} ✗ (failed — too low volatility)", "INFO", "signal")
            toTrade = toTrade and False

        algo_audit["atr_gate"] = {
            "atr": float(atrVal),
            "threshold": float(ATR_CHECKS) if ATR_CHECKS is not None else None,
            "passed": bool(atr_passed),
            "condition": "toTrade requires ATR >= ATR_CHECKS (combined with VWAP when ON)",
        }
        algo_audit["composite_algo_to_trade"] = bool(toTrade)

        ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        algo_audit["ema_series_note"] = "Final EMA8/13/21 values appear in placement_context (ema_8, ema_13, ema_21) from same bars."

        return toTrade, atrVal, ema_S, algo_audit
    if onlyAtrCheck == "yes":
        atrVal = getATRValue(Stock, getCandlesData)
        ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        algo_audit["only_atr_check"] = True
        algo_audit["atr_gate"] = {
            "atr": float(atrVal) if atrVal is not None else None,
            "note": "onlyAtrCheck=yes — VWAP/ATR gate branch skipped",
        }
        return toTrade, atrVal, ema_S, algo_audit

    logger.error("checkAlgoAndTrade: invalid onlyAtrCheck value — returning no-trade")
    return (False, 0.0, _z, {"failure_reason": "invalid_onlyAtrCheck", **{k: v for k, v in algo_audit.items() if k in ("ohlcv_bars_used", "stock", "right_requested", "bar_size")}})

def updateStockMapper(stockName, value):
    logger.info(f"\n updateStockMapper for stock = {stockName}\n")
    with open(f"{stockName}.txt", "r",  encoding="utf-8") as f1_2:
        f1_2_data = f1_2.read()
    valuePresent = f1_2_data.split(",")
    valuePresent[0] = str(value)
    valuePresent[1] = valuePresent[1]

    updateVal = ",".join(valuePresent)
    logger.info(
        f"\n STOCK = {stockName} updateStockMapper UPDATE VALUES ARE  AFTER JOIN= {updateVal}\n"
    )

    with open(f"{stockName}.txt", "w",  encoding="utf-8") as f2:
        f2.write(f"{updateVal}")


def _signal_entry_context(
    *,
    decision_path: str,
    stock_name: str,
    right_match: str,
    strike: float,
    trade_expiry: str,
    signal_strength: str,
    delta_value: float,
    volume: float,
    delta_threshold: float,
    volume_threshold: float,
    to_trade: bool,
    atr_value: float,
    ema_8: float,
    ema_13: float,
    ema_21: float,
    algo_audit: Optional[dict] = None,
    supertrend_engulf_gate_passed: Optional[bool] = None,
    signal_path_audit: Optional[dict] = None,
) -> dict:
    """Serializable dict: why the bot allowed an entry (pre–option-tick execution details)."""
    out = {
        "decision_path": decision_path,
        "decision_path_human": {
            "CALL_heavy_or_strong_signal": "CALL + delta/vol OK + checkAlgo passed + signal heavy/strong",
            "CALL_scalp_ema_conditions": "CALL + delta/vol OK + checkAlgo passed + scalp EMA band / EMA8>13 rules",
            "CALL_intraday_ema_conditions": "CALL + delta/vol OK + checkAlgo passed + intraday EMA alignment",
            "PUT_heavy_or_strong_signal": "PUT + delta/vol OK + checkAlgo passed + signal heavy/strong",
            "PUT_scalp_ema_conditions": "PUT + delta/vol OK + checkAlgo passed + scalp EMA rules",
            "PUT_intraday_ema_conditions": "PUT + delta/vol OK + checkAlgo passed + intraday EMA rules",
        }.get(decision_path, decision_path),
        "signal_strength": signal_strength,
        "stock": stock_name,
        "option_right": right_match,
        "strike": float(strike),
        "expiry": str(trade_expiry),
        "delta": float(delta_value),
        "delta_threshold": float(delta_threshold),
        "delta_condition": "CALL: delta >= CALL_DELTA_CHECK; PUT: delta <= PUT_DELTA_CHECK",
        "option_volume_db": float(volume),
        "volume_threshold": float(volume_threshold),
        "volume_condition": "volume >= VOLUME_CHECK",
        "to_trade_algo": bool(to_trade),
        "atr": float(atr_value),
        "ema_8": float(ema_8),
        "ema_13": float(ema_13),
        "ema_21": float(ema_21),
        "config_snapshot": {
            "candleTime": candleTime,
            "ATR_CHECKS": float(ATR_CHECKS) if ATR_CHECKS is not None else None,
            "ATR_VALUE": float(ATR_VALUE) if ATR_VALUE is not None else None,
            "VWAP_ON_OFF": str(VWAP_ON_OFF),
            "MAX_CONTRACT_AMOUNT": float(MAX_CONTRACT_AMOUNT) if MAX_CONTRACT_AMOUNT is not None else None,
            "PROFIT_INCREMENT": float(PROFIT_INCREMENT) if PROFIT_INCREMENT is not None else None,
            "TRADE_COOLDOWN_SECONDS": float(TRADE_COOLDOWN_SECONDS) if TRADE_COOLDOWN_SECONDS is not None else None,
            "CALL_DELTA_CHECK": float(CALL_DELTA_CHECK) if CALL_DELTA_CHECK is not None else None,
            "PUT_DELTA_CHECK": float(PUT_DELTA_CHECK) if PUT_DELTA_CHECK is not None else None,
            "VOLUME_CHECK": float(VOLUME_CHECK) if VOLUME_CHECK is not None else None,
            "option_tp_sl_max_pct": float(
                (globals().get("fileData") or {}).get("option_tp_sl_max_pct", 0.15)
            ),
            "option_tp_sl_min_dist": float(
                (globals().get("fileData") or {}).get("option_tp_sl_min_dist", 0.02)
            ),
        },
    }
    if supertrend_engulf_gate_passed is not None:
        out["supertrend_engulf_gate_passed"] = bool(supertrend_engulf_gate_passed)
    if algo_audit is not None:
        out["bars_and_algo_conditions"] = algo_audit
    if signal_path_audit is not None:
        out["signal_generation_full"] = signal_path_audit
    return out


def checkConditionsAndTrade(dataValueSet, stock_tick):
    if globals().get("STOP_TRADING", False):
        return "stopped"
    if globals().get("CLOSE_ALL_IN_PROGRESS", False):
        return "closingAll"
    #global tradeExpiry
    logger.info(f"Stock {dataValueSet[0][2].upper()} checkConditionsAndTrade - start")
    
    # from datetime import datetime
    # curMarketTime = datetime.today().astimezone(pytz.timezone("America/New_York")).strftime("%H-%M")
    # marketTime = curMarketTime.replace("-", "")
    # marketTime = int(marketTime)

    stockData = dataValueSet[0]
    allStrieksList = dataValueSet[1] # copy.deepcopy(dataValueSet[1])
    conditionMatch = stockData[0]
    rightMatch = stockData[1].upper()
    stockName = stockData[2].upper()
    signalStrength = stockData[3].lower()
    signal_path_audit = stockData[4] if len(stockData) >= 5 else None
    _emit_log(f"Trade check: {stockName} {rightMatch} (strength={signalStrength})", "INFO", "signal")

    dataReturn = "None"
    tradeExpiry = tradeExpiry_val
    if "spy" in stockName.lower() or "qqq" in stockName.lower():
        tradeExpiry = spy_qqq_tradeExpiry
    
    position = client.get_open_position(symbol=stockName)
    logger.info(f"get_open_position: {stockName}: {position}")
    if position != None:
        pos_right = (position.right or "")[0] if getattr(position, "right", None) else ""
        logger.info("Position = {} and pos_right = {}".format(position.position, pos_right))
        right_char = (rightMatch[0][0] if rightMatch and rightMatch[0] else "").lower()
        if position.position != 0 and pos_right and pos_right.lower() == right_char:
            logger.info(f"Position already Present for Stock = {stockName}")
            _emit_log(f"{stockName} {rightMatch}: Position already open (qty={position.position}) — skipping", "INFO", "signal")
            return "positionAlreadyPresent"
        else:
            logger.info(f"Position is not present with same Right for Stock = {stockName}")

    stockMapperDict = 0
    order = order_mgr.get_entry_order(stockName, right=rightMatch[0] if rightMatch else None)
    if order != None and order.active == True:
        logger.info(f"Order Already Present for Stock = {stockName}, status: {order.order_status}")
        _emit_log(f"{stockName}: Pending {order.order_status} order exists — skipping", "INFO", "signal")
        return "orderAlreadyPresent"
    try:
        if conditionMatch == False:
            dataReturn = "conditionNotMatched"
        else:
            # if stockMapperDict == 1:
            #     logger.info("Order Already Present for Stock = {} and Mapper file value is ={}".format(stockName, stockMapperDict))
            #     dataReturn = "orderAlreadyPresent"
            # else:
            logger.info(f"Order not present for Stock = {stockName} and Mapper file value is ={stockMapperDict}. so going to place order after algo data checks")
            # TODO: commented
            # if marketTime == newJsonTime:
            #     logger.info("Current Candle time is = {} and Last traded Candle time is = {}. BOTH are same candle. so not doing any trades and continue on next".format(marketTime, newJsonTime))
            #     dataReturn = "sameCandleNoTrade"
            # else:
            stockStrikes = getStockNearStrikes(stockName, allStrieksList, stock_tick)
            # logger.info("STRIKES LIST TO TRADE = {}".format(stockStrikes))
            if rightMatch == "CALL":
                logger.info(f"Right is CALL and stock is = {stockName} and Checking for Trade")
                strikesToTrade = stockStrikes["highList"]
                for eachStrike in strikesToTrade:
                    deltaVolDataReturn1 = get_delta_volume(stockName, eachStrike, rightMatch, tradeExpiry)
                    deltaVolDataReturn = deltaVolDataReturn1[0]
                    options_tick = deltaVolDataReturn1[1]
                    # If the distance between trades check fails (symbol+right+expiry specific)
                    if check_TRADE_COOLDOWN_SECONDS(stockName, rightMatch, tradeExpiry):
                        continue
                    else:
                        tradeKey = _side_cooldown_key(stockName, rightMatch)
                        last_trade = trade_time_dict.get(tradeKey)
                        if last_trade is not None:
                            logger.info(f"{stockName} distance between trade check passed for {tradeKey}, last_close_time={last_trade}, TRADE_COOLDOWN_SECONDS={TRADE_COOLDOWN_SECONDS}")

                    logger.info(f"DELTA DATA RETURN For {stockName}{tradeExpiry}{rightMatch}{eachStrike} IS = {deltaVolDataReturn}")
                    if deltaVolDataReturn == "NoDataPresent":
                        logger.info("No Trade Happend For Stocks as Table Data is not present")
                        _emit_log(f"{stockName} {eachStrike}{rightMatch[0]} {tradeExpiry}: No options data available", "DEBUG", "signal")
                        continue
                    elif len(deltaVolDataReturn) == 2:
                        logger.info(f"Checking Delta and Volume Match Condition for stock ={stockName} and strike is ={eachStrike}")
                        deltaValue = deltaVolDataReturn[0]
                        volumes = deltaVolDataReturn[1]
                        logger.info(f"Recevied delta value is = {deltaValue} and Volume is = {volumes} from DB for stock = {stockName}")
                        _emit_log(f"{stockName} {eachStrike}{rightMatch[0]}: delta={deltaValue:.2f} (need≥{CALL_DELTA_CHECK}), vol={volumes} (need≥{VOLUME_CHECK})", "DEBUG", "signal")

                        if deltaValue >= CALL_DELTA_CHECK and volumes >= VOLUME_CHECK:
                            # TODO: MUST REMOVE FOLLOWING CODE
                            # NOTE: TO test order placement temporary code, 
                            # -----------
                            #getCandlesData = client.get_bars(stock=stockName, barSize=candleTime, limit="day")
                            #atrValue = float(getATRValue(stockName, getCandlesData))
                            #toTrade = True
                            # -----------
                            toTrade, atrValue, ema_S, algo_audit = checkAlgoAndTrade(stockName, "CALL")                            
                            logger.info("\n EMA_S Values for 8D, 13D, and 21D are = {}\n".format(ema_S))

                            ema_S_8 = ema_S[0][len(ema_S[0])-1]
                            ema_S_13 = ema_S[1][len(ema_S[1])-1]
                            ema_S_21 = ema_S[2][len(ema_S[2])-1]
                            
                            if toTrade and ("heavy" in signalStrength.lower() or "strong" in signalStrength.lower()):
                                ###### SCLAP HIT
                                _pc = _signal_entry_context(
                                    decision_path="CALL_heavy_or_strong_signal",
                                    stock_name=stockName,
                                    right_match=rightMatch,
                                    strike=eachStrike,
                                    trade_expiry=tradeExpiry,
                                    signal_strength=signalStrength,
                                    delta_value=deltaValue,
                                    volume=volumes,
                                    delta_threshold=CALL_DELTA_CHECK,
                                    volume_threshold=VOLUME_CHECK,
                                    to_trade=toTrade,
                                    atr_value=atrValue,
                                    ema_8=ema_S_8,
                                    ema_13=ema_S_13,
                                    ema_21=ema_S_21,
                                    algo_audit=algo_audit,
                                    supertrend_engulf_gate_passed=conditionMatch,
                                    signal_path_audit=signal_path_audit,
                                )
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="CALL",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick,
                                                        placement_context=_pc)
                                
                                if orderData == "orderPlaced":
                                    # stockMapperDict[stockName].update({"trade":1})
                                    # updateStockMapper(stockName, 1)
                                    dataReturn = "orderPlaced"
                                    break
                                else:
                                    logger.info(f"Order Not Placed for stock={stockName}, Right={rightMatch}, Strike={eachStrike}, Expiry={tradeExpiry}\nBecause ={orderData}")
                                    dataReturn = orderData
                                    continue
                            elif toTrade and ((ema_S_21 - ema_S_8 >= atrValue/2) and (ema_S_21 - ema_S_8 <= atrValue*0.85)) or (ema_S_8 > ema_S_13-(atrValue/1.3) or (ema_S_8 > ema_S_13 and ema_S_13 > ema_S_21)):
                                ###### SCLAP HIT
                                _pc = _signal_entry_context(
                                    decision_path="CALL_scalp_ema_conditions",
                                    stock_name=stockName,
                                    right_match=rightMatch,
                                    strike=eachStrike,
                                    trade_expiry=tradeExpiry,
                                    signal_strength=signalStrength,
                                    delta_value=deltaValue,
                                    volume=volumes,
                                    delta_threshold=CALL_DELTA_CHECK,
                                    volume_threshold=VOLUME_CHECK,
                                    to_trade=toTrade,
                                    atr_value=atrValue,
                                    ema_8=ema_S_8,
                                    ema_13=ema_S_13,
                                    ema_21=ema_S_21,
                                    algo_audit=algo_audit,
                                    supertrend_engulf_gate_passed=conditionMatch,
                                    signal_path_audit=signal_path_audit,
                                )
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="CALL",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick,
                                                        placement_context=_pc)
                                
                                if orderData == "orderPlaced":
                                    # stockMapperDict[stockName].update({"trade":1})
                                    # updateStockMapper(stockName, 1)
                                    dataReturn = "orderPlaced"
                                    break
                                else:
                                    logger.info(f"Order Not Placed for stock={stockName}, Right={rightMatch}, Strike={eachStrike}, Expiry={tradeExpiry}\nBecause ={orderData}")
                                    dataReturn = orderData
                                    continue
                            elif toTrade and (ema_S_21 >= ema_S_13 and ema_S_8 >= ema_S_13) or (ema_S_8 > ema_S_13 and ema_S_13 > ema_S_21 and (ema_S_8-ema_S_13 < atrValue*0.85)):
                                ###### INTRADAY HIT
                                _pc = _signal_entry_context(
                                    decision_path="CALL_intraday_ema_conditions",
                                    stock_name=stockName,
                                    right_match=rightMatch,
                                    strike=eachStrike,
                                    trade_expiry=tradeExpiry,
                                    signal_strength=signalStrength,
                                    delta_value=deltaValue,
                                    volume=volumes,
                                    delta_threshold=CALL_DELTA_CHECK,
                                    volume_threshold=VOLUME_CHECK,
                                    to_trade=toTrade,
                                    atr_value=atrValue,
                                    ema_8=ema_S_8,
                                    ema_13=ema_S_13,
                                    ema_21=ema_S_21,
                                    algo_audit=algo_audit,
                                    supertrend_engulf_gate_passed=conditionMatch,
                                    signal_path_audit=signal_path_audit,
                                )
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="CALL",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick,
                                                        placement_context=_pc)
                                if orderData == "orderPlaced":
                                    dataReturn = "orderPlaced"
                                    break
                                else:
                                    logger.info(f"Order Not Placed for stock={stockName}, Right={rightMatch}, Strike={eachStrike}, Expiry={tradeExpiry}\nBecause ={orderData}")
                                    dataReturn = orderData
                                    continue
                            else:
                                dataReturn = "algoNotMatched"
                                logger.info("CALL -> AlgoNotMatched for stock = {} = Values are => toTrade = {}, atrValue = {} , ema Values = {}".format(stockName, toTrade, atrValue, ema_S))
                        else:
                            dataReturn = "deltaVolumeNotMatched"
                            logger.info("Delta/Volume values not matched. received Delta is = {} and Volume is = {} ** Expected Delta is = {} and Volume is = {} \n".format(deltaValue, volumes, CALL_DELTA_CHECK, VOLUME_CHECK))
            elif rightMatch == "PUT":
                logger.info("RIght is PUT and stock is = {} and Checking for Trade".format(stockName))
                strikesToTrade = stockStrikes["lowList"]
                for eachStrike in strikesToTrade:
                    deltaVolDataReturn1 = get_delta_volume(stockName, eachStrike, rightMatch, tradeExpiry)
                    deltaVolDataReturn = deltaVolDataReturn1[0]
                    options_tick = deltaVolDataReturn1[1]
                    # If the distance between trades check fails (symbol+right+expiry specific)
                    if check_TRADE_COOLDOWN_SECONDS(stockName, rightMatch, tradeExpiry):
                        continue
                    else:
                        tradeKey = _side_cooldown_key(stockName, rightMatch)
                        last_trade = trade_time_dict.get(tradeKey)
                        if last_trade is not None:
                            logger.info(f"{stockName} distance between trade check passed for {tradeKey}, last_close_time={last_trade}, TRADE_COOLDOWN_SECONDS={TRADE_COOLDOWN_SECONDS}")
                    
                    logger.info(f"DELTA DATA RETURN For {stockName}{tradeExpiry}{rightMatch}{eachStrike} IS = {deltaVolDataReturn}")
                    if deltaVolDataReturn == "NoDataPresent":
                        logger.info("No Trade Happend For Stocks as Table Data is not present")
                        continue
                    elif len(deltaVolDataReturn) == 2:
                        logger.info("Checking Delta and Volume Match Condition for stock ={} and strike is ={}".format(stockName, eachStrike))
                        deltaValue = deltaVolDataReturn[0]
                        volumes = deltaVolDataReturn[1]
                        logger.info("Recevied delta value is = {} and Volume is = {} from DB for stock = {}".format(deltaValue, volumes, stockName))
                        if deltaValue <= PUT_DELTA_CHECK and volumes >= VOLUME_CHECK:
                            #------------
                            # TODO: MUST REMOVE FOLLOWING CODE
                            # NOTE: TO test order placement temporary code, 
                            # -----------
                            #getCandlesData = client.get_bars(stock=stockName, barSize=candleTime, limit="day")
                            #atrValue = float(getATRValue(stockName, getCandlesData))
                            #toTrade = True
                            # -----------
                            
                            toTrade, atrValue, ema_S, algo_audit = checkAlgoAndTrade(stockName, "PUT")
                            logger.info("\n EMA_S Values for 8D, 13D, and 21D are = {}\n".format(ema_S))

                            ema_S_8 = ema_S[0][len(ema_S[0])-1]
                            ema_S_13 = ema_S[1][len(ema_S[1])-1]
                            ema_S_21 = ema_S[2][len(ema_S[2])-1]
                            
                            # SCLAP HIT
                            if toTrade and ("heavy" in signalStrength.lower() or "strong" in signalStrength.lower()):
                                _pc = _signal_entry_context(
                                    decision_path="PUT_heavy_or_strong_signal",
                                    stock_name=stockName,
                                    right_match=rightMatch,
                                    strike=eachStrike,
                                    trade_expiry=tradeExpiry,
                                    signal_strength=signalStrength,
                                    delta_value=deltaValue,
                                    volume=volumes,
                                    delta_threshold=PUT_DELTA_CHECK,
                                    volume_threshold=VOLUME_CHECK,
                                    to_trade=toTrade,
                                    atr_value=atrValue,
                                    ema_8=ema_S_8,
                                    ema_13=ema_S_13,
                                    ema_21=ema_S_21,
                                    algo_audit=algo_audit,
                                    supertrend_engulf_gate_passed=conditionMatch,
                                    signal_path_audit=signal_path_audit,
                                )
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="PUT",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick,
                                                        placement_context=_pc)
                                if orderData == "orderPlaced":
                                    dataReturn = "orderPlaced"
                                    break
                                else:
                                    logger.info(f"Order Not Placed for stock={stockName}, Right={rightMatch}, Strike={eachStrike}, Expiry={tradeExpiry}\nBecause ={orderData}")
                                    dataReturn = orderData
                                    continue
                            elif toTrade and ((ema_S_21>=ema_S_13 and ema_S_13<=ema_S_8) or ema_S_13>=ema_S_8 ):
                                _pc = _signal_entry_context(
                                    decision_path="PUT_scalp_ema_conditions",
                                    stock_name=stockName,
                                    right_match=rightMatch,
                                    strike=eachStrike,
                                    trade_expiry=tradeExpiry,
                                    signal_strength=signalStrength,
                                    delta_value=deltaValue,
                                    volume=volumes,
                                    delta_threshold=PUT_DELTA_CHECK,
                                    volume_threshold=VOLUME_CHECK,
                                    to_trade=toTrade,
                                    atr_value=atrValue,
                                    ema_8=ema_S_8,
                                    ema_13=ema_S_13,
                                    ema_21=ema_S_21,
                                    algo_audit=algo_audit,
                                    supertrend_engulf_gate_passed=conditionMatch,
                                    signal_path_audit=signal_path_audit,
                                )
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="PUT",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick,
                                                        placement_context=_pc)
                                if orderData == "orderPlaced":
                                    dataReturn = "orderPlaced"
                                    break
                                else:
                                    logger.info(f"Order Not Placed for stock={stockName}, Right={rightMatch}, Strike={eachStrike}, Expiry={tradeExpiry}\nBecause ={orderData}")
                                    dataReturn = orderData
                                    continue
                            elif toTrade and ((ema_S_21>=ema_S_13 and ema_S_13>=ema_S_8) or ema_S_21-ema_S_13 >= atrValue*0.77):
                                ###### INTRADAY HIT
                                _pc = _signal_entry_context(
                                    decision_path="PUT_intraday_ema_conditions",
                                    stock_name=stockName,
                                    right_match=rightMatch,
                                    strike=eachStrike,
                                    trade_expiry=tradeExpiry,
                                    signal_strength=signalStrength,
                                    delta_value=deltaValue,
                                    volume=volumes,
                                    delta_threshold=PUT_DELTA_CHECK,
                                    volume_threshold=VOLUME_CHECK,
                                    to_trade=toTrade,
                                    atr_value=atrValue,
                                    ema_8=ema_S_8,
                                    ema_13=ema_S_13,
                                    ema_21=ema_S_21,
                                    algo_audit=algo_audit,
                                    supertrend_engulf_gate_passed=conditionMatch,
                                    signal_path_audit=signal_path_audit,
                                )
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="PUT",
                                                        expiry=tradeExpiry, 
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick,
                                                        placement_context=_pc)
                                if orderData == "orderPlaced":
                                    dataReturn = "orderPlaced"
                                    break
                                else:
                                    logger.info(f"Order Not Placed for stock={stockName}, Right={rightMatch}, Strike={eachStrike}, Expiry={tradeExpiry}\nBecause ={orderData}")
                                    dataReturn = orderData
                                    continue
                            else:
                                dataReturn = "algoNotMatched"
                                logger.info("PUT -> AlgoNotMatched for stock = {} = Values are => toTrade = {}, atrValue = {} , ema Values = {}".format(stockName, toTrade, atrValue, ema_S))
                        else:
                            dataReturn = "deltaVolumeNotMatched"
                            logger.info("Delta/Volume values not matched. received Delta is = {} and Volume is = {} ** Expected Delta is = {} and Volume is = {} \n".format(deltaValue, volumes, PUT_DELTA_CHECK, VOLUME_CHECK))
                # logger.info("stockMapperDict Current Value After Checks is  = {}".format(stockMapperDict))
    except Exception as tradeError:
        logger.error(f"Current Error During Trade logic = {tradeError}", exc_info=True)
    stock_name = dataValueSet[0][2].upper() if dataValueSet and len(dataValueSet[0]) > 2 else "?"
    logger.info(f"Stock {stock_name} checkConditionsAndTrade - end")
    _emit_log(f"Trade check result: {stock_name} → {dataReturn}", "INFO", "signal")
    return dataReturn

def getAllPositions():
    allStocksPosition = []
    logger.info('getting All Open Positions')
    # allPositions = callTWS(whatToGet="reqPositions")
    allPositions = client.get_all_positions()

    for ePos in allPositions:
        totalQty = int(abs(ePos.position))
        if totalQty > 0:
            allStocksPosition.append(ePos.symbol)

    return allStocksPosition

def cancel_all_orders():
    logger.info("cancelling all orders")
    if not client.isConnected():
        logger.error("TWS not connected.")
        return
    client.cancel_all_orders()

# def squareOffOrder(OrderId):
#     orderStatusData = getAllOrdersStatus()
#     oLen = len(orderStatusData)

#     return orderStatusData


## This Function is a Check if Market time is 3.30PM or above then Close the existing orders at market price and close the program execution also
#def timeCheckAndCloseProgram():
def timeCheckAndCloseProgram(SUB_ACCOUNT_ID, profit_amount_day, loss_amount_day):
    """
    Check if the current time is past the end time of the trading day, and if so, cancel all open orders and square
    off any existing positions. If an error occurs during this process, log the error and advise the user to close
    their positions manually.

    Returns:
        bool: True if the program should be closed, False otherwise.
    """
    global DAY_LOCKED, STOP_TRADING, CLOSE_ALL_ORDERS
    logger.info(f"Checking timeCheckAndCloseProgram")
    tradeMarketTime = False
    pnlData, realizedPNL = client.get_pnl(SUB_ACCOUNT_ID)
    logger.info(f"Account {SUB_ACCOUNT_ID} PNL is {pnlData}")
    try:
        # Use global endTime if set (by main_call or trading engine); else default 15:45
        end_time_val = globals().get("endTime", "1545")
        marketTime = datetime.now().astimezone(NY_TZ).strftime("%H-%M")
        # endTime from config is already a string like "1545" (HHmm)
        end_time_str = str(end_time_val).replace(":", "").replace("-", "")[:4]
        if marketTime.replace("-", "") > end_time_str:
            logger.info(f"Market Time is ={marketTime} > {end_time_val}. So Closing All Placed Orders if Any Or Closing Execution if no Orders Present")
            tradeMarketTime = True
            _emit_log(f"Market hours ended ({marketTime} > {end_time_val}) — closing all positions", "WARN", "risk")
            logger.info("Cancel All Placed Order/s And Square Off all existing Bought Quantities if any at MKT Price")
            DAY_LOCKED = True
            STOP_TRADING = True
            CLOSE_ALL_ORDERS = True
            cancel_all_orders()
            getAndBuyAfterMarketEnd()
        elif pnlData >= profit_amount_day or pnlData <= loss_amount_day:
            tradeMarketTime = True
            logger.info(f"Day PNL Target HIT. Either {pnlData} is Greater than Profit Target {profit_amount_day} or Less than Loss Target {loss_amount_day}")
            logger.info("Cancel All Placed Order/s And Square Off all existing Bought Quantities if any at MKT Price as Daily Profit/StopLoss Target HIT.")
            side = "profit" if pnlData >= profit_amount_day else "loss"
            _emit_log(f"DAY LIMIT HIT ({side}): P&L ${pnlData:.2f} — cancelling orders & closing positions", "ERROR", "risk")
            DAY_LOCKED = True
            STOP_TRADING = True
            CLOSE_ALL_ORDERS = True
            cancel_all_orders()
            getAndBuyAfterMarketEnd()
        else:
            logger.info(f"timeCheckAndCloseProgram:=>> Market Time is = {marketTime} <={end_time_val}. Keep Going Trade")
            logger.info(f"Account Current: ${pnlData} SL: -${loss_amount_day} TP: ${profit_amount_day}...")
    except Exception as lastError:
        logger.info(f"Got error during final call of day is = {lastError}")
        logger.info("Please Close All Positions Manually")
        tradeMarketTime = True

    return tradeMarketTime
    
def squareOffAll():
    logger.info("Cancel All Placed Order/s And Square Off all existing Bought Quantities if any at MKT Price as SquareOff Button HIT.")
    cancel_all_orders()
    getAndBuyAfterMarketEnd()
    sys.exit()
    sys.exit(0)
    sys.exit(1)
    os._exit(1)
    

def getAndBuyAfterMarketEnd(buffer_seconds=None):
    """Close all TWS positions at market. Each position wrapped in try/except so one failure does not abort the rest.
    After first pass, waits buffer_seconds (from config emergency_close_buffer_seconds or 5), re-checks TWS,
    and retries MKT close for any positions still open."""
    try:
        if not client:
            logger.warning("getAndBuyAfterMarketEnd: client is None — cannot close positions")
            return
        buf = buffer_seconds
        if buf is None:
            file_data = globals().get("fileData") or {}
            buf = file_data.get("emergency_close_buffer_seconds", 5) if isinstance(file_data, dict) else 5
        try:
            buf = max(0, int(buf) if buf is not None else 5)
        except (TypeError, ValueError):
            buf = 5

        def _close_positions(positions_to_close, pass_label=""):
            closed = 0
            failed = []
            for i, ePos in enumerate(positions_to_close):
                totalQty = int(abs(ePos.position))
                if totalQty <= 0:
                    continue
                key = f"{ePos.symbol}{ePos.expiry}{ePos.right}{ePos.strike}"
                try:
                    action = "SELL"
                    orderId = placeOrder(symbol=ePos.symbol,
                                         expiry=ePos.expiry,
                                         strike=ePos.strike,
                                         right=ePos.right,
                                         action=action,
                                         totalQuantity=totalQty,
                                         orderType="MKT",
                                         options_tick=None,
                                         closing_order=True,
                                         is_sqare_off=True)
                    if orderId and str(orderId) not in ("TWS API connection error", "DayLocked", "error", "None"):
                        closed += 1
                        logger.info(f"Square off [{pass_label}][{i+1}/{len(positions_to_close)}]: {key} — orderId={orderId} PLACED")
                    else:
                        failed.append((key, orderId))
                        logger.warning(f"Square off [{pass_label}][{i+1}/{len(positions_to_close)}]: {key} — placeOrder returned {orderId}")
                except Exception as ex:
                    failed.append((key, str(ex)))
                    logger.error(f"Square off [{pass_label}][{i+1}/{len(positions_to_close)}]: {key} FAILED — {ex}", exc_info=True)
            return closed, failed

        OPEN_POSITION = list(client.get_all_positions())
        positions_to_close = [p for p in OPEN_POSITION if p and int(abs(getattr(p, "position", 0))) > 0]
        logger.info(f"getAndBuyAfterMarketEnd: {len(positions_to_close)} position(s) to close (of {len(OPEN_POSITION)} total) — placing MKT close for each")

        if len(positions_to_close) == 0:
            logger.info("No options positions with qty>0 to close")
            return

        closed, failed = _close_positions(positions_to_close, pass_label="1st")

        if buf > 0 and len(positions_to_close) > 0:
            logger.info(f"getAndBuyAfterMarketEnd: waiting {buf}s buffer, then re-checking TWS for still-open positions")
            time.sleep(buf)
            OPEN_POSITION_2 = list(client.get_all_positions())
            still_open = [p for p in OPEN_POSITION_2 if p and int(abs(getattr(p, "position", 0))) > 0]
            if still_open:
                logger.warning(f"getAndBuyAfterMarketEnd: {len(still_open)} position(s) still open after buffer — retrying MKT close")
                closed2, failed2 = _close_positions(still_open, pass_label="2nd")
                closed += closed2
                failed.extend(failed2)
            else:
                logger.info("getAndBuyAfterMarketEnd: all positions closed after buffer — no retry needed")

        logger.info(f"getAndBuyAfterMarketEnd done: {closed} placed, {len(failed)} failed. Failed: {failed}")
        if failed:
            try:
                _emit_log(f"Emergency close: {closed} placed, {len(failed)} failed — check logs", "WARN", "order")
            except Exception:
                pass
    except Exception as ex:
        logger.error(f"Error in getAndBuyAfterMarketEnd: {ex}", exc_info=True)
    
def timeDecayDiff(expiryDate):
    logger.info("Current Expiry data is = {}".format(expiryDate))
    import datetime
    today = datetime.date.today()
    todayDate = today.strftime("%Y%m%d")
    logger.info("Today date is = {}".format(todayDate))
    
    diffTimedecay = int(tradeExpiry_val) - int(todayDate)
    
    logger.info("\n\n Time Decay Days Diff remaing from expiry is = {}\n\n".format(diffTimedecay))
    
    return diffTimedecay
    


def takeTrade(atrVale:float, stock_symbol: str, expiry: str, strike: float, right: str, options_tick: Tick, stock_tick: Tick, placement_context=None):
    if DAY_LOCKED and CLOSE_ALL_ORDERS:
        logger.warning("Trading blocked: DAY LOCK active (PnL limit hit)")
        return "DayLocked"
    if globals().get("CLOSE_ALL_IN_PROGRESS", False):
        logger.warning("Trading blocked: Close All in progress")
        return "CloseAllInProgress"

    logger.info(f"All Algo's conditions meet, now doing a check for Options Price must be ${MAX_CONTRACT_AMOUNT} or low")
    # tick = client.get_options_data(symbol=takeTick, expiry=takeExpiry, right=takeRight, strike=takeStrike)
    
    trade_key = "{}_{}".format(stock_symbol, right)

    bidPrice = options_tick.bid
    askPrice = options_tick.ask
    lastPrice = options_tick.last
    activeVol = options_tick.volume

    if lastPrice == -1:
        if bidPrice > 0 and askPrice > 0:
            lastPrice = round((bidPrice + askPrice) / 2, 2)
            logger.info(f"options_tick.last=-1, using mid-price ${lastPrice:.2f} (bid=${bidPrice:.2f}, ask=${askPrice:.2f})")
        else:
            return "priceConditionNotMatched"

    if bidPrice <= 0 and askPrice <= 0:
        logger.warning(f"{stock_symbol} {right}: No valid bid/ask (bid={bidPrice}, ask={askPrice}) — skipping")
        return "priceConditionNotMatched"

    # Skip strikes with price below $0.25
    _prices = [p for p in (bidPrice, askPrice, lastPrice) if p > 0]
    min_price = min(_prices) if _prices else 999.0
    if min_price < 0.25:
        logger.info(f"{stock_symbol} {right}: Skip strike with price ${min_price:.2f} < $0.25")
        _emit_log(f"{stock_symbol} {right}: Skip strike below $0.25 (price=${min_price:.2f})", "INFO", "order")
        return "strikeBelow25c"

    midPrice = (bidPrice + askPrice) / 2 if (bidPrice > 0 and askPrice > 0) else lastPrice
    spreadGap = (askPrice - bidPrice) if (bidPrice > 0 and askPrice > 0) else 0.0
    
    if spreadGap >=0.12:
        _emit_log(f"{stock_symbol} {right}: Spread too wide ${spreadGap:.2f} ≥ $0.12 — skipping", "INFO", "order")
        return "SpreadGapHighOver0.12ComingOut"

    if bidPrice == -1.0:
        bidPrice = lastPrice - 0.02
    if askPrice == -1.0:
        askPrice = lastPrice + 0.02
    # askMinusBidPrice = float(askPrice) - float(bidPrice)
    askMinusBidPrice = round(askPrice - bidPrice, 2)
    logger.info(f"Spread is {askMinusBidPrice}.")

    if askMinusBidPrice > 0.4:
        logger.info("Spread Difference is greater than 0.05 so not doing anything and continue for next checks")
        _emit_log(f"{stock_symbol} {right}: Spread ${askMinusBidPrice:.2f} > $0.40 — too wide, skipping", "INFO", "order")
        return "spreadHigherThan0.05"
    elif askMinusBidPrice <= 0.03:
        ORDER_TYPE = "MKT"
        logger.info("Spread is 0.03 and less so taking ASKPrice/MKT Price to place order")
        tradePrice = round(askPrice, 2)

    if askMinusBidPrice > 0.03:
        ORDER_TYPE = "LMT"
        logger.info("Spread is greater than 0.03 so using BID price Price to place order")
        tradePrice = round(bidPrice, 2)

    logger.info(f"Current tradePrice is = {tradePrice}")
    
    # ============ PROFIT/STOPLOSS CALCULATION - THIS IS CRITICAL ============
    marketTime = datetime.now().astimezone(pytz.timezone("America/New_York")).strftime("%H-%M")
    marketTime = marketTime.replace("-", "")
    marketTimeInt = int(marketTime)
    
    TimeDecayDiffVal = timeDecayDiff(tradeExpiry_val)
    if "spy" in stock_symbol.lower() or "qqq" in stock_symbol.lower():
        TimeDecayDiffVal = -1
        
    # Log the calculation parameters
    logger.info(
        f"PL_CALC {stock_symbol}: Entry=${tradePrice:.2f} ATR=${atrVale:.4f} "
        f"Time={marketTime} DTE={TimeDecayDiffVal} SPY/QQQ={'spy' in stock_symbol.lower() or 'qqq' in stock_symbol.lower()}"
    )

    # TP/SL: underlying ATR → dollar distance, then cap to a fraction of option premium (see option_targets.py)
    _cfg = globals().get("fileData") or {}
    _tg = targets_from_config(tradePrice, float(atrVale), _cfg)
    profitPrice = _tg.profit_price
    auxPrice = _tg.aux_price
    max_tp_price = _tg.max_tp_price
    min_sl_price = _tg.min_sl_price
    atr_dist = _tg.dist_applied
    atr_dist_raw = _tg.atr_dist_raw
    _max_pct = float(_cfg.get("option_tp_sl_max_pct", 0.15))

    # Special 0DTE returns (no trade in these cases)
    if TimeDecayDiffVal == 0:
        if marketTimeInt >= 1445:
            return "0dte2ndhalfnotrade"
        if tradePrice <= 0.1:
            return "0dtepricebelow10cent"

    logger.info(
        f"TP_SL_MODEL {stock_symbol}: premium_cap={_max_pct:.0%} of entry | "
        f"atr_raw_dist=${atr_dist_raw:.4f} applied_dist=${atr_dist:.4f} → TP=${profitPrice:.2f} SL=${auxPrice:.2f}"
    )

    # ============ LOG FINAL CALCULATED VALUES ============
    profit_pct = ((profitPrice - tradePrice) / tradePrice * 100) if tradePrice > 0 else 0
    loss_pct = ((tradePrice - auxPrice) / tradePrice * 100) if tradePrice > 0 else 0
    
    rr = ((profitPrice - tradePrice) / (tradePrice - auxPrice)) if (tradePrice - auxPrice) > 0 else 0
    logger.info(
        f"TARGETS {stock_symbol}: Entry=${tradePrice:.2f} | TP=${profitPrice:.2f} (+{profit_pct:.1f}%) "
        f"| SL=${auxPrice:.2f} (-{loss_pct:.1f}%) | Increment=${PROFIT_INCREMENT:.2f} | R:R=1:{rr:.2f}"
    )

    logger.info(f"\n\nCurrent Options Price is = {lastPrice} And Current Active Volume = {activeVol}")

    if (lastPrice * 100) <= MAX_CONTRACT_AMOUNT:
        totalQty = int(useAmount[stock_symbol]["amount"] / (tradePrice * 100))
        if totalQty==0:
            totalQty = 1

        #logger.info(f"Amount to Use is = {useAmount} and Quantities to trade is = useAmount/tradPrice = {totalQty}")
        logger.info(f"Amount to Use is = {useAmount[stock_symbol]['amount']} and Quantities to trade = {totalQty}")
        rr_ratio = (profitPrice - tradePrice) / (tradePrice - auxPrice) if (tradePrice - auxPrice) > 0 else 0
        _emit_log(
            f"TRADE SETUP: {stock_symbol} {right} {strike} @ ${tradePrice:.2f} | TP=${profitPrice:.2f} SL=${auxPrice:.2f} | R:R=1:{rr_ratio:.1f} | Qty={totalQty}",
            "INFO", "order"
        )

        execution_snapshot = {
            "execution": {
                "bid": float(bidPrice),
                "ask": float(askPrice),
                "last": float(lastPrice),
                "option_tick_volume": float(activeVol) if activeVol is not None else None,
                "mid_price": float(midPrice),
                "spread_abs": float(askMinusBidPrice),
                "order_type": ORDER_TYPE,
                "trade_price": float(tradePrice),
                "take_profit": float(profitPrice),
                "stop_loss": float(auxPrice),
                "atr_dist": float(atr_dist),
                "atr_dist_raw": float(atr_dist_raw),
                "option_tp_sl_max_pct": float(_max_pct),
                "option_tp_sl_min_dist": float(_cfg.get("option_tp_sl_min_dist", 0.02)),
                "max_tp_price": float(max_tp_price),
                "min_sl_price": float(min_sl_price),
                "underlying_atr": float(atrVale) if atrVale is not None else None,
                "quantity": int(totalQty),
                "use_amount_usd": float(useAmount[stock_symbol]["amount"]),
                "contract_notional_cents": float(lastPrice * 100),
                "time_decay_dte": int(TimeDecayDiffVal),
                "market_time_ny_hhmm_int": int(marketTimeInt),
                "underlying_last": float(getattr(stock_tick, "last", 0) or 0) if stock_tick else None,
            }
        }
        merged_context = {**(placement_context or {}), **execution_snapshot}

        # action = "BUY"
        currentOrderId = placeAndVerifyOrder(
                            symbol=stock_symbol, 
                            expiry=expiry,
                            strike=strike, 
                            right=right, 
                            action="BUY", 
                            totalQuantity=totalQty,
                            orderType=ORDER_TYPE, 
                            lmtPrice=tradePrice, 
                            profitPrice=profitPrice,
                            auxPrice=auxPrice,
                            options_tick=options_tick,
                            stock_tick=stock_tick,
                            placement_context=merged_context,
                            max_tp_price=max_tp_price,
                            min_sl_price=min_sl_price,
                            underlying_atr=float(atrVale) if atrVale is not None else None)

        # Cooldown is recorded in order_manager.process_fill when exit order fills (not on placement)
        logger.info(f"currentOrderId is = {currentOrderId}")
        return "orderPlaced"
    else:
        logger.info(f"Options Price is Above ${MAX_CONTRACT_AMOUNT} so going for next check")
        _emit_log(f"{stock_symbol} {right}: Options price ${lastPrice * 100:.0f} > max ${MAX_CONTRACT_AMOUNT} — too expensive", "INFO", "order")
        return "priceConditionNotMatched"


def get_stock_strikes(symbol: str):
    logger.info(f"{symbol} get strikes.")
    strikes = client.get_strikes(symbol=symbol)
    return { "Strike" : strikes }

def get_strikes_map(stock_list):
    return {symbol: get_stock_strikes(symbol=symbol) for symbol in stock_list}

def init_order_requests():
    try:
        if not client.isConnected():
            logger.info("TWS not connected.")
            return

        logger.info("Request Open Orders")
        client.reqOpenOrders()
        logger.info("Request Positions")
        client.reqPositions()
        logger.info("Request PnL")
        client.reqPnL(10001, SUB_ACCOUNT_ID, "")
    except Exception as ex:
        logger.error(f"init_order_requests: {ex}", exc_info=True)


def _wait_underlying_ticks_ready(client, stock_contracts, timeout_sec=3.0, poll_interval=0.05):
    """
    Poll market data until STK underlyings have a usable last price, or timeout.
    Replaces a fixed sleep so startup can finish earlier when TWS is fast.
    """
    stk_contracts = [c for c in stock_contracts if getattr(c, "secType", "") == "STK"]
    fut_contracts = [c for c in stock_contracts if getattr(c, "secType", "") != "STK"]
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if stk_contracts:
            all_ok = True
            for c in stk_contracts:
                md = client.get_data(contract=c)
                if md is None:
                    all_ok = False
                    break
                last = getattr(md, "last", -1)
                if last is None or last <= 0 or last == -1:
                    all_ok = False
                    break
            if all_ok:
                return
        elif fut_contracts:
            for c in fut_contracts:
                md = client.get_data(contract=c)
                if md is not None:
                    last = getattr(md, "last", -1)
                    if last is not None and last > 0 and last != -1:
                        return
        else:
            return
        time.sleep(poll_interval)
    logger.info(
        "init_data_feed: underlying tick wait %.1fs timeout — continuing",
        timeout_sec,
    )


def _wait_option_snapshots_ready(client, options_contracts, timeout_sec=8.0, poll_interval=0.15):
    """
    Poll option snapshot ticks until enough contracts have bid/ask/last, or timeout.
    """
    if not options_contracts:
        return
    n = len(options_contracts)
    need = max(1, min(n, int(n * 0.4)))
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        good = 0
        for contract in options_contracts:
            md = client.get_data(contract=contract)
            if not md:
                continue
            last = getattr(md, "last", -1)
            bid = getattr(md, "bid", -1)
            ask = getattr(md, "ask", -1)
            try:
                if (last is not None and float(last) > 0) or (bid is not None and float(bid) > 0) or (ask is not None and float(ask) > 0):
                    good += 1
            except (TypeError, ValueError):
                continue
        if good >= need:
            logger.info(
                "init_data_feed: option snapshots %s/%s ready — continuing",
                good,
                n,
            )
            return
        time.sleep(poll_interval)
    logger.info(
        "init_data_feed: option snapshot wait %.1fs timeout — continuing (%s OPT)",
        timeout_sec,
        n,
    )


def init_data_feed():
    """
    Initializes the data feed by connecting to the TWS, subscribing to the stocks in `stockList`, and
    subscribing to the options contracts.

    The function first checks if the TWS connection is established. If not, it logs an error message and returns.

    The function then creates a list of stock contracts and subscribes to the historical data for each stock with
    a bar size of "1 min". The function also generates a strikes_map with the stock symbols and their corresponding
    strikes.

    The function then selects the strikes nearest to the underlying price and creates call and put options contracts
    for each selected strike. The function subscribes to the snapshot data for each option contract and waits for 10
    seconds. Finally, it subscribes to the live data for each option contract.
    """
    try:
        if not client.isConnected():
            logger.info("TWS not connected.")
            # Write empty file so fetch_all_strike_expiries() does not fail with "file not found"
            try:
                with open("expiryStrike.json", "w", encoding="utf-8") as fp:
                    json.dump({}, fp)
            except Exception:
                pass
            return

        # STK = stocks, FUT = futures (e.g. MNQU5, NQU5), OPT = options (calls/puts on STK underlyings).
        stock_list_to_trade = globals().get("stock_list_to_trade", None) or {}
        logger.info(f"Subscribing to underlyings: {stockList}. Then options (OPT) on stocks for strategy.")
        _emit_log(f"Subscribing to {len(stockList)} underlyings: {', '.join(stockList)}", "INFO", "signal")

        # Create a list of underlying contracts (STK or FUT)
        stock_contracts = []
        for symbol in stockList:
            exchange = stock_list_to_trade.get(symbol, "SMART")
            is_future = (exchange == "CME") or (len(symbol) >= 4 and symbol[-1].isdigit() and symbol[-2].isalpha())
            if is_future:
                stock_contract = client.get_futures_contract(symbol, exchange)
            else:
                stock_contract = client.get_stock_contract(symbol)
            stock_contracts.append(stock_contract)

        # Subscribe to live and historical data for each underlying
        for stock_contract in stock_contracts:
            client.subscribe(contract=stock_contract)
            client.subscribe_historical_data(contract=stock_contract, fetchValue=fetchValue, barSize=candleTime)
        _wait_underlying_ticks_ready(client, stock_contracts, timeout_sec=3.0, poll_interval=0.05)

        # Build strikes_map only for stocks (options chain); futures have no options in this flow
        stock_only_list = [c.symbol for c in stock_contracts if getattr(c, "secType", "") == "STK"]
        strikes_map = get_strikes_map(stock_list=stock_only_list) if stock_only_list else {}
        for sym, data in strikes_map.items():
            count = len(data.get("Strike", []))
            logger.info(f"STRIKES_LOADED: {sym} -> {count} strikes from TWS")
        with open("expiryStrike.json", "w",  encoding="utf-8") as fp:
            json.dump(strikes_map, fp)

        # Create and subscribe to options contracts only for STK underlyings
        options_contracts = []
        for stock_contract in stock_contracts:
            if getattr(stock_contract, "secType", "") != "STK":
                continue
            market_data = client.get_data(contract=stock_contract)
            if not market_data or stock_contract.symbol not in strikes_map:
                continue
            strikes = strikes_map[stock_contract.symbol]["Strike"]
            logger.info(f"{stock_contract.symbol} UNDERLYING PRICE IS = {market_data.last}")
            ls, hs = get10StrikesNearUnderlying(strikeList=list(strikes), undPrc=market_data.last, range_limit=4)
            selected_strikes = ls + hs

            for strike in selected_strikes:
                tradeExpiry = tradeExpiry_val
                if "spy" in stock_contract.symbol.lower() or "qqq" in stock_contract.symbol.lower():
                    tradeExpiry = spy_qqq_tradeExpiry
                call_option = client.get_options_contract(stock_contract.symbol, tradeExpiry, "C", strike)
                put_option = client.get_options_contract(stock_contract.symbol, tradeExpiry, "P", strike)
                client.subscribe(contract=call_option, snapshot=True)
                client.subscribe(contract=put_option, snapshot=True)
                options_contracts.extend((call_option, put_option))

        _wait_option_snapshots_ready(client, options_contracts, timeout_sec=8.0, poll_interval=0.15)
        for contract in options_contracts:
            client.subscribe(contract=contract)
    except Exception as ex:
        logger.error(f"init_data_feed: {ex}")


def _expiry_strike_paths():
    """Return candidate paths for expiryStrike.json (CWD first, then bundle when frozen)."""
    paths = [os.path.join(os.getcwd(), "expiryStrike.json")]
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", "")
        if base:
            paths.append(os.path.join(base, "expiryStrike.json"))
    return paths


def fetch_all_strike_expiries():
    logger.info(
        f"Fetching All strikes/Expiries List for all stocks. = {stockList}"
    )
    for path in _expiry_strike_paths():
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as fp:
                    return [json.loads(fp.read())]
        except Exception as e:
            logger.warning(f"Could not read {path}: {e}")
            continue
    logger.warning("expiryStrike.json not found in CWD or bundle. Using empty strikes.")
    return [{}]

def check_order_conditions(tick: Tick):
    pass

def event_processor(event_queue: Queue, count: int) -> None:
    """
    Processes events from the event queue.

    Parameters:
        event_queue (Queue): The queue containing the events to be processed.
        count (int): The count of the event processor.

    Returns:
        None
    """
    global STOP_TRADING
    logger.info(f"Starting event processor #{count + 1}")
    _emit_log(f"Event processor #{count + 1} started — scanning for signals", "INFO", "signal")
    tries = 0
    keep_running = True
    while keep_running:
        if STOP_TRADING:
            logger.info(f"Event processor #{count + 1} stopping (STOP_TRADING)")
            keep_running = False
            break
        try:
            # Get the event data from the queue
            # block=True respects timeout; block=False ignores timeout (busy-spin). Use blocking wait to reduce CPU.
            event_data = event_queue.get(block=True, timeout=0.25)
            tick: Tick = event_data["tick"]
            sym = getattr(tick.contract, "symbol", "") or getattr(tick.contract, "localSymbol", "") or getattr(tick, "symbol", "")
            sec_type = getattr(tick.contract, "secType", "")
            _emit_log(f"IBKR tick: {sym} ({sec_type}) last={getattr(tick, 'last', -1)} bid={getattr(tick, 'bid', -1)}", "DEBUG", "data")
            
            # If the security type is 'OPT' and an active order exists
            if tick.contract.secType == "OPT" and tick.active_order is not None:
                logger.debug(f"Event path: OPT tick with active_order -> TP/SL check for {getattr(tick.active_order, 'option_symbol', tick.contract.symbol or '?')}")
                order_mgr.check_and_close_position(tick=tick)
            elif tick.contract.secType == "STK":
                # Gate: skip signal scan when market is closed (from config.json market_hours or scriptStartTime/scriptEndTime)
                _start = str(globals().get("startTime", "0935")).replace(":", "").replace("-", "")[:4]
                _end = str(globals().get("endTime", "1545")).replace(":", "").replace("-", "")[:4]
                _now_hm = datetime.now().astimezone(NY_TZ).strftime("%H-%M").replace("-", "")
                try:
                    now_int = int(_now_hm)
                    start_int = int(_start)
                    end_int = int(_end)
                    if not (start_int <= now_int <= end_int):
                        _emit_log(f"Signal scan skipped: market closed ({_now_hm} outside {_start}-{_end})", "DEBUG", "signal")
                        event_queue.task_done()
                        continue
                except (ValueError, TypeError):
                    pass  # fallback: allow scan if time parsing fails
                # Get the result of the call/put engulf check
                _emit_log(f"Signal scan: {tick.contract.symbol} (IBKR tick → Engulfing-based)", "DEBUG", "signal")
                dataEngulf = getCallPutEngulfCheck(tick.contract.symbol)
                logger.info(f"\n dataEngulf = {dataEngulf}\n")
                if dataEngulf[0]:
                    sig_direction = dataEngulf[1]  # CALL or PUT
                    sig_strength = dataEngulf[3]    # strongBuy, heavyBuy, etc.
                    _emit_log(f"Signal detected: {tick.contract.symbol} → {sig_direction} ({sig_strength})", "INFO", "signal")
                    # Throttle UI signal popups: same symbol+direction at most once per 60s
                    _sig_key = f"{tick.contract.symbol}_{sig_direction}"
                    _now = time.time()
                    _last_emit = _signal_emit_times.get(_sig_key, 0)
                    if _now - _last_emit >= 60:
                        _signal_emit_times[_sig_key] = _now
                        underlying_price = getattr(tick, "last", None) or getattr(tick, "close", -1)
                        if underlying_price is None or underlying_price <= 0:
                            underlying_price = 0.0
                        _emit_signal(
                            tick.contract.symbol,
                            sig_direction,
                            0.0,
                            float(underlying_price),
                            sig_strength or "signal",
                        )
                    # Skip trading on first snapshot per symbol and on unchanged signal (wait for *next* signal after start)
                    if _post_start_signal_blocks_trade(tick.contract.symbol, dataEngulf):
                        event_queue.task_done()
                        continue
                    result = checkConditionsAndTrade((dataEngulf, dataStrike), tick)
                    logger.info(f"checkConditionsAndTrade: {result}")
                    if result == "orderPlaced":
                        _emit_log(f"Trade executed: {tick.contract.symbol} {sig_direction} order placed", "INFO", "order")
                    elif result == "positionAlreadyPresent":
                        _emit_log(f"{tick.contract.symbol}: Position already open — skipping", "DEBUG", "signal")
                    elif result == "orderAlreadyPresent":
                        _emit_log(f"{tick.contract.symbol}: Pending order exists — skipping", "DEBUG", "signal")
                    elif result == "conditionNotMatched":
                        _emit_log(f"{tick.contract.symbol}: Conditions not met for trade", "DEBUG", "signal")
                    elif isinstance(result, str) and result != "None":
                        _emit_log(f"{tick.contract.symbol}: {result}", "DEBUG", "signal")
                else:
                    _emit_log(f"{tick.contract.symbol}: No signal (engulfing no match)", "DEBUG", "signal")
            
            # Mark the event as processed
            event_queue.task_done()
        except Empty:
            if STOP_TRADING:
                keep_running = False
            elif client is not None and not client.isConnected():
                # Re-check STOP_TRADING to avoid logging during shutdown (race with engine.stop)
                if STOP_TRADING:
                    keep_running = False
                else:
                    logger.error("TWS is disconnected — engine loop handles reconnect")
                    _emit_log("TWS disconnected — waiting for engine reconnect", "WARN", "system")
                    time.sleep(5.0)
                    if getattr(client, "connection_closed", False):
                        keep_running = False
        except Exception as ex:
            logger.error(f"Event processor error: {ex}", exc_info=True)
            _emit_log(f"Event processor error: {ex}", "ERROR", "trading")


def check_and_close_all_open_positions():
    """
    Closes all open positions by selling the assets held in each position.
    """
    try:
        # Get all open positions
        positions = client.get_all_positions()

        # If there are no positions, log a message indicating so
        if len(positions) == 0:
            logger.info("There are no open positions available")
        else:
            logger.info(f"check_and_close_all_open_positions: closing {len(positions)} position(s) via MKT (day_limit/time/signal)")
            # Iterate over each position
            for pos in positions:
                # Calculate the total quantity held
                total_qty = int(abs(pos.position))

                # If the total quantity is greater than zero, create an order to sell the assets held
                if total_qty > 0:
                    action = "SELL"
                    placeOrder(symbol=pos.symbol,
                                expiry=pos.expiry, 
                                strike=pos.strike,
                                right=pos.right, 
                                action=action, 
                                totalQuantity=total_qty,
                                orderType="MKT",
                                closing_order=True)

    except Exception as ex:
        # If any exception is encountered, log an error message with the exception information
        logger.error(f"{ex}", exc_info=True)


def init_start_event_processors():
    processors = None
    if client.isConnected():
        arm_trading_session_gates()
        # Create the specified number of event processors
        processors = [Thread(target=event_processor, args=(event_queue, count,)) for count in range(PROCESSORS_COUNT)]
        # Start the event processors
        for processor in processors:
            processor.start()
    else:
        # Log an error message if the TWS client is not connected
        logger.error("TWS is not connected.")

    return processors
    

def pnl_watchdog_thread(account_id, day_profit_limit, day_loss_limit):
    global STOP_TRADING, DAY_LOCKED, DAY_LOCK_DATE, CLOSE_ALL_ORDERS

    logger.info("PnL Watchdog started")

    while True:
        if STOP_TRADING:
            logger.info("PnL watchdog stopping (STOP_TRADING)")
            break
        try:
            pnl, realizedPNL = client.get_pnl(account_id)

            if pnl >= day_profit_limit or pnl <= day_loss_limit:
                logger.error(
                    f" DAILY LIMIT HIT  PnL={pnl} "
                    f"Limits=({day_profit_limit}, {day_loss_limit})")
                _emit_log(
                    f"DAY LOCK: P&L ${pnl:.2f} hit limit (profit=${day_profit_limit:.2f}, loss=${day_loss_limit:.2f}) — trading stopped",
                    "ERROR", "risk"
                )

                STOP_TRADING = True
                DAY_LOCKED = True
                DAY_LOCK_DATE = datetime.now().date()

                cancel_all_orders()
                getAndBuyAfterMarketEnd()
                CLOSE_ALL_ORDERS = True

                logger.error(" Trading LOCKED for the day until manual restart")
                break

        except Exception as e:
            logger.error(f"PnL watchdog error: {e}", exc_info=True)

        time.sleep(1)
    logger.info("CLOSE CURRENT PROCESS")
    hard_exit()


def synchronize_positions():
    """
    This function synchronizes the positions held by the client with their corresponding filled BUY orders. 
    For each position, it looks for the matching filled BUY order in the order manager and subscribes to the corresponding options 
    contract to receive real-time market data. It then sets the order to active and assigns it the corresponding contract and tick data, 
    and adds the order to the order manager's list of active orders.

    Args:
    None

    Returns:
    None
    """
    logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ synchronize positions from DB CHECK $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

    def _norm_exp(s):
        return (s or "").replace("-", "").replace(" ", "").strip()
    def _norm_right(r):
        r = (r or "").upper()
        return "C" if r in ("C", "CALL") else "P" if r in ("P", "PUT") else r

    positions = client.get_all_positions()
    filled_sell_orders = order_mgr.get_filled_orders(order_side='BUY')
    # Filter to non-zero positions for sync
    positions_to_sync = [p for p in positions if p.position != 0]

    logger.info(f"synchronize_positions: {len(positions_to_sync)} TWS positions (qty≠0), {len(filled_sell_orders)} filled BUY orders in DB")
    try:
        _emit_log(f"Syncing positions: {len(positions_to_sync)} TWS, {len(filled_sell_orders)} filled BUY in DB", "INFO", "system")
    except Exception:
        pass

    matched = 0
    unmatched = 0

    for pos in positions:
        if pos.position == 0:
            continue

        right = pos.right
        if right == "C":
            right = "CALL"
        elif right == "P":
            right = "PUT"

        pos_exp = _norm_exp(pos.expiry)
        pos_r = _norm_right(pos.right)

        # finds the matching filled BUY order for the position
        order : OptionOrder = next(
            (o for o in filled_sell_orders
             if _norm_exp(o.expiration) == pos_exp
             and str(o.symbol or "") == str(pos.symbol or "")
             and abs(float(o.strike or 0) - float(pos.strike or 0)) < 0.01
             and _norm_right(o.right) == pos_r),
            None,
        )
        
        if order is None:
            unmatched += 1
            sought = f"{pos.symbol}{pos_exp}{pos_r}{pos.strike}"
            db_formats = [f"{o.symbol}{_norm_exp(o.expiration)}{_norm_right(o.right)}{o.strike}" for o in filled_sell_orders if str(o.symbol) == str(pos.symbol)]
            logger.warning(f"synchronize_positions: no match for {sought} (TWS pos) — cannot monitor TP/SL. DB orders for {pos.symbol}: {db_formats[:5]}{'...' if len(db_formats) > 5 else ''}")
            try:
                _emit_log(f"No DB match for {sought} — TP/SL not monitored", "WARN", "position")
            except Exception:
                pass
            continue

        matched += 1

        # Use normalized expiry for contract (TWS format YYYYMMDD)
        exp_for_contract = pos_exp or _norm_exp(order.expiration)
        contract = client.get_options_contract(symbol=order.symbol, expiry=exp_for_contract, right=order.right, strike=order.strike)
        
        # subscribes to the contract to receive real-time market data
        client.subscribe(contract=contract)

        tick = client.get_options_data(symbol=order.symbol, expiry=exp_for_contract, right=order.right, strike=order.strike)

        order.active = True
        order.contract = contract
        tick.active_order = order
        
        order_mgr.add_entry_order(order=order, option_tick=tick)
        logger.info(f"Position synchronized: {order.option_symbol} — TP/SL monitoring active")

    logger.info(f"synchronize_positions: done — matched {matched}, unmatched {unmatched}")
    try:
        _emit_log(f"Position sync done: {matched} matched, {unmatched} unmatched (no TP/SL)", "INFO", "system")
    except Exception:
        pass

def synchronize_orders():
    """
    Synchronizes the orders in the order manager with the corresponding trades in the client's trades cache.
    For each order that is still active and has a matching trade, subscribes to the corresponding options contract
    to receive real-time market data and adds the order to the order manager's list of active orders.
    """
    logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    logger.info("synchronize orders")
    logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    
    # gets all orders from the order manager
    orders = order_mgr.get_orders()
    
    # loops through each order
    for order in orders:
        # checks if the order has a matching trade in the client's trades cache and is still active
        if order.id in client.trades_cache.keys() and order.order_side == 'BUY' and order.order_status not in ['inactive', 'cancelled', 'expired', 'filled']:
            
            # gets the options contract for the order
            contract = client.get_options_contract(symbol=order.symbol, expiry=order.expiration, right=order.right, strike=order.strike)
            
            # subscribes to the contract to receive real-time market data
            client.subscribe(contract=contract)
            
            # gets the options tick data for the order
            tick = client.get_options_data(symbol=order.symbol, expiry=order.expiration, right=order.right, strike=order.strike)
            
            # sets the order to active and assigns it the corresponding contract and tick data
            order.active = True
            order.contract = contract
            tick.active_order = order
            
            # adds the order to the order manager's list of active orders
            order_mgr.add_entry_order(order=order, option_tick=tick)
            
            # logs a message to indicate that the order has been successfully synchronized
            logger.info(f"Order synchronized: {order.option_symbol} {order}")

def account_pnl_monitor(account_id, ACCOUNT_TP, ACCOUNT_SL):
    while True:
        try:
            daily_pnl, realizedpnl = client.get_pnl(account_id)
            if daily_pnl >= ACCOUNT_TP:
                logger.info(f"Account profit target reached (${daily_pnl} >= ${ACCOUNT_TP}), closing all positions...")
                client.cancel_all_orders()
                check_and_close_all_open_positions()
                break
            elif daily_pnl <= -ACCOUNT_SL:
                logger.info(f"Account stop-loss hit (${daily_pnl} <= ${ACCOUNT_SL}), closing all positions...")
                client.cancel_all_orders()
                check_and_close_all_open_positions()
                break
            else:
                logger.info(f"Accoun Current: ${daily_pnl} SL: ${ACCOUNT_SL} TP: ${ACCOUNT_TP}...")
        except Exception as e:
            logger.error(f"PnL monitor error: {e}")
        time.sleep(1)  # check every 1 sec
    sys.exit(0)
    sys.exit(1)
    sys._exit(1)
    
# ===== ADD THIS BELOW OrderManager / helper functions =====

def monitor_positions_loop():
    """Monitor open positions for TP/SL; checks run in parallel for better throughput."""
    logger.info("Position monitor thread started")
    _emit_log("Position monitor thread started — checking TP/SL on open positions", "INFO", "position")
    last_heartbeat = time.time()
    HEARTBEAT_INTERVAL = 30.0  # Log every 30s to confirm thread is alive

    while not STOP_TRADING:
        try:
            if client is None:
                time.sleep(1.0)
                continue
            open_positions = list(client.get_all_positions())
            pos_count = len([p for p in open_positions if p and getattr(p, "position", 0) != 0])

            if pos_count > 0:
                if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                    n_entry = len(getattr(order_mgr, "entry_orders_cache", {}))
                    n_tick = len(getattr(order_mgr, "order_id_tick_lookup", {}))
                    logger.info(f"Position monitor: {pos_count} TWS pos | {n_entry} entry_orders, {n_tick} ticks. If no match, see 'Position NO MATCH' or 'matched but NO TICK' in logs.")
                    _emit_log(f"Monitor: {pos_count} pos, {n_entry} entries, {n_tick} ticks", "INFO", "position")
                    last_heartbeat = time.time()

                # Check positions in parallel (up to 16 workers for 10–20 positions)
                max_workers = min(16, max(1, pos_count))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(order_mgr.check_exit_conditions, pos): pos for pos in open_positions if pos and getattr(pos, "position", 0) != 0}
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as ex:
                            pos = futures[future]
                            logger.error(f"Position check error for {getattr(pos, 'symbol', '?')}: {ex}", exc_info=True)
        except Exception as e:
            logger.error(f"Position monitor error: {e}", exc_info=True)
            _emit_log(f"Position monitor error: {e}", "ERROR", "position")

        time.sleep(0.1)



def main_call(data):
    logger.info("Starting BOT")
    print("DATA is = {}\n\n\n".format(data))
    
    # ============ RE-READ CONFIG FILE TO GET LATEST VALUES ============
    global fileData
    file_data = globals().get("fileData") or {}
    try:
        config_path = os.path.join(os.getcwd(), "config.json")
        with open(config_path, "r", encoding="utf-8") as fopen:
            fileData = json.loads(fopen.read())
            file_data = fileData
            logger.info("Config file reloaded successfully")
    except Exception as e:
        logger.error(f"Failed to reload config file: {e}")
        pass
    # ==================================================================
    
    global IP, PORT, CLIENTID, SUB_ACCOUNT_ID, fetchValue, candleTime, stockListDict, stockList, dataInFile, EXPIRY, useAmount, MARKET_START_TIME, startTime, endTime, VWAP_ON_OFF, TRANSMIT, ORDER_EXPIRY_TIMER, USE_TIMER_IN_ORDER, CALL_DELTA_CHECK, PUT_DELTA_CHECK
    global VOLUME_CHECK, ATR_CHECKS, ACTIVE_VOLUME, MAX_CONTRACT_AMOUNT, ATR_VALUE, SHARE_VOLUME, BODY, perDayTrades, USE_DIFF_EXPIRY_INDEX, spy_qqq_tradeExpiry, PROFIT_INCREMENT, TRADE_COOLDOWN_SECONDS, EXPIRY, tradeExpiry_val
    global ADX_ON_OFF, ADX_THRESHOLD, RSI_DIVERGENCE_ON_OFF, VOLUME_DIVERGENCE_ON_OFF, LIQUIDITY_SWAP_ON_OFF, LIQUIDITY_CHECK_ON_OFF, LIQUIDITY_MIN_VOLUME, LIQUIDITY_MAX_SPREAD_PCT
    global trade_time_dict, signal_dict, profit_amount_day, loss_amount_day
    global starting_profit, starting_loss
    starting_profit = 0
    starting_loss = 0
    
    IP = data["IP"]
    PORT = data["PORT"]
    CLIENTID = data["CLIENTID"]
    SUB_ACCOUNT_ID = data["ACCOUNT_ID"]
    
    fetchValue = data["fetchValue"]
    candleTime = data["candleTime"]
    
    stockListDict = data["stockListToTrade"]
    stockList = list(stockListDict.keys())
    dataInFile = len(stockList)
    EXPIRY = data["expiryToTrade"]
    useAmount = data["stockData"]
    
    MARKET_START_TIME = data.get("marketStartTime", "09:30:00")
    # Prefer market_hours from config.json; fallback to scriptStartTime/scriptEndTime
    mh = data.get("market_hours") or {}
    startTime = mh.get("start") or data.get("scriptStartTime", "0935")
    endTime = mh.get("end") or data.get("scriptEndTime", "1545")
    
    VWAP_ON_OFF = "On"
    TRANSMIT = data["ORDER_TRANSMIT"]
    ORDER_EXPIRY_TIMER = data["ORDER_EXPIRY_TIMER"]   # ORDER EXPIRY TIMER - VALUE IN SECONDS
    USE_TIMER_IN_ORDER = data["USE_TIMER_IN_ORDER"]   # USE OF TIMER IN ORDER
    
    # Fall back to config file if keys missing (e.g. when config comes from UI without these)
    CALL_DELTA_CHECK = float(data.get("CALL_DELTA_CHECK", file_data.get("CALL_DELTA_CHECK", 0.35)))
    PUT_DELTA_CHECK = float(data.get("PUT_DELTA_CHECK", file_data.get("PUT_DELTA_CHECK", -0.35)))
    VOLUME_CHECK = int(data.get("VOLUME_CHECK", file_data.get("VOLUME_CHECK", 100)))
    ATR_CHECKS = data["ATR_CHECKS"]
    ACTIVE_VOLUME = data["ACTIVE_VOLUME"]
    MAX_CONTRACT_AMOUNT = data["MAX_CONTRACT_AMOUNT"]
    ATR_VALUE = data["ATR_VALUE"]
    SHARE_VOLUME = data["SHARE_VOLUME"]
    BODY = data["BODY"]
    loss_amount_day = float(data["loss_amount_day"])
    profit_amount_day = float(data["profit_amount_day"])

    ADX_ON_OFF = str(data.get("ADX_ON_OFF", fileData.get("ADX_ON_OFF", "OFF"))).upper()
    ADX_THRESHOLD = float(data.get("ADX_THRESHOLD", fileData.get("ADX_THRESHOLD", 25)))
    RSI_DIVERGENCE_ON_OFF = str(data.get("RSI_DIVERGENCE_ON_OFF", fileData.get("RSI_DIVERGENCE_ON_OFF", "OFF"))).upper()
    VOLUME_DIVERGENCE_ON_OFF = str(data.get("VOLUME_DIVERGENCE_ON_OFF", fileData.get("VOLUME_DIVERGENCE_ON_OFF", "OFF"))).upper()
    LIQUIDITY_SWAP_ON_OFF = str(data.get("LIQUIDITY_SWAP_ON_OFF", fileData.get("LIQUIDITY_SWAP_ON_OFF", "OFF"))).upper()
    LIQUIDITY_CHECK_ON_OFF = str(data.get("LIQUIDITY_CHECK_ON_OFF", fileData.get("LIQUIDITY_CHECK_ON_OFF", "OFF"))).upper()
    LIQUIDITY_MIN_VOLUME = int(data.get("LIQUIDITY_MIN_VOLUME", fileData.get("LIQUIDITY_MIN_VOLUME", 20)))
    LIQUIDITY_MAX_SPREAD_PCT = float(data.get("LIQUIDITY_MAX_SPREAD_PCT", fileData.get("LIQUIDITY_MAX_SPREAD_PCT", 15)))
    
    # 
    USE_DIFF_EXPIRY_INDEX = fileData["USE_DIFF_EXPIRY_INDEX"]
    SPY_QQQ_EXPIRY = fileData["SPY_QQQ_EXPIRY"]
    PROFIT_INCREMENT = fileData["profit_increment"]
    TRADE_COOLDOWN_SECONDS = fileData["distance_between_trade"]

    tradeExpiry_val = getExpiry(EXPIRY)
    spy_qqq_tradeExpiry = getExpiry(SPY_QQQ_EXPIRY)
    
    pnl_thread = None
    
    # Cooldown keys are now symbol+right+expiry; no pre-population at startup (first trade per combo allowed)
    trade_time_dict.clear()
    logger.info("trade_time_dict cleared (expiry-specific cooldown; no entries at startup)")
    
    for each in stockList:
        signal_dict[each] = {"last_signal":"", "current_signal":"", "last_trade_short_strike":"", "last_trade_buy_strike":"", "right":"", "conIdDetails_short":"", "conIdDetails_buy":""}
    logger.info("Signal Dict is = {}".format(signal_dict))
    
    print("PORT = {}".format(PORT))
    global client, client_thread, NY_TZ, event_queue, order_mgr, reconnect_time, dataStrike
    
    client_thread = None
    client = None
    event_queue = Queue()
    db = DAL()
    order_mgr = OrderManager(db=db)
    client = init_api_client(_event_queue=event_queue, _order_mgr = order_mgr)

    # Start the TWS client connection
    start_client(_client=client)

    #init_day_pnl(SUB_ACCOUNT_ID)
    pnlData, realized_start_PNL = client.get_pnl(SUB_ACCOUNT_ID)
    if realized_start_PNL < 0:
        starting_loss = realized_start_PNL
        profit_amount_day = profit_amount_day - starting_loss
        loss_amount_day = loss_amount_day + starting_loss
    elif realized_start_PNL > 0:
        starting_profit = realized_start_PNL
        profit_amount_day = profit_amount_day - starting_profit
        loss_amount_day = loss_amount_day + starting_profit
        #logger.info(f"First time log Pnl Value is {pnlData}")

    logger.info(f"First time log Pnl Value is {realized_start_PNL}")
    logger.info(f"Profit Day based on Existing pnl is {profit_amount_day} and Loss day is {loss_amount_day}")
    
    #from threading import Thread
    Thread(target=pnl_watchdog_thread, args=(SUB_ACCOUNT_ID, profit_amount_day, loss_amount_day), daemon=True).start()
    
    Thread(target=monitor_positions_loop, daemon=True).start()

    while True:
        if client is None:
            time.sleep(3.0)
            continue
            
        # Start the timer to check and close the program if needed
        timeCheckAndCloseProgram(SUB_ACCOUNT_ID, profit_amount_day, loss_amount_day)
        #timeCheckAndCloseProgram()
        
        # Initialize the order requests
        init_order_requests()

        # wait 3 seconds to get response of orders & positions request
        time.sleep(2.0)

        # Initialize the data feed
        init_data_feed()
        # Fetch all the strike expiries for all stocks
        dataStrike = fetch_all_strike_expiries()
        # synchronize positions to be monitored for closing (required for TP/SL on pre-existing TWS positions)
        synchronize_positions()
        # synchronize previous days open orders
        synchronize_orders()

        # Initialize the event processors if the TWS client is connected
        processors = init_start_event_processors()
        
        # set the flag to start putting market data in the event queue
        client.initialization_done = True
        
        """if pnl_thread is None or not pnl_thread.is_alive():
            pnl_thread = Thread(target=account_pnl_monitor, args=(SUB_ACCOUNT_ID, profit_amount_day, loss_amount_day), daemon=True)
            pnl_thread.start()"""

        try:
            for processor in processors:
                processor.join()
        except Exception as ex:
            pass

        if client.connection_closed == True:
            logger.error(f"TWS connection is closed, trying re-connect in {reconnect_time} seconds")

def start_trading(data):
    global _process
    if _process and _process.is_alive():
        print("BOT already running")
        return
    _process = Process(target=main_call, args=(data,))
    _process.start()

    
def stop_trading():
    global _process
    if _process and _process.is_alive():
        _process.terminate()
        _process.join()
        _process = None
        print("BOT process stopped")
    

"""if __name__ == "__main__":
    logger.info("Starting BOT")
    while True:
        client_thread = None
        client = None
        event_queue = Queue()
        db = DAL()
        order_mgr = OrderManager(db=db)
        client = init_api_client(_event_queue=event_queue, _order_mgr = order_mgr)
        
        if client is None:
            time.sleep(10.0)
            continue

        # Start the TWS client connection
        start_client(_client=client)

        # Start the timer to check and close the program if needed
        timeCheckAndCloseProgram()
        
        # Initialize the order requests
        init_order_requests()

        # wait 3 seconds to get response of orders & positions request
        time.sleep(3.0)

        # Initialize the data feed
        init_data_feed()
        # Fetch all the strike expiries for all stocks
        data = fetch_all_strike_expiries()
        # synchronize positions to be monitored for closing.
        synchronize_positions()
        # synchronize previous days open orders
        synchronize_orders()

        # Initialize the event processors if the TWS client is connected
        processors = init_start_event_processors()
        
        # set the flag to start putting market data in the event queue
        client.initialization_done = True
        
        try:
            for processor in processors:
                processor.join()
        except Exception as ex:
            pass

        if client.connection_closed == True:
            logger.error(f"TWS connection is closed, trying re-connect in {reconnect_time} seconds")"""