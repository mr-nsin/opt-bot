import threading
import time
import datetime
from datetime import date, datetime, timezone
from typing import List, Union
from ibapi import wrapper
from ibapi import utils
from ibapi.client import EClient, TickerId, OrderId
from ibapi.utils import iswrapper

from ibapi.contract import *
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import Order
from ibapi.wrapper import EWrapper, OrderState, Order, Contract, TickType, BarData, SetOfString, SetOfFloat

from common import Tick, logger, Position, Trade, setup_logger, PNL
import pandas as pd
from queue import Queue

class TwsApiClient(EWrapper, EClient):
    def __init__(self, host: str, port: int, clientId: int, event_queue: Queue, callback): 
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)
        self._host = host
        self._port = port
        self._clientId = clientId
        self.event_queue = event_queue
        self.nextValidOrderId = 0
        self.ticker_id = 0
        self.ticker_id_contract_cache = {}
        self.tick_cache = {}
        self.ticker_contract_cache = {}
        self.reqId = 1000
        self.contract_detail_fetched = False
        self.temp_contract_detail = None
        self.history_contract_reqId_map = {}
        self.history_cache = {}
        self.bar_size_conId_map = {}
        self.ticker_strike_cache = {}
        self.ticker_strike_fetched = False
        self.allOrders = []
        self.allOpenOrders = []
        self.openOrdersSymbol = []
        self.positions = {}
        self.trades_cache = {}
        self.process_trades_callback = callback
        self.initialization_done: bool = False
        self.connection_closed: bool= False
        self.pnl_cache = {}
        self.account_summary_cache = {}  # tag -> value (str from TWS; parse to float in engine)
        self._lock = threading.Lock()
        self.ACCOUNT_SUMMARY_REQ_ID = 2
        # When True, reconnects are done by the trading engine only (avoids multiple TWS connections)
        self.reconnect_handled_externally: bool = False

    @iswrapper
    def connectAck(self):
        logger.info('TWS connected.')
        threading.Thread(target=self.run, daemon=True).start()
        self.start_heartbeat()
    
    """def start(self)-> None:
        t = threading.Thread(target=self.run)
        t.start()"""
        
    @iswrapper
    def connectionClosed(self):
        logger.error("TWS connection closed.")
        if getattr(self, "reconnect_handled_externally", False):
            logger.info("Reconnect is handled by the trading engine; not reconnecting from client.")
            return
        logger.info("Attempting to reconnect...")
        self.try_reconnect()
        
    def try_reconnect(self, max_attempts=5, delay=5):
        self.connection_closed = True  # Signal existing thread to stop
        attempts = 0
    
        while attempts < max_attempts and not self.isConnected():
            try:
                logger.info(f"Reconnection attempt {attempts + 1}...")
                self.disconnect()
                time.sleep(delay)
                self.connect(self._host, self._port, self._clientId)
            
                if self.isConnected():
                    logger.info("Successfully reconnected to TWS")
                    self.connection_closed = False
                    threading.Thread(target=self.run, daemon=True).start()
                    # Re-request essential data
                    self.reqPositions()
                    self.reqAllOpenOrders()
                    return True
                
            except Exception as e:
                logger.error(f"Reconnect attempt {attempts + 1} failed: {e}")
                attempts += 1
            
        logger.error("Max reconnect attempts reached")
        return False

    @iswrapper
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        logger.info("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
        logger.info(f"NextValidId: {orderId}")
        
        # Request essential data
        self.reqPositions()
        self.reqAllOpenOrders()
        
        #self.reqPnL(self.managed_account)
    
        # Mark as initialized after a brief delay
        def mark_initialized():
            time.sleep(2)
            self.initialization_done = True
            logger.info("Initialization complete")
    
        threading.Thread(target=mark_initialized, daemon=True).start()
    
    def nextOrderId(self):
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid

    def nextTickerId(self)-> TickerId:
        self.ticker_id = self.ticker_id + 1
        return self.ticker_id

    def parseIBDatetime(self, s: str) -> Union[date, datetime]:
        """
        (ib-insync)
        Parse string in IB date or datetime format to datetime.
        """
        if len(s) == 8:
            # YYYYmmdd
            y = int(s[0:4])
            m = int(s[4:6])
            d = int(s[6:8])
            dt = date(y, m, d)
        elif s.isdigit():
            dt = datetime.fromtimestamp(int(s), timezone.utc)
        else:
            # YYYYmmdd  HH:MM:SS
            # or
            # YYYY-mm-dd HH:MM:SS.0
            ss = s.replace(' ', '').replace('-', '')[:16]
            dt = datetime.strptime(ss, '%Y%m%d%H:%M:%S')
        return dt

    def cancel_all_orders(self):
        self.reqGlobalCancel()
        
    def get_stock_contract(self, symbol: str):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        if "spx" in symbol.lower():
            contract.secType = "IND"
            contract.exchange = "CBOE"
        contract.currency = "USD"

        result = self.get_contract_detail(contract=contract)
        self.ticker_contract_cache[contract.symbol] = result
        return result

    # IB futures month code -> number (F=Jan .. Z=Dec)
    _FUT_MONTH = {"F": "01", "G": "02", "H": "03", "J": "04", "K": "05", "M": "06",
                  "N": "07", "Q": "08", "U": "09", "V": "10", "X": "11", "Z": "12"}

    def get_futures_contract(self, symbol: str, exchange: str = "CME"):
        """Build a FUT contract for symbols like NQU5, MNQU5 (root + month letter + year digit).
        If the parsed expiry is in the past (e.g. NQU5 = Sep 2025 when we're in 2026), use next front-quarter expiry
        so TWS will stream data (expired contracts get no ticks)."""
        contract = Contract()
        contract.secType = "FUT"
        contract.exchange = exchange
        contract.currency = "USD"
        # Parse e.g. NQU5 -> root=NQ, month=U (Sep), year=5 (2025) -> 202509
        if len(symbol) >= 4 and symbol[-1].isdigit() and symbol[-2].isalpha():
            year_digit = symbol[-1]
            month_letter = symbol[-2].upper()
            root = symbol[:-2]
            year = "202" + year_digit if year_digit in "456789" else "203" + year_digit  # 5->2025, 0->2030
            month = self._FUT_MONTH.get(month_letter, "01")
            expiry_ym = int(year + month)
            # If expiry is in the past, use next CME quarter (Mar/Jun/Sep/Dec) so we get live data
            now = datetime.utcnow()
            current_ym = now.year * 100 + now.month
            if expiry_ym < current_ym:
                quarters = [3, 6, 9, 12]  # CME NQ/MNQ quarterly
                y, m = now.year, now.month
                next_q = None
                for q in quarters:
                    if y * 100 + q > current_ym:
                        next_q = (y, q)
                        break
                if next_q is None:
                    next_q = (y + 1, 3)
                year, month = str(next_q[0]), f"{next_q[1]:02d}"
                contract.symbol = root
                contract.lastTradeDateOrContractMonth = f"{year}{month}"
                logger.info(f"Futures {symbol} expiry was in the past; using front quarter {year}{month}")
            else:
                contract.symbol = root
                contract.lastTradeDateOrContractMonth = f"{year}{month}"
        else:
            contract.symbol = symbol
            contract.lastTradeDateOrContractMonth = ""
        contract.localSymbol = symbol  # display symbol for UI (e.g. MNQU5)
        try:
            result = self.get_contract_detail(contract=contract)
            cache_key = f"{contract.symbol}{contract.lastTradeDateOrContractMonth}"
            self.ticker_contract_cache[cache_key] = result
            return result
        except Exception as e:
            logger.warning(f"get_futures_contract detail for {symbol} failed: {e}, using unresolved contract")
            self.ticker_contract_cache[getattr(contract, "symbol", symbol) + getattr(contract, "lastTradeDateOrContractMonth", "")] = contract
            return contract

    def get_options_contract(self, symbol, expiry, right, strike, exchange= "SMART", currency="USD", multiplier = 100):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"
        contract.strike = str(strike)
        contract.right = right
        contract.exchange = exchange
        contract.currency = currency
        contract.multiplier = multiplier
        contract.lastTradeDateOrContractMonth = expiry

        # result = self.get_contract_detail(contract=contract)
        ticker = f"{symbol}{expiry}{right}{strike}"
        self.ticker_contract_cache[ticker] = contract

        return contract

    def get_strikes(self, symbol: str):
        contract = self.ticker_contract_cache.get(symbol, None)
        if contract == None:
            contract = self.get_stock_contract(symbol=symbol)
        
        ticker_id = self.nextTickerId()
        if symbol.lower() == "spx":
            self.reqSecDefOptParams(ticker_id, symbol,"", "IND", contract.conId)
        else:
            self.reqSecDefOptParams(ticker_id, symbol,"", "STK", contract.conId)

        self.ticker_strike_fetched = False
        while self.ticker_strike_fetched != True:
            time.sleep(0.5)

        return self.ticker_strike_cache[ticker_id]

    """def get_contract_detail(self, contract: Contract):
        reqId = self.nextTickerId()
        self.reqContractDetails(reqId=reqId, contract=contract)
        self.contract_detail_fetched = False
        self.temp_contract_detail = None

        tries = 0
        while self.contract_detail_fetched != True and tries < 5:
            time.sleep(0.5)
            tries = tries + 1
        
        if self.temp_contract_detail == None:
            logger.info(f"{contract} contract details not found.")
            return contract

        return self.temp_contract_detail.contract"""
        
    def start_heartbeat(self):
        def heartbeat():
            while not self.connection_closed:
                if self.isConnected():
                    self.reqCurrentTime()  # Simple keepalive
                else:
                    logger.warning("Connection lost, attempting reconnect")
                    self.try_reconnect()
                time.sleep(60)  # Check every minute
    
        threading.Thread(target=heartbeat, daemon=True).start()
        
    def get_contract_detail(self, contract: Contract):
        """Request resolved contract from TWS. Uses shared state (not thread-safe); call from a single thread only."""
        reqId = self.nextTickerId()
        self.reqContractDetails(reqId=reqId, contract=contract)
        self.contract_detail_fetched = False
        self.temp_contract_detail = None

        max_wait = 10  # seconds (TWS can be slow when market is closed or under load)
        waited = 0
        while not self.contract_detail_fetched and waited < max_wait:
            time.sleep(0.5)
            waited += 0.5

        if self.temp_contract_detail is None:
            logger.warning(
                "Contract details timeout for %s — TWS did not respond in %ds. "
                "Using unresolved contract (trading may still work). Check: market hours, TWS connection, IB rate limits.",
                contract,
                max_wait,
            )
            return contract

        return self.temp_contract_detail.contract

    def subscribe(self, contract: Contract, snapshot = False)-> None:
        ticker_id: TickerId = None
        ticker = contract.symbol
        if contract.secType == "OPT":
            ticker = f"{contract.symbol}{contract.lastTradeDateOrContractMonth}{contract.right}{contract.strike}"
        elif contract.secType == "FUT":
            ticker = f"{contract.symbol}{getattr(contract, 'lastTradeDateOrContractMonth', '')}"
        
        # check if contract is already subscribed.
        # ticker_id = self.ticker_id_contract_cache.get(contract.conId, None)
        
        ticker_id = self.ticker_id_contract_cache.get(ticker, None)
        # if ticker_id != None:
        #     logger.info(f'Contract :{ticker} already subscribed.')
        #     return

        if ticker_id is None:
            # contract is not subscribed
            ticker_id = self.nextTickerId()
            self.ticker_id_contract_cache[ticker] = ticker_id
            if contract.secType == "OPT":
                self.tick_cache[ticker_id] = Tick(symbol=ticker, contract=contract, option_symbol=ticker)
            else:
                # STK/FUT: display symbol for logs (FUT: use original e.g. NQU5)
                self.tick_cache[ticker_id] = Tick(symbol=ticker, contract=contract)
        else:
            if snapshot == False:
                temp_ticker_id = ticker_id
                ticker_id = self.nextTickerId()
                self.ticker_id_contract_cache[ticker] = ticker_id
                self.tick_cache[ticker_id] = self.tick_cache[temp_ticker_id]

        logger.info(f"Subscribing contract {contract} ticker_id {ticker_id}")
        self.reqMktData(reqId=ticker_id, contract=contract, genericTickList='', snapshot=snapshot,regulatorySnapshot= False, mktDataOptions=[])
        
        # logger.info(f'subscribe: {contract.localSymbol}, TickerId: {ticker_id}')
        # self.ticker_id_contract_cache[contract.conId] = ticker_id
        

    def unsubscribe(self, contract: Contract)-> None:
        reqId = self.reqid_contract_cache.get(contract.conId, None)
        if reqId is None:
            logger.info(f'Contract: {contract.localSymbol} not found.')
            return
            
        logger.info(f'Unsubscribe {contract.localSymbol}')
        self.cancelMktData(reqId=reqId)

    def subscribe_historical_data(self, contract: Contract, fetchValue: str, barSize: str)-> None:
        # Generate a unique ticker id for the request
        ticker_id = self.nextTickerId()
        
        # Store the mapping of contract id to ticker id
        self.history_contract_reqId_map[contract.conId] = ticker_id
        
        # Store the mapping of bar size and contract id to ticker id
        bar_key = f"{barSize}-{contract.conId}"
        self.bar_size_conId_map[bar_key] = ticker_id
        
        # Make a historical data request with the generated ticker id, contract, fetch value, bar size, trade type, 
        # and historical data settings
        self.reqHistoricalData(ticker_id, contract, '', fetchValue, barSize, "TRADES", 0, 1, True, [])

    def get_all_positions(self):
        return self.positions.values()

    def get_all_open_orders(self):
        return self.allOpenOrders, self.openOrdersSymbol

    def get_last(self, contract: Contract)-> None:
        ticker = contract.symbol
        if contract.secType == "OPT":
            ticker = f"{contract.symbol}{contract.lastTradeDateOrContractMonth}{contract.right}{contract.strike}"
        elif contract.secType == "FUT":
            ticker = f"{contract.symbol}{getattr(contract, 'lastTradeDateOrContractMonth', '')}"

        # ticker_id: TickerId = self.ticker_id_contract_cache.get(contract.conId, None)
        ticker_id: TickerId = self.ticker_id_contract_cache.get(ticker, None)
        if ticker_id is None:
            logger.error(f'get_last: {contract.localSymbol} TickerId not found.')
            return None
        
        tick: Tick = self.tick_cache.get(ticker_id, None)
        if tick  is None:
            logger.error(f'{contract.localSymbol} last price not found.')
            return None
        
        return tick.last

    def get_data(self, contract: Contract)-> Tick:
        # Get the symbol from the contract
        ticker = contract.symbol
        
        # If the security type is an option, create a unique ticker symbol by combining the symbol, last trade date, right and strike
        if contract.secType == "OPT":
            ticker = f"{contract.symbol}{contract.lastTradeDateOrContractMonth}{contract.right}{contract.strike}"
        elif contract.secType == "FUT":
            ticker = f"{contract.symbol}{getattr(contract, 'lastTradeDateOrContractMonth', '')}"
            
        # Check if the ticker is in the ticker ID to contract cache
        ticker_id: TickerId = self.ticker_id_contract_cache.get(ticker, None)
        
        # If the ticker ID is not found, log an error message and return None
        if ticker_id is None:
            logger.error(f'get_data: {contract.localSymbol} TickerId not found.')
            return None
        
        # Return the tick from the tick cache using the ticker ID
        return self.tick_cache.get(ticker_id, None)
    
    def get_stock_data(self, symbol):
        contract = self.ticker_contract_cache[symbol]
        return self.get_data(contract=contract)

    def get_options_data(self, symbol: str, expiry: str, right: str, strike: float)-> Tick:
        ticker = f"{symbol}{expiry}{str(right[0])}{strike}"
        contract = self.ticker_contract_cache.get(ticker, None)
        if contract:
            return self.get_data(contract=contract)
        
        logger.error(f"contract not found: {ticker}")
        contract = self.get_options_contract(symbol, expiry, right, strike)
        self.subscribe(contract=contract)
        data = self.get_data(contract=contract)
        tries = 0
        while data is None and tries < 8:
            time.sleep(0.25)
            data = self.get_data(contract=contract)
            tries += 1

        return data
        
    
    def get_bars(self, stock: str, barSize: str, limit: int = 8):
        """
        Retrieve bars for a given stock.

        :param stock: The stock symbol.
        :param limit: The number of bars to retrieve (default is 8).
        :return: A list of bars for the stock.
        """

        # Retrieve the contract for the stock from the ticker contract cache
        contract = self.ticker_contract_cache.get(stock, None)
        
        if not contract:
            # If the contract is not found, log an error message and return
            logger.info(f"{stock} contract not found.")
            return

        bar_key = f"{barSize}-{contract.conId}"
        ticker_id = self.bar_size_conId_map.get(bar_key, None)
        if ticker_id == None:
            logger.info(f"{stock} {barSize} bars not found.")
            return

        bar_map = self.history_cache.get(ticker_id, None)
        if bar_map == None:
            logger.error(f"{stock} bars not found.")
            return None

        # Convert the bar map values to a list
        values = list(bar_map.values())
        if limit == 1:
            # If the limit is 1, return the last element of the values list
            return [values[-1]]
        else:
            # If the limit is 8, return the last 8 elements of the values list
            return values[-limit:]

        # day data
        return values

    def to_df(self, bars):
        """
        converts bars dictionary to a dataframe
        """
        data = [{"date" : o.date, "open" : o.open, "high" : o.high, "low" : o.low, "close" : o.close, "volume" : o.volume } for o in bars]
        df = pd.DataFrame(data=data)

        return df

    def get_open_position(self, symbol: str) -> Position:
        """
        Get the open position for a given symbol.

        Args:
            symbol: The symbol to search for.

        Returns:
            The open position for the given symbol, or None if no open position is found.
        """
        logger.info(f"get_open_position: {symbol}")
        return next(
            (
                pos
                for pos in self.positions.values()
                if pos.symbol == symbol and pos.position != 0
            ),
            None,
        )
        
    def get_pnl(self, account: str) -> PNL:
        """
        Get the open position for a given symbol.

        Args:
            symbol: The symbol to search for.

        Returns:
            The open position for the given symbol, or None if no open position is found.
        """
        logger.info(f"get_PNL for account : {account}")
        logger.info(f"PNL Data for account : {self.pnl_cache}")
        return self.pnl_cache.get("daily", 0.0), self.pnl_cache.get("realized", 0.0)
        

    def get_options_position(self, symbol: str, expiry: str, right: str, strike: float) -> Position:
        """
        Get the open position for a given symbol.

        Args:
            symbol: The symbol to search for.

        Returns:
            The open position for the given symbol, or None if no open position is found.
        """
        logger.info(f"get_options_position: {symbol}{expiry}{right}{strike}")
        return next(
            (
                pos
                for pos in self.positions.values()
                if pos.symbol == symbol
                and pos.expiry == expiry
                and pos.right == right
                and pos.strike == strike
                and pos.position != 0
            ),
            None,
        )
        
    @iswrapper
    # def error(self, reqId: TickerId, errorCode: int, errorString: str):
    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson = ""):
        # super().error(reqId, errorCode, errorString, advancedOrderRejectJson)
        logger.error(f'Id: {reqId}, Code: {errorCode}, Msg: {errorString}')
        if errorCode == 200:
            symbol = self.ticker_id_contract_cache.get(reqId, None)
            if symbol != None:
                logger.error(f"Code: {errorCode}, Symbol: {symbol}")

    @iswrapper
    def winError(self, text: str, lastError: int):
        # super().winError(text, lastError)
        logger.error(f'Msg: {text} Last error: {lastError}')

    @iswrapper
    def tickSnapshotEnd(self, reqId: int):
        # logger.info(f"Snapshot completed {reqId} ")
        pass

    @iswrapper
    def tickPrice(self, reqId, tickType, price: float, attrib):
        # The function is triggered when there is a change in the price of a financial instrument
        # reqId is a unique identifier for the request that triggered the event
        # tickType specifies the type of price update, such as bid, ask, last, or close
        # price is the new price
        # attrib is a set of attributes that provide additional information about the price update
        
        # Get the tick data from the cache, using the reqId as a key
        with self._lock:
            tick: Tick = self.tick_cache.get(reqId, None)

            # If the tick data is not found in the cache, return
            if tick is None:
                return

            # Update the bid price of the tick data, if the tickType is 1
            if tickType == 1:
                tick.bid = price
                if self.initialization_done and tick.contract.secType == "OPT":
                    self.event_queue.put({"tick": tick})
            # Update the ask price of the tick data, if the tickType is 2
            elif tickType == 2:
                tick.ask = price
            # Update the last price of the tick data, if the tickType is 4
            # Also, put an event in the event queue, which contains the tick data and the last price
            elif tickType == 4:
                tick.last = price
                if self.initialization_done:
                    self.event_queue.put({"tick": tick})
            # Update the close price of the tick data, if the tickType is 9
            elif tickType == 9:
                tick.close = price

    @iswrapper
    def tickSize(self, reqId,  tickType, size):
        # The function is triggered when there is a change in the size of a tick, which is the smallest possible change in price for a financial instrument
        # reqId is a unique identifier for the request that triggered the event
        # tickType specifies the type of tick that caused the event, such as volume, open interest of calls, or open interest of puts
        # size is the new size of the tick
        
        # Get the tick data from the cache, using the reqId as a key
        tick: Tick = self.tick_cache.get(reqId, None)

        # If the tick data is not found in the cache, return
        if tick is None:
            return

        # Update the volume of the tick data, if the tickType is 8
        if tickType == 8:
            tick.volume = size
        # Update the open interest of calls of the tick data, if the tickType is 27
        elif tickType == 27:
            tick.open_interest_call = size
        # Update the open interest of puts of the tick data, if the tickType is 28
        elif tickType ==  28:
            tick.open_interest_put = size

            
        # logger.info(quote)

    @iswrapper    
    def tickOptionComputation(self, reqId: TickerId, tickType: TickType, tickAttrib: int,
                                impliedVol: float, delta: float, optPrice: float, pvDividend: float,
                                gamma: float, vega: float, theta: float, undPrice: float):
        tick: Tick = self.tick_cache.get(reqId, None)
        if tick is None:
            return

        if tickType == 13:
            tick.delta = delta
            logger.info("Delta for contract = {}".format(tick.delta))

    @iswrapper
    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        self.temp_contract_detail = contractDetails

    @iswrapper
    def contractDetailsEnd(self, reqId: int):
        self.contract_detail_fetched = True

    @iswrapper
    def historicalData(self, reqId: int, bar: BarData):
        bar.date = self.parseIBDatetime(bar.date)
        bar_map = self.history_cache.get(reqId, None)
        
        if bar_map == None:
            bar_map = {}
            self.history_cache[reqId] = bar_map

        bar_map[bar.date] = bar
        # print(bar)

    @iswrapper
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        print(reqId, start, end)
        
    """@iswrapper
    def pnl(self, reqId: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float):
        self.pnl_cache.update({
            "daily": dailyPnL,
            "unrealized": unrealizedPnL,
            "realized": realizedPnL
        })
        print(f"PNL Update for Req {reqId} - Daily: {dailyPnL}, Unrealized: {unrealizedPnL}, Realized: {realizedPnL}")"""
        
    @iswrapper
    def pnl(self, reqId: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float):
        self.pnl_cache.update({
            "daily": dailyPnL,
            "unrealized": unrealizedPnL,
            "realized": realizedPnL
        })
        print(f"PNL Update for Req {reqId} - Daily: {dailyPnL}, Unrealized: {unrealizedPnL}, Realized: {realizedPnL}")
        """if not hasattr(self, "_pnl_cancelled"):
            self.cancelPnL(reqId)
            self._pnl_cancelled = True"""


    """@iswrapper
    def pnlSingle(self, reqId: int, pos: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float, value: float):
        print(f"PNL Single Req {reqId} - Pos: {pos}, Daily: {dailyPnL}, Unrealized: {unrealizedPnL}, Realized: {realizedPnL}, Value: {value}")"""


    @iswrapper 
    def historicalDataUpdate(self, reqId: int, bar: BarData):
        bar.date = self.parseIBDatetime(bar.date)
        # print(f"historicalDataUpdate: {bar}")
        bar_map = self.history_cache.get(reqId, None)
        bar_map[bar.date] = bar
        # print(bar)
        # print(datetime.datetime.now().strftime("%Y%m%d%H%M"))

    @iswrapper
    def securityDefinitionOptionParameter(self, reqId: int, exchange: str, underlyingConId: int, tradingClass: str, multiplier: str, expirations: SetOfString, strikes: SetOfFloat):
        self.ticker_strike_cache[reqId] = list(strikes)

    @iswrapper
    def securityDefinitionOptionParameterEnd(self, reqId: int):
        self.ticker_strike_fetched = True

    @iswrapper
    def orderStatus(self, orderId: OrderId, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        self.allOrders.append({orderId: {"status": status, "filled": filled, "remaining": remaining, "avgFullPrice": avgFillPrice}})
        trade: Trade = self.trades_cache.get(orderId, None)

        if trade is None:
            logger.error(f'OrderId {orderId} not found.')
            return

        #status = status.lower()
        status_lower = status.lower()

        # check for duplicate
        if trade.order_status == status_lower and trade.executed_qty == filled and trade.remaining_qty == remaining:
            return

        trade.executed_qty = filled 
        trade.remaining_qty = remaining
        trade.average_price = avgFillPrice
        trade.last_fill_price = lastFillPrice
        trade.order_status = status_lower

        if status_lower in ["filled", "cancelled", "expired", "rejected", "inactive"]:
            self.openOrdersSymbol.remove(trade.contract.symbol)
            # self.allOpenOrders.pop(orderId)

        self.process_trades_callback(trade)


    @iswrapper
    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        logger.info(f"openOrder: {orderId}")
        # self.allOpenOrders.append({orderId: orderState.status})
        if contract.symbol not in self.openOrdersSymbol:
            self.openOrdersSymbol.append(contract.symbol)
        
        trade: Trade = self.trades_cache.get(orderId, None)
        if trade is None:
            order.contract = contract
            trade = Trade(contract=contract, order=order, orderStatus=orderState)
            self.trades_cache[order.orderId] = trade

    @iswrapper
    def openOrderEnd(self):
        # return super().openOrderEnd()
        logger.info("openOrderEnd")


    @iswrapper
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        if contract.secType != "OPT":
            return

        ticker = f"{contract.symbol}{contract.lastTradeDateOrContractMonth}{contract.right}{contract.strike}"
        position_obj = self.positions.get(ticker, None)
        if position_obj is None:
            position_obj = Position(account=account, symbol=contract.symbol, position=position, strike=contract.strike, right=contract.right, expiry=contract.lastTradeDateOrContractMonth, avg_cost=avgCost)
            self.positions[ticker] = position_obj
            logger.info(position_obj)
            return

        position_obj.position = position
        position_obj.avg_cost = avgCost
        if position == 0:
            self.positions.pop(ticker, None)
        logger.info(position_obj)

        # self.positions.append(
        #     {"Account": account, "Symbol": contract.symbol, "Position": position, "Strike": contract.strike,
        #      "Right": contract.right, "Expiry": contract.lastTradeDateOrContractMonth})
    
    @iswrapper
    def positionEnd(self):
        # return super().positionEnd()
        logger.info("positionEnd")

    #@iswrapper
    #def managedAccounts(self, accountsList: str):
    #    logger.info(f"managed accounts: {accountsList}")
        
    @iswrapper
    def managedAccounts(self, accountsList: str):
        accounts = accountsList.split(",")
        self.managed_account = accounts[0]

        logger.info(f"Using account for PnL: {self.managed_account}")

        # Cancel existing subscription safely
        try:
            self.cancelPnL(1)
        except Exception:
            pass

        # CORRECT reqPnL signature (keep subscription open for continuous updates)
        self.reqPnL(
            reqId=1,
            account=self.managed_account,
            modelCode=""
        )

        # Request account summary for all IBKR metrics (continuous updates)
        _tags = (
            "NetLiquidation,TotalCashValue,GrossPositionValue,BuyingPower,"
            "AvailableFunds,ExcessLiquidity,MaintMarginReq,InitialMarginReq,"
            "RealizedPnL,UnrealizedPnL,SettledCash,EquityWithLoanValue"
        )
        try:
            self.cancelAccountSummary(self.ACCOUNT_SUMMARY_REQ_ID)
        except Exception:
            pass
        self.reqAccountSummary(self.ACCOUNT_SUMMARY_REQ_ID, "All", _tags)

    @iswrapper
    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        with self._lock:
            self.account_summary_cache[tag] = value

    @iswrapper
    def accountSummaryEnd(self, reqId: int):
        pass

    @iswrapper
    def connectionClosed(self):
        logger.error("TWS connection closed.")
        self.connection_closed = True