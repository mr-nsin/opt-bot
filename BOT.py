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

import logging
logging.getLogger().handlers.clear()


from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract, ComboLeg
from ibapi.ticktype import TickTypeEnum
from ibapi.order import *
from bisect import bisect_left
from logger import Loggers

# from datetime import date
import datetime
import pytz
# import MySQLdb
from datetime import datetime, timedelta
from threading import Thread
from queue import Queue, Empty
from common import OptionOrder, logger, Tick, getExpiry
from tws_api_client import TwsApiClient
from order_manager import OrderManager
from data_access import DAL

from multiprocessing import Process

_process = None

PROCESSORS_COUNT = 4

global client, client_thread, NY_TZ, event_queue, order_mgr, reconnect_time, dataStrike, signal_dict
global trade_time_dict, recent_trade_times, TRADE_COOLDOWN_SECONDS, tradeExpiry_val
global starting_profit, starting_loss
starting_profit = 0
starting_loss = 0

STOP_TRADING = False
DAILY_LIMIT_HIT = False
DAY_LOCKED = False
CLOSE_ALL_ORDERS = False
START_DAY_PNL = None


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

#def get_file_data()
filePath = os.getcwd() + "\\config.json"
with open("config.json", "r",  encoding="utf-8") as fopen:
    fileDataGet = fopen.read()
    ####### GET DATA FROM CONFIG FILE #######
    fileData = json.loads(fileDataGet)

# Connection Details - IP, PORT, ClientID
global IP, PORT, CLIENTID, SUB_ACCOUNT_ID, fetchValue, candleTime, stockListDict, stockList, dataInFile, EXPIRY, useAmount, MARKET_START_TIME, startTime, endTime, VWAP_ON_OFF, TRANSMIT, ORDER_EXPIRY_TIMER, USE_TIMER_IN_ORDER, CALL_DELTA_CHECK, PUT_DELTA_CHECK, VOLUME_CHECK, ATR_CHECKS
global ACTIVE_VOLUME, MAX_CONTRACT_AMOUNT, ATR_VALUE, SHARE_VOLUME, BODY, perDayTrades, USE_DIFF_EXPIRY_INDEX, spy_qqq_tradeExpiry, PROFIT_INCREMENT, TRADE_COOLDOWN_SECONDS, EXPIRY, tradeExpiry_val, profit_amount_day, loss_amount_day


# -- LICENSE SYSTEM --
LICENSE_FILE = "license.json"
LICENSE_KEY = "TraderNova_987_90_1"

def hard_exit():
    logger.error("HARD EXIT: Daily limit hit, terminating process")
    os.kill(os.getpid(), signal.SIGTERM)
    
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
        callback=_order_mgr.process_trade
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

def check_TRADE_COOLDOWN_SECONDS(stockName, rightMatch) -> bool:
    """
    Check if the time since the last trade exceeds the minimum distance between trades.

    Parameters:
    tick (Optional[Tick]): A Tick object containing the time of the last trade.

    Returns:
    bool: True if the time since the last trade exceeds the minimum distance between trades, False otherwise.
    """
    key = "{}_{}".format(stockName, rightMatch)
    if key in trade_time_dict.keys():
        last_trade_time = trade_time_dict["{}_{}".format(stockName, rightMatch)]
        time_since_last_trade = datetime.now() - last_trade_time
        logger.info(f"{stockName}: time_since_last_trade: {int(time_since_last_trade.total_seconds())}")
        return int(time_since_last_trade.total_seconds()) < TRADE_COOLDOWN_SECONDS
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
                stock_tick:Tick = None, closing_order: bool = False, is_sqare_off=False):
                    
    if DAY_LOCKED and CLOSE_ALL_ORDERS:
        logger.warning("Trading blocked: DAY LOCK active (PnL limit hit)")
        return "DayLocked"

    option_order = None

    logger.info("Checking for Order Place condition")

    logger.info("Order Data 1 ")
    
    open_order = order_mgr.get_entry_order(symbol=symbol)
    if open_order != None and open_order.active == True and open_order.right==right:
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
            active=True)

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
                        profitPrice=0, conIdDetails=None, legPrices=None, options_tick: Tick=None,
                        stock_tick: Tick=None):
                            
    if DAY_LOCKED and CLOSE_ALL_ORDERS:
        logger.warning("Trading blocked: DAY LOCK active (PnL limit hit)")
        return "DayLocked"

    if options_tick.locked == True:
        return "optionsTickLocked"

    options_tick.locked = True
    logger.info("Creating Orders")
    
    try:
        if options_tick.active_order != None and options_tick.active_order.order_status in ["Pending", "submitted"]:
            return "orderAlreadyPresent"
        
        key = f"{symbol}_{right}"
        last_trade_time = trade_time_dict.get(key)
    
        if last_trade_time:
            seconds_since = (datetime.now() - last_trade_time).total_seconds()
            if seconds_since < TRADE_COOLDOWN_SECONDS:
                logger.info(f"[{key}] Trade skipped. Cooldown active ({int(seconds_since)}s < {TRADE_COOLDOWN_SECONDS}s)")
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
                        stock_tick=stock_tick)
        return result
    except Exception as ex:
        logger.error(f"Error in placeAndVerifyOrder: {ex}", exc_info=True)
        return "error"
    finally:
        options_tick.locked = False

def getCallPutEngulfCheck(stock, limit=21, indicator="supertrend"):
    from datetime import datetime
    logger.info(f"Checking BEARISH OR BULLISH Engulf Data for stock = {stock}")

    # NOTE: commented by Saif
    # getCandlesData = getCurrentUndPrice(stock)

    getCandlesData = client.get_bars(stock=stock, barSize=candleTime, limit=limit)
    
    #############################################################################################################################################################################
    #############################################################################################################################################################################
    if indicator == "supertrend":
        if getCandlesData is None:
            return False, "None", stock, "notrade"
        
        if len(getCandlesData) < limit:
            logger.info(f"{stock} not enough candles.")
            logger.info(f"\n Received Candles for stocks= {stock} are = {getCandlesData}\n")
            return False, "None", stock, "notrade"
            
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
        
        if signal_dict[stock]['last_signal'] != signal_dict[stock]['current_signal']:
            logger.info("Signal Match for stock = {} and trade signal is = {}".format(stock, signal_dict[stock]['current_signal']))
            trade_value = "trade"

        right = "CALL"
        if signal_dict[stock]['current_signal'].lower() == "sell":
            right = "PUT"
        return True, right,  stock, "strongBuy"
    else:
        if getCandlesData is None:
            return False, "None", stock, "notrade"
        
        if len(getCandlesData) < 8:
            logger.info(f"{stock} not enough candles.")
            logger.info(f"\n Received Candles for stocks= {stock} are = {getCandlesData}\n")
            return False, "None", stock, "notrade"
        
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
        
        #AI_function() # match the pattern
        if candle_6_close >= candle_5_close and (candle_5_close >= candle_4_open or candle_5_close >= candle_4_high or candle_5_close >= candle_4_close) and candle_4_close <= candle_3_close and \
            candle_6_vol>= candle_5_vol*0.65 and candle_5_vol >=candle_4_vol*0.65:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 3 candles Pure Bullish Engulf Condition <<<CALL-AAAAA-StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "strongBuy"
        elif candle_6_close >= candle_5_close and (candle_5_close >= candle_4_open or candle_5_close >= candle_4_high or candle_5_close >= candle_4_close) and candle_4_close <= candle_3_close and \
            candle_5_vol >=candle_4_vol*0.65 and (candle_6_vol >=candle_5_vol*1.2 or candle_6_vol >=candle_4_vol*1.2):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 3 candles Pure Bullish Engulf Condition <<<CALL-AAAAA_HVY_VOL-StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "heavyBuy"
        elif (candle_6_close >= candle_5_open or candle_6_close >= candle_5_high) and (candle_5_close <= candle_4_close or (candle_5_high+candle_5_low)/2<= candle_4_close) and (candle_4_close <= candle_3_close or (candle_4_high+candle_4_low)/2<= candle_3_close) and \
            candle_6_vol >=candle_5_vol*0.65:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 4 candles Pure Bullish Engulf Condition <<<CALL-BBBBB-StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "strongBuy"
        elif (candle_6_close >= candle_5_open or candle_6_close >= candle_5_high) and (candle_5_close <= candle_4_close or (candle_5_high+candle_5_low)/2<= candle_4_close) and (candle_4_close <= candle_3_close or (candle_4_high+candle_4_low)/2<= candle_3_close) and \
            candle_6_vol >=candle_5_vol*1.25:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 4 candles Pure Bullish Engulf Condition <<<CALL-BBBBB_HVY_VOL_StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "heavyBuy"
        elif candle_6_close >= candle_5_close and candle_5_close>=candle_5_open and (candle_5_open-candle_5_low>=candle_5_close-candle_5_open*2) and \
            (candle_5_high-candle_5_open<=candle_5_close-candle_5_open) and \
            (candle_6_vol >=candle_5_vol*0.65 and candle_5_vol >=candle_4_vol*0.85):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 3 candles Pure Bullish Engulf Condition <<<CALL-CCCCC-StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "strongBuy"
        elif candle_6_close >= candle_5_close and candle_5_close>=candle_5_open and (candle_5_open-candle_5_low>=candle_5_close-candle_5_open*2) and \
            (candle_5_high-candle_5_open<=candle_5_close-candle_5_open) and \
            candle_5_vol >=candle_4_vol*1.05 and candle_6_vol >=candle_5_vol*0.55:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> 3 candles Pure Bullish Engulf Condition <<<CALL-CCCCC_HVY_VOL_StrongBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "heavyBuy"
        elif (candle_6_close >= candle_4_open or candle_6_close >= candle_4_high) and \
            candle_4_open >= candle_4_close and \
            (candle_5_vol >= candle_4_vol*0.65 and candle_6_vol >= candle_5_vol*0.55 and candle_6_vol >=candle_4_vol*0.5):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bullish Engulf Condition <<<CALL-DDDDD-MediumBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "normalBuy"
        elif (candle_6_close >= candle_4_open or candle_6_close >= candle_4_high) and \
            candle_4_open >= candle_4_close and \
            (candle_5_vol > candle_4_vol*0.55 and candle_6_vol >=candle_4_vol*0.52 and candle_6_vol >=candle_5_vol*0.55):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bullish Engulf Condition <<<CALL-DDDDD_HVY_VOL_MediumBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "mediumBuy"
        elif (candle_6_close >= candle_3_open or candle_6_close >= candle_3_high) and \
            candle_3_open >= candle_3_close and \
            (candle_4_open <= candle_3_open or candle_4_open <= candle_3_high) and (candle_5_open <= candle_3_open or candle_5_open <= candle_3_high) and \
            (candle_6_vol >= candle_3_vol*0.6 and candle_4_vol >= candle_3_vol*0.55 and candle_5_vol <= candle_3_vol*0.6):
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bullish Engulf Condition <<<CALL-EEEEE-MediumBUY>> meet. Return TRUE \
                        candle_4_close = {} and candle_4_high = {} candle_4_vol = {} and candle_3_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_4_close, candle_4_high, candle_4_vol, candle_3_vol, candle_6_close, candle_5_close, candle_3_open, candle_3_close, candle_4_open))
            return True, "CALL", stock, "mediumBuy"
        elif candle_6_close <= candle_4_open and candle_6_close <= candle_5_open and candle_5_high >= candle_4_high and candle_6_close <= candle_4_open and \
            candle_6_close <= candle_5_low and candle_6_vol >= candle_5_vol * 0.85 and candle_6_vol >= candle_4_vol * 0.8:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bearish Engulf Condition <<<PUT-AAAAA_MediumSELL>> meet. Return TRUE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return True, "PUT", stock, "mediumSell"
        elif candle_6_close <= candle_5_open and candle_6_open >= candle_5_close and candle_6_open >= candle_5_high and candle_6_close <= candle_5_low and \
            candle_6_vol >= candle_5_vol * 0.85 and candle_6_vol <= candle_5_vol * 1.25:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bearish Engulf Condition <<<PUT-BBBBB_StrongSELL>> meet. Return TRUE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return True, "PUT", stock, "strongSell"
        elif candle_6_close <= candle_5_open and candle_6_close <= candle_4_open and candle_6_close <= candle_3_open and \
            candle_6_vol >= candle_5_vol * 0.8:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bearish Engulf Condition <<<PUT-BBBBB_HVY_VOL_StrongSELL>> meet. Return TRUE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return True, "PUT", stock, "mediumSell"
        elif (candle_2_close <= candle_3_close or candle_2_close > candle_3_close) and \
                (candle_1_close >= candle_2_close or candle_1_close < candle_2_close) and \
                (candle_0_open >= candle_1_close or candle_0_open < candle_1_close) and \
                (candle_0_close < candle_1_low) and \
                candle_1_vol >= candle_0_vol * 0.8:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> AND Bearish Engulf Condition <<<PUT-AAAAA>> meet. Return TRUE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}.\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return True, "PUT", stock, "normalSell"
        else:
            logger.info("\n\n*********************************** <<<<Stock = {} >>>>> NO CONDITION MEET. Return FALSE \
                        candle_1_close = {} and candle_1_high = {} candle_1_vol = {} and candle_0_vol = {} \
                        4th Candle close is = {}, 3rd Candle Close is ={}, Current Open is = {}, Current Close is = {}, Previous OPEN is = {}. \
                        ********************************** STOCK CHECK END ********************************************\n\n".format(
                stock, candle_1_close, candle_1_high, candle_1_vol, candle_0_vol, candle_3_close, candle_2_close, candle_0_open, candle_0_close, candle_1_open))
            return False, "None", stock, "notrade"

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
    except:
        logger.info("Got except in getting ATR so running ATR code again in loop in except block")
        while True:
            atrValue = getATR(df)
            if len(atrValue) > 0:
                break
            else:
                continue

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
    
    dataDict = copy.deepcopy(strikesListDict)
    #logger.info("\n\nStrikes list for stock  {} is = \n{}\n".format(stock, dataDict))

    for eachStockStrike in dataDict:
        for key, value in eachStockStrike.items():
            if key.upper() == stock.upper():
                strikesList = eachStockStrike[stock]["Strike"]
                break

    strikesListNew = [float(each) for each in strikesList]
    
    logger.info("UNDERLYING PRICE IS = {}".format(tick.last))
    #logger.info("\n\nSTRIKES LIST NEW IS  = {}".format(strikesListNew))
    lowList, highList = get10StrikesNearUnderlying(strikesListNew, tick.last)

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
    if market_data:
        deltaVolData = [(market_data.delta, market_data.volume)]

    # If deltaVolData is empty, then add the string "NoDataPresent" to deltaVolData
    if not deltaVolData:
        deltaVolData.append("NoDataPresent")

    # Add the market data to deltaVolData
    deltaVolData.append(market_data)
    return deltaVolData

def checkAlgoAndTrade(Stock, Right, onlyAtrCheck="no"):
    if DAY_LOCKED and CLOSE_ALL_ORDERS:
        logger.warning("Trading blocked: DAY LOCK active (PnL limit hit)")
        return "DayLocked"

    isPreviousNeutralCandles = False
    timeCheck = timeCheckAndCloseProgram(SUB_ACCOUNT_ID, profit_amount_day, loss_amount_day)
    # When running as sidecar (Tauri app), do not exit process; just skip trading
    if timeCheck:
        logger.warning("Time/PnL check: skipping trade (day end or PnL limit); not exiting process")
        return (False, 0.0, ([0], [0], [0]))
    from datetime import datetime
    toTrade = False
    logger.info("Current NewYork Trade Time is = {}".format(
        datetime.today().astimezone(NY_TZ).strftime("%Y-%m-%d-%H-%M-%S")))
    
    getCandlesData = client.get_bars(stock=Stock, barSize=candleTime, limit=21)
    logger.info("candle Data is = {}".format(getCandlesData))
    if not getCandlesData or len(getCandlesData) < 2:
        logger.warning(f"No/insufficient candle data for {Stock}; skipping algo check (historical data may not be ready)")
        return (False, 0.0, ([0], [0], [0]))

    logger.info("\nVWAP_ON_OFF => {}\n".format(VWAP_ON_OFF))
    if onlyAtrCheck == "no":
        atrVal = float(getATRValue(Stock, getCandlesData))
        if VWAP_ON_OFF.lower()=="on":
            vwapVal = checkVWAPValue(Stock, Right, getCandlesData)
            logger.info("vwapVal Data Return for stock = {} is = {}".format(Stock, vwapVal))
            toTrade = vwapVal
        else:
            toTrade = True

        if atrVal >= ATR_CHECKS:
            logger.info("ATR_CHECKS Meet the ATR value")
            toTrade = toTrade and True
        else:
            logger.info("ATR_CHECKS Not Meet the ATR value")
            toTrade = toTrade and False

        # FOR SCLAP
        if candleTime == "3 mins":
            ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        elif candleTime == "1 min":
            ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        elif candleTime == "5 mins":
            ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        else:
            ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        # FOR INTRADAY

        return toTrade, atrVal, ema_S
    elif onlyAtrCheck == "yes":
        isPreviousNeutralCandles = False
        atrVal = getATRValue(Stock, getCandlesData)
        last2Candles = getCandlesData[::-1][1:3]
        logger.info("Last 2 candles data is = {}".format(last2Candles))

        candle_0 = last2Candles[0][1:]
        candle_1 = last2Candles[1][1:]

        candle_1_close = float(candle_1[3])
        candle_1_open = float(candle_1[0])
        if (round(candle_1_open, 3) - round(candle_1_close, 3)) == 0:
            logger.info("Previous Open = {} ad previous close is = {}".format(round(candle_1_open, 3), round(candle_1_close, 3)))
            isPreviousNeutralCandles = True
        
        # FOR SCLAP
        if candleTime == "3 mins":
            ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        elif candleTime == "1 min":
            ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        elif candleTime == "5 mins":
            ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))
        else:
            ema_S = indi.EMA_8_13_21(client.to_df(getCandlesData))

        return toTrade, atrVal, ema_S
    else:
        logger.info("\n\n\n\n\n\nWrong Data Given. So exiting Execution. Please Exit Orders Manually if Any placed by Program")
        sys.exit(0)
        sys.exit(0)

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

def checkConditionsAndTrade(dataValueSet, stock_tick):
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

    dataReturn = "None"
    tradeExpiry = tradeExpiry_val
    if "spy" in stockName.lower() or "qqq" in stockName.lower():
        tradeExpiry = spy_qqq_tradeExpiry
    
    position = client.get_open_position(symbol=stockName)
    logger.info(f"get_open_position: {stockName}: {position}")
    if position != None:
        pos_right = position.__str__().split(",")[::-1][1].split("=")[1]
        logger.info("Position = {} and pos_right = {}".format(position.position, pos_right))
        if position.position != 0 and pos_right.lower() == rightMatch[0].lower():
            logger.info(f"Position already Present for Stock = {stockName}")
            return "positionAlreadyPresent"
        else:
            logger.info(f"Position is not present with same Right for Stock = {stockName}")

    stockMapperDict = 0
    order = order_mgr.get_entry_order(stockName)
    if order != None and order.active == True:
        logger.info(f"Order Already Present for Stock = {stockName}, status: {order.order_status}")
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
                    # If the distance between trades check fails
                    if check_TRADE_COOLDOWN_SECONDS(stockName, rightMatch):
                        logger.info(f"{stockName} distance between trade check failed, TRADE_COOLDOWN_SECONDS {TRADE_COOLDOWN_SECONDS}")
                        continue
                    else:
                        tradeKey = '{}_{}'.format(stockName, rightMatch)
                        #logger.info("trade_time_dict = {}".format(trade_time_dict))
                        if len(trade_time_dict.keys()) != 0:
                            logger.info(f"{stockName} distance between trade check passed last_trade_time is {trade_time_dict[tradeKey]}, TRADE_COOLDOWN_SECONDS {TRADE_COOLDOWN_SECONDS}")

                    logger.info(f"DELTA DATA RETURN For {stockName}{tradeExpiry}{rightMatch}{eachStrike} IS = {deltaVolDataReturn}")
                    if deltaVolDataReturn == "NoDataPresent":
                        logger.info("No Trade Happend For Stocks as Table Data is not present")
                        continue
                    elif len(deltaVolDataReturn) == 2:
                        logger.info(f"Checking Delta and Volume Match Condition for stock ={stockName} and strike is ={eachStrike}")
                        deltaValue = deltaVolDataReturn[0]
                        volumes = deltaVolDataReturn[1]
                        logger.info(f"Recevied delta value is = {deltaValue} and Volume is = {volumes} from DB for stock = {stockName}")

                        if deltaValue >= CALL_DELTA_CHECK and volumes >= VOLUME_CHECK:
                            # TODO: MUST REMOVE FOLLOWING CODE
                            # NOTE: TO test order placement temporary code, 
                            # -----------
                            #getCandlesData = client.get_bars(stock=stockName, barSize=candleTime, limit="day")
                            #atrValue = float(getATRValue(stockName, getCandlesData))
                            #toTrade = True
                            # -----------
                            toTrade, atrValue, ema_S = checkAlgoAndTrade(stockName, "CALL")                            
                            logger.info("\n EMA_S Values for 8D, 13D, and 21D are = {}\n".format(ema_S))

                            ema_S_8 = ema_S[0][len(ema_S[0])-1]
                            ema_S_13 = ema_S[1][len(ema_S[1])-1]
                            ema_S_21 = ema_S[2][len(ema_S[2])-1]
                            
                            if toTrade and ("heavy" in signalStrength.lower() or "strong" in signalStrength.lower()):
                                ###### SCLAP HIT
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="CALL",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick)
                                
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
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="CALL",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick)
                                
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
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="CALL",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick)
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
                    # If the distance between trades check fails
                    if check_TRADE_COOLDOWN_SECONDS(stockName, rightMatch):
                        logger.info(f"{stockName} distance between trade check failed, TRADE_COOLDOWN_SECONDS {TRADE_COOLDOWN_SECONDS}")
                        continue
                    else:
                        tradeKey = '{}_{}'.format(stockName, rightMatch)
                        #logger.info("trade_time_dict = {}".format(trade_time_dict))
                        if len(trade_time_dict.keys()) != 0:
                            logger.info(f"{stockName} distance between trade check passed last_trade_time is {trade_time_dict[tradeKey]}, TRADE_COOLDOWN_SECONDS {TRADE_COOLDOWN_SECONDS}")
                    
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
                            
                            toTrade, atrValue, ema_S  = checkAlgoAndTrade(stockName, "PUT")
                            logger.info("\n EMA_S Values for 8D, 13D, and 21D are = {}\n".format(ema_S))

                            ema_S_8 = ema_S[0][len(ema_S[0])-1]
                            ema_S_13 = ema_S[1][len(ema_S[1])-1]
                            ema_S_21 = ema_S[2][len(ema_S[2])-1]
                            
                            # SCLAP HIT
                            if toTrade and ("heavy" in signalStrength.lower() or "strong" in signalStrength.lower()):
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="PUT",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick)
                                if orderData == "orderPlaced":
                                    dataReturn = "orderPlaced"
                                    break
                                else:
                                    logger.info(f"Order Not Placed for stock={stockName}, Right={rightMatch}, Strike={eachStrike}, Expiry={tradeExpiry}\nBecause ={orderData}")
                                    dataReturn = orderData
                                    continue
                            elif toTrade and ((ema_S_21>=ema_S_13 and ema_S_13<=ema_S_8) or ema_S_13>=ema_S_8 ):
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="PUT",
                                                        expiry=tradeExpiry,
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick)
                                if orderData == "orderPlaced":
                                    dataReturn = "orderPlaced"
                                    break
                                else:
                                    logger.info(f"Order Not Placed for stock={stockName}, Right={rightMatch}, Strike={eachStrike}, Expiry={tradeExpiry}\nBecause ={orderData}")
                                    dataReturn = orderData
                                    continue
                            elif toTrade and ((ema_S_21>=ema_S_13 and ema_S_13>=ema_S_8) or ema_S_21-ema_S_13 >= atrValue*0.77):
                                ###### INTRADAY HIT
                                orderData = takeTrade(atrVale=atrValue, 
                                                        stock_symbol=stockName,
                                                        strike=eachStrike, 
                                                        right="PUT",
                                                        expiry=tradeExpiry, 
                                                        options_tick=options_tick, 
                                                        stock_tick=stock_tick)
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
    logger.info(f"Stock {dataValueSet[0][2].upper()} checkConditionsAndTrade - end")
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
    logger.info(f"Checking timeCheckAndCloseProgram")
    tradeMarketTime = False
    pnlData, realizedPNL = client.get_pnl(SUB_ACCOUNT_ID)
    logger.info(f"Account {SUB_ACCOUNT_ID} PNL is {pnlData}")
    try:
        marketTime = datetime.now().astimezone(NY_TZ).strftime("%H-%M")
        if marketTime.replace("-", "") > endTime.toString("HHmm"):
            logger.info(f"Market Time is ={marketTime} > {endTime}.So Closing All Placed Orders if Any Or Closing Execution if no Orders Present")
            tradeMarketTime = True
            logger.info("Cancel All Placed Order/s And Square Off all existing Bought Quantities if any at MKT Price")
            cancel_all_orders()
            getAndBuyAfterMarketEnd()
        elif pnlData >= profit_amount_day or pnlData <= loss_amount_day:
            tradeMarketTime = True
            logger.info(f"Day PNL Target HIT. Either {pnlData} is Greater than Profit Target {profit_amount_day} or Less than Loss Target {loss_amount_day}")
            logger.info("Cancel All Placed Order/s And Square Off all existing Bought Quantities if any at MKT Price as Daily Profit/StopLoss Target HIT.")
            cancel_all_orders()
            getAndBuyAfterMarketEnd()
        else:
            logger.info(f"timeCheckAndCloseProgram:=>> Market Time is = {marketTime} <={endTime}. Keep Going Trade")
            logger.info(f"Accoun Current: ${pnlData} SL: -${loss_amount_day} TP: ${profit_amount_day}...")
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
    

def getAndBuyAfterMarketEnd():
    try:
        OPEN_POSITION = client.get_all_positions()
        logger.info(f"Current Open Positions are {OPEN_POSITION}\nClosing all of them")

        if len(OPEN_POSITION) == 0:
            logger.info("No Options Positions is present in Portfolio, so exiting the program now only")
            return

        for ePos in OPEN_POSITION:
            totalQty = int(abs(ePos.position))

            if totalQty > 0:
                action = "SELL"
                
                options_tick = client.get_options_data(
                    symbol=ePos.symbol,
                    expiry=ePos.expiry,
                    right=ePos.right,
                    strike=ePos.strike
                )
                

                allSquareOffOrderId = placeOrder(symbol=ePos.symbol,
                                                    expiry=ePos.expiry, 
                                                    strike=ePos.strike,
                                                    right=ePos.right, 
                                                    action=action, 
                                                    totalQuantity=totalQty,
                                                    orderType="MKT",
                                                    options_tick=options_tick,
                                                    closing_order=True,
                                                    is_sqare_off=True)
                logger.info(f"Square off order placed: {allSquareOffOrderId}")
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
    


def takeTrade(atrVale:float, stock_symbol: str, expiry: str, strike: float, right: str, options_tick: Tick, stock_tick: Tick):
    if DAY_LOCKED and CLOSE_ALL_ORDERS:
        logger.warning("Trading blocked: DAY LOCK active (PnL limit hit)")
        return "DayLocked"

    logger.info(f"All Algo's conditions meet, now doing a check for Options Price must be ${MAX_CONTRACT_AMOUNT} or low")
    # tick = client.get_options_data(symbol=takeTick, expiry=takeExpiry, right=takeRight, strike=takeStrike)
    
    trade_key = "{}_{}".format(stock_symbol, right)

    if options_tick.last == -1:
        return "priceConditonNotMatched"

    bidPrice = options_tick.bid
    askPrice = options_tick.ask
    lastPrice = options_tick.last
    activeVol = options_tick.volume
    
    midPrice = (bidPrice + askPrice)/2
    spreadGap = askPrice - bidPrice
    
    if spreadGap >=0.12:
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
    logger.info(f"""
    ═══════════════════════════════════════════════════════
    PROFIT/LOSS CALCULATION for {stock_symbol}
    ═══════════════════════════════════════════════════════
    Entry Price: ${tradePrice:.2f}
    ATR Value: ${atrVale:.4f}
    Market Time: {marketTime}
    Time to Expiry: {TimeDecayDiffVal} days
    Is SPY/QQQ: {"spy" in stock_symbol.lower() or "qqq" in stock_symbol.lower()}
    """)

    if atrVale <= 0.01:
        profitPrice = round(tradePrice + 0.02, 2)
        auxPrice = round(tradePrice - 0.01, 2)
        logger.info(f"Low ATR case: Profit=${profitPrice:.2f}, StopLoss=${auxPrice:.2f}")
    else:
        atrVale = atrVale * ATR_VALUE

        # ProfitPrice
        profitPrice = round(tradePrice + float(atrVale), 2)
        timeDiffMultiplyVal = 0.13
        TimeDecayDiffVal = timeDecayDiff(tradeExpiry_val)
        
        """if tradePrice<=0.2 and TimeDecayDiffVal == 0 and marketTime >= "1301" and marketTime <= "1401":
            profitPrice = round(tradePrice + float(0.05), 2)
            auxPrice = round(tradePrice - float(tradPrice*0.04), 2)
            if auxPrice <= 0.0:
                auxPrice = 0.01
        elif tradePrice<=0.2 and TimeDecayDiffVal == 0 and marketTime >= "1201":
            profitPrice = round(tradePrice + float(0.04), 2)
            auxPrice = round(tradePrice - float(tradPrice*0.03), 2)
            if auxPrice <= 0.0:
                auxPrice = 0.01
        elif tradePrice>=0.2 and tradePrice<=0.4 and TimeDecayDiffVal == 0 and marketTime < "1301":
            profitPrice = round(tradePrice + float(tradPrice*0.15), 2)
            auxPrice = round(tradePrice - float(tradPrice*0.14), 2)
        elif tradePrice>=0.2 and tradePrice<=0.4 and TimeDecayDiffVal == 0 and marketTime >= "1301":
            profitPrice = round(tradePrice + float(tradPrice*0.13), 2)
            auxPrice = round(tradePrice - float(tradPrice*0.12), 2)
        elif atrVale < 0.235:
            if marketTime >= "1201":
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.7
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.65
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.6
                profitPrice = round(tradePrice + float(atrVale * 0.65), 2)
            elif marketTime < "1201":
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.75
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.68
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.59
                profitPrice = round(tradePrice + float(atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 0.235 and atrVale < 0.485:
            if marketTime >= "1201":
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.7
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.64
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.56
                profitPrice = round(tradePrice + float(atrVale * timeDiffMultiplyVal), 2)
            elif marketTime < "1201":
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.85
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.68
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.55
                profitPrice = round(tradePrice + float(atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 0.485 and atrVale < 1.05:
            if marketTime >= "1201":
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.48
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.42
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.35
                profitPrice = round(tradePrice + float(atrVale * timeDiffMultiplyVal), 2)
            elif marketTime < "1200":
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.5
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.44
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.35
                profitPrice = round(tradePrice + float(atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 1.05:
            if marketTime >= "1201":
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.35
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.31
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.25
                profitPrice = round(tradePrice + float(atrVale * timeDiffMultiplyVal), 2)
            elif marketTime < "1200":
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.41
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.36
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.3
                profitPrice = round(tradePrice + float(atrVale * timeDiffMultiplyVal), 2)

        # auxPrice
        auxPrice = round(tradePrice - float(atrVale), 2)
        if atrVale < 0.235:
            if TimeDecayDiffVal >=4:
                timeDiffMultiplyVal = 0.8
            elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                 timeDiffMultiplyVal = 0.75
            elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                timeDiffMultiplyVal = 0.7
            auxPrice = round(tradePrice - float(atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 0.235 and atrVale < 0.485:
            if TimeDecayDiffVal >=4:
                timeDiffMultiplyVal = 0.75
            elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                 timeDiffMultiplyVal = 0.69
            elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                timeDiffMultiplyVal = 0.6
            auxPrice = round(tradePrice - float(atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 0.485 and atrVale < 1.05:
            if TimeDecayDiffVal >=4:
                timeDiffMultiplyVal = 0.55
            elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                 timeDiffMultiplyVal = 0.49
            elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                timeDiffMultiplyVal = 0.4
        elif atrVale >= 1.05:
            if TimeDecayDiffVal >=4:
                timeDiffMultiplyVal = 0.4
            elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                 timeDiffMultiplyVal = 0.33
            elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                timeDiffMultiplyVal = 0.25
            auxPrice = round(tradePrice - float(atrVale * timeDiffMultiplyVal), 2)
            
        if TimeDecayDiffVal == 0:
            if marketTime <= "1130":
                if tradePrice <= 0.1:
                    return "0dtepricebelow10cent"
                elif tradePrice <= 0.2:
                    profitPrice = round(tradePrice - float(tradePrice * 0.2), 2)
                    auxPrice = round(tradePrice - float(tradePrice * 0.2), 2)
                elif tradePrice <= 0.3 and tradePrice > 0.2:
                    profitPrice = round(tradePrice - float(tradePrice * 22)/100, 2)
                    auxPrice = round(tradePrice - float(tradePrice * 25)/100, 2)
                elif tradePrice > 0.3 and tradePrice <= 0.75:
                    profitPrice = round(tradePrice - float(tradePrice * 19)/100, 2)
                    auxPrice = round(tradePrice - float(tradePrice * 21)/100, 2)
                elif tradePrice > 0.75 and tradePrice <= 1.5:
                    profitPrice = round(tradePrice - float(tradePrice * 14)/100, 2)
                    auxPrice = round(tradePrice - float(tradePrice * 16)/100, 2)
                elif tradePrice > 1.5 and tradePrice <= 3.5:
                    profitPrice = round(tradePrice - float(tradePrice * 10)/100, 2)
                    auxPrice = round(tradePrice - float(tradePrice * 12)/100, 2)
            elif marketTime > "1130" and marketTime <= "1300":
                if tradePrice <= 0.1:
                    return "0dtepricebelow10cent"
                elif tradePrice <= 0.2:
                    profitPrice = round(tradePrice - float(tradePrice * 0.2), 2)
                    auxPrice = round(tradePrice - float(tradePrice * 0.2), 2)
                elif tradePrice <= 0.3 and tradePrice > 0.2:
                    profitPrice = round(tradePrice - float(tradePrice * 17)/100, 2)
                    auxPrice = round(tradePrice - float(tradePrice * 23)/100, 2)
                elif tradePrice > 0.3 and tradePrice <= 0.75:
                    profitPrice = round(tradePrice - float(tradePrice * 14)/100, 2)
                    auxPrice = round(tradePrice - float(tradePrice * 19)/100, 2)
                elif tradePrice > 0.75 and tradePrice <= 1.5:
                    profitPrice = round(tradePrice - float(tradePrice * 10)/100, 2)
                    auxPrice = round(tradePrice - float(tradePrice * 14)/100, 2)
                elif tradePrice > 1.5 and tradePrice <= 3.5:
                    profitPrice = round(tradePrice - float(tradePrice * 7)/100, 2)
                    auxPrice = round(tradePrice - float(tradePrice * 10)/100, 2)
            elif marketTime >= "1445":
                return "0dte2ndhalfnotrade"""
                
        if tradePrice<=0.2 and TimeDecayDiffVal == 0 and marketTimeInt >= 1301 and marketTimeInt <= 1401:
            profitPrice = round(tradePrice + 0.05, 2)
            auxPrice = round(tradePrice - (tradePrice*0.04), 2)
            if auxPrice <= 0.0:
                auxPrice = 0.01
        elif tradePrice<=0.2 and TimeDecayDiffVal == 0 and marketTimeInt >= 1201:
            profitPrice = round(tradePrice + 0.04, 2)
            auxPrice = round(tradePrice - (tradePrice*0.03), 2)
            if auxPrice <= 0.0:
                auxPrice = 0.01
        elif tradePrice>=0.2 and tradePrice<=0.4 and TimeDecayDiffVal == 0 and marketTimeInt < 1301:
            profitPrice = round(tradePrice + (tradePrice*0.15), 2)
            auxPrice = round(tradePrice - (tradePrice*0.14), 2)
        elif tradePrice>=0.2 and tradePrice<=0.4 and TimeDecayDiffVal == 0 and marketTimeInt >= 1301:
            profitPrice = round(tradePrice + (tradePrice*0.13), 2)
            auxPrice = round(tradePrice - (tradePrice*0.12), 2)
        elif atrVale < 0.235:
            if marketTimeInt >= 1201:
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.7
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.65
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.6
                profitPrice = round(tradePrice + (atrVale * 0.65), 2)
            elif marketTimeInt < 1201:
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.75
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.68
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.59
                profitPrice = round(tradePrice + (atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 0.235 and atrVale < 0.485:
            if marketTimeInt >= 1201:
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.7
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.64
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.56
                profitPrice = round(tradePrice + (atrVale * timeDiffMultiplyVal), 2)
            elif marketTimeInt < 1201:
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.85
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.68
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.55
                profitPrice = round(tradePrice + (atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 0.485 and atrVale < 1.05:
            if marketTimeInt >= 1201:
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.48
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.42
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.35
                profitPrice = round(tradePrice + (atrVale * timeDiffMultiplyVal), 2)
            elif marketTimeInt < 1200:
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.5
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.44
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.35
                profitPrice = round(tradePrice + (atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 1.05:
            if marketTimeInt >= 1201:
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.35
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.31
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.25
                profitPrice = round(tradePrice + (atrVale * timeDiffMultiplyVal), 2)
            elif marketTimeInt < 1200:
                if TimeDecayDiffVal >=4:
                    timeDiffMultiplyVal = 0.41
                elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                    timeDiffMultiplyVal = 0.36
                elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                    timeDiffMultiplyVal = 0.3
                profitPrice = round(tradePrice + (atrVale * timeDiffMultiplyVal), 2)

        # ========== STOPLOSS CALCULATION ==========
        # (Your existing logic)
        auxPrice = round(tradePrice - atrVale, 2)
        if atrVale < 0.235:
            if TimeDecayDiffVal >=4:
                timeDiffMultiplyVal = 0.8
            elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                 timeDiffMultiplyVal = 0.75
            elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                timeDiffMultiplyVal = 0.7
            auxPrice = round(tradePrice - (atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 0.235 and atrVale < 0.485:
            if TimeDecayDiffVal >=4:
                timeDiffMultiplyVal = 0.75
            elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                 timeDiffMultiplyVal = 0.69
            elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                timeDiffMultiplyVal = 0.6
            auxPrice = round(tradePrice - (atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 0.485 and atrVale < 1.05:
            if TimeDecayDiffVal >=4:
                timeDiffMultiplyVal = 0.55
            elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                 timeDiffMultiplyVal = 0.49
            elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                timeDiffMultiplyVal = 0.4
            auxPrice = round(tradePrice - (atrVale * timeDiffMultiplyVal), 2)
        elif atrVale >= 1.05:
            if TimeDecayDiffVal >=4:
                timeDiffMultiplyVal = 0.4
            elif TimeDecayDiffVal < 4 and TimeDecayDiffVal >=2:
                 timeDiffMultiplyVal = 0.33
            elif TimeDecayDiffVal < 2 and TimeDecayDiffVal >0:
                timeDiffMultiplyVal = 0.25
            auxPrice = round(tradePrice - (atrVale * timeDiffMultiplyVal), 2)
            
        # Special 0DTE handling
        if TimeDecayDiffVal == 0:
            if marketTimeInt <= 1130:
                if tradePrice <= 0.1:
                    return "0dtepricebelow10cent"
                elif tradePrice <= 0.2:
                    profitPrice = round(tradePrice + (tradePrice * 0.2), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.2), 2)
                elif tradePrice <= 0.3 and tradePrice > 0.2:
                    profitPrice = round(tradePrice + (tradePrice * 0.22), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.25), 2)
                elif tradePrice > 0.3 and tradePrice <= 0.75:
                    profitPrice = round(tradePrice + (tradePrice * 0.19), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.21), 2)
                elif tradePrice > 0.75 and tradePrice <= 1.5:
                    profitPrice = round(tradePrice + (tradePrice * 0.14), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.16), 2)
                elif tradePrice > 1.5 and tradePrice <= 3.5:
                    profitPrice = round(tradePrice + (tradePrice * 0.10), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.12), 2)
            elif marketTimeInt > 1130 and marketTimeInt <= 1300:
                if tradePrice <= 0.1:
                    return "0dtepricebelow10cent"
                elif tradePrice <= 0.2:
                    profitPrice = round(tradePrice + (tradePrice * 0.2), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.2), 2)
                elif tradePrice <= 0.3 and tradePrice > 0.2:
                    profitPrice = round(tradePrice + (tradePrice * 0.17), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.23), 2)
                elif tradePrice > 0.3 and tradePrice <= 0.75:
                    profitPrice = round(tradePrice + (tradePrice * 0.14), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.19), 2)
                elif tradePrice > 0.75 and tradePrice <= 1.5:
                    profitPrice = round(tradePrice + (tradePrice * 0.10), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.14), 2)
                elif tradePrice > 1.5 and tradePrice <= 3.5:
                    profitPrice = round(tradePrice + (tradePrice * 0.07), 2)
                    auxPrice = round(tradePrice - (tradePrice * 0.10), 2)
            elif marketTimeInt >= 1445:
                return "0dte2ndhalfnotrade"

    # Ensure stoploss is never negative
    if auxPrice < 0.01:
        auxPrice = 0.01
        
    # ============ LOG FINAL CALCULATED VALUES ============
    profit_pct = ((profitPrice - tradePrice) / tradePrice * 100) if tradePrice > 0 else 0
    loss_pct = ((tradePrice - auxPrice) / tradePrice * 100) if tradePrice > 0 else 0
    
    logger.info(f"""
    ═══════════════════════════════════════════════════════
    FINAL PROFIT/LOSS TARGETS for {stock_symbol}
    ═══════════════════════════════════════════════════════
    Entry Price:     ${tradePrice:.2f}
    Take Profit:     ${profitPrice:.2f}  (+{profit_pct:.1f}%)
    Stop Loss:       ${auxPrice:.2f}     (-{loss_pct:.1f}%)
    Profit Increment: ${PROFIT_INCREMENT:.2f}
    Risk/Reward:     1:{(profitPrice-tradePrice)/(tradePrice-auxPrice):.2f}
    ═══════════════════════════════════════════════════════
    """)

    logger.info(f"\n\nCurrent Options Price is = {lastPrice} And Current Active Volume = {activeVol}")

    if (lastPrice * 100) <= MAX_CONTRACT_AMOUNT:
        totalQty = int(useAmount[stock_symbol]["amount"] / (tradePrice * 100))
        if totalQty==0:
            totalQty = 1

        #logger.info(f"Amount to Use is = {useAmount} and Quantities to trade is = useAmount/tradPrice = {totalQty}")
        logger.info(f"Amount to Use is = {useAmount[stock_symbol]['amount']} and Quantities to trade = {totalQty}")

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
                            stock_tick=stock_tick)

        logger.info("\nupdating new time for last trade\n")
        trade_key = "{}_{}".format(stock_symbol, right)
        trade_time_dict.update({trade_key:datetime.now()})
        
        #options_tick.last_trade_time = datetime.now()
        logger.info(f"currentOrderId is = {currentOrderId}")
        return "orderPlaced"
    else:
        logger.info(f"Öptions Price is Above ${MAX_CONTRACT_AMOUNT} so going or next check")
        return "priceConditonNotMatched"


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
            return

        # STK = stocks, FUT = futures (e.g. MNQU5, NQU5), OPT = options (calls/puts on STK underlyings).
        stock_list_to_trade = globals().get("stock_list_to_trade", None) or {}
        logger.info(f"Subscribing to underlyings: {stockList}. Then options (OPT) on stocks for strategy.")

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
        time.sleep(3.0)

        # Build strikes_map only for stocks (options chain); futures have no options in this flow
        stock_only_list = [c.symbol for c in stock_contracts if getattr(c, "secType", "") == "STK"]
        strikes_map = get_strikes_map(stock_list=stock_only_list) if stock_only_list else {}
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
            ls, hs = get10StrikesNearUnderlying(strikeList=strikes, undPrc=market_data.last, range_limit=4)
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

        time.sleep(10)
        for contract in options_contracts:
            client.subscribe(contract=contract)
    except Exception as ex:
        logger.error(f"init_data_feed: {ex}")


def fetch_all_strike_expiries():
    logger.info(
        f"Fetching All strikes/Expiries List for all stocks. = {stockList}"
    )
    with open("expiryStrike.json", "r",  encoding="utf-8") as fp:
        return [json.loads(fp.read())]

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
    logger.info(f"Starting event processor #{count + 1}")
    tries = 0
    keep_running = True
    while keep_running:
        try:
            # Get the event data from the queue
            event_data = event_queue.get(block=False, timeout=0.20)
            tick: Tick = event_data["tick"]
            
            # If the security type is 'OPT' and an active order exists
            if tick.contract.secType == "OPT" and tick.active_order is not None:
                order_mgr.check_and_close_position(tick=tick)
            elif tick.contract.secType == "STK":
                # Get the result of the call/put engulf check
                dataEngulf = getCallPutEngulfCheck(tick.contract.symbol)
                logger.info(f"\n dataEngulf = {dataEngulf}\n")
                if dataEngulf[0]:
                    result = checkConditionsAndTrade((dataEngulf, dataStrike), tick)
                    logger.info(f"checkConditionsAndTrade: {result}")
            
            # Mark the event as processed
            event_queue.task_done()
        except Empty:
            # If TWS is disconnected
            if client is not None and not client.isConnected():
                logger.error("TWS is disconnected")
                logger.info("trying Reconnect")
                client.try_reconnect()
                #if not client.isConnected():
                #return "TWS API connection error"
                time.sleep(5.0)
                if client.connection_closed == True:
                    keep_running = False
        except Exception as ex:
            # Log the error
            logger.error("Error occurred:", exc_info=True)


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
        try:
            pnl, realizedPNL = client.get_pnl(account_id)

            if pnl >= day_profit_limit or pnl <= day_loss_limit:
                logger.error(
                    f" DAILY LIMIT HIT  PnL={pnl} "
                    f"Limits=({day_profit_limit}, {day_loss_limit})")

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
    # logs a message to indicate the function has started
    logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ synchronize positions from DB CHECK $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    
    # gets all positions held by the client
    positions = client.get_all_positions()
    
    # gets all filled BUY orders from the order manager
    filled_sell_orders = order_mgr.get_filled_orders(order_side='BUY')
    
    # loops through each position
    for pos in positions:
        # skips positions with zero quantity
        if pos.position == 0:
            continue
        
        # converts the 'right' attribute of the position to a human-readable format
        right = pos.right
        if right == "C":
            right = "CALL"
        elif right == "P":
            right = "PUT"
        
        # constructs the option symbol from the position information
        option_symbol = f"{pos.symbol}{pos.expiry}{right}{pos.strike}"
        
        # finds the matching filled BUY order for the position
        order : OptionOrder = next((o for o in filled_sell_orders if o.option_symbol == option_symbol), None,)
        
        # if no matching order is found, logs an error message and continues to the next position
        if order is None:
            logger.error(f"{option_symbol} position matching order not found")
            continue
        
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
        
        # logs a message to indicate that the position has been successfully synchronized
        logger.info(f"Position synchronized: {order.option_symbol} {order}")

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
    logger.info("Position monitor thread started")
    while not STOP_TRADING:
        try:
            open_positions = client.get_all_positions()
            for pos in open_positions:
                order_mgr.check_exit_conditions(pos)
        except Exception as e:
            logger.error(f"Position monitor error: {e}")
        time.sleep(0.1)



def main_call(data):
    logger.info("Starting BOT")
    print("DATA is = {}\n\n\n".format(data))
    
    # ============ RE-READ CONFIG FILE TO GET LATEST VALUES ============
    # This ensures we get the updated values from config.json
    try:
        config_path = os.path.join(os.getcwd(), "config.json")
        with open(config_path, "r", encoding="utf-8") as fopen:
            fileData = json.loads(fopen.read())
            logger.info("Config file reloaded successfully")
    except Exception as e:
        logger.error(f"Failed to reload config file: {e}")
        # Fall back to the module-level fileData if reload fails
        pass
    # ==================================================================
    
    global IP, PORT, CLIENTID, SUB_ACCOUNT_ID, fetchValue, candleTime, stockListDict, stockList, dataInFile, EXPIRY, useAmount, MARKET_START_TIME, startTime, endTime, VWAP_ON_OFF, TRANSMIT, ORDER_EXPIRY_TIMER, USE_TIMER_IN_ORDER, CALL_DELTA_CHECK, PUT_DELTA_CHECK
    global VOLUME_CHECK, ATR_CHECKS, ACTIVE_VOLUME, MAX_CONTRACT_AMOUNT, ATR_VALUE, SHARE_VOLUME, BODY, perDayTrades, USE_DIFF_EXPIRY_INDEX, spy_qqq_tradeExpiry, PROFIT_INCREMENT, TRADE_COOLDOWN_SECONDS, EXPIRY, tradeExpiry_val
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
    
    MARKET_START_TIME = data["marketStartTime"]
    startTime = data["scriptStartTime"]
    endTime = data["scriptEndTime"]
    
    VWAP_ON_OFF = "On"
    TRANSMIT = data["ORDER_TRANSMIT"]
    ORDER_EXPIRY_TIMER = data["ORDER_EXPIRY_TIMER"]   # ORDER EXPIRY TIMER - VALUE IN SECONDS
    USE_TIMER_IN_ORDER = data["USE_TIMER_IN_ORDER"]   # USE OF TIMER IN ORDER
    
    CALL_DELTA_CHECK = float(data["CALL_DELTA_CHECK"])
    PUT_DELTA_CHECK = data["PUT_DELTA_CHECK"]
    VOLUME_CHECK = data["VOLUME_CHECK"]
    ATR_CHECKS = data["ATR_CHECKS"]
    ACTIVE_VOLUME = data["ACTIVE_VOLUME"]
    MAX_CONTRACT_AMOUNT = data["MAX_CONTRACT_AMOUNT"]
    ATR_VALUE = data["ATR_VALUE"]
    SHARE_VOLUME = data["SHARE_VOLUME"]
    BODY = data["BODY"]
    loss_amount_day = float(data["loss_amount_day"])
    profit_amount_day = float(data["profit_amount_day"])
    
    # 
    USE_DIFF_EXPIRY_INDEX = fileData["USE_DIFF_EXPIRY_INDEX"]
    SPY_QQQ_EXPIRY = fileData["SPY_QQQ_EXPIRY"]
    PROFIT_INCREMENT = fileData["profit_increment"]
    TRADE_COOLDOWN_SECONDS = fileData["distance_between_trade"]

    tradeExpiry_val = getExpiry(EXPIRY)
    spy_qqq_tradeExpiry = getExpiry(SPY_QQQ_EXPIRY)
    
    pnl_thread = None
    
    for each in stockList:
        trade_time_dict.update({"{}_{}".format(each, "CALL"):datetime.now(), "{}_{}".format(each, "PUT"):datetime.now()})
    
    logger.info("\n trade_time_dict is = {}\n".format(trade_time_dict))
    
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
        profit_amount_day = profit_amount_day + starting_loss
        loss_amount_day = loss_amount_day - starting_loss
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
        # synchronize positions to be monitored for closing.
        #synchronize_positions()
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