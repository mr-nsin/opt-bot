# Core Modules Reference — OPT_BOT

## 1. BOT.py — Main Trading Engine

**Location:** `/BOT.py` (~2400 lines)
**Role:** Core orchestration of the entire trading system.

### Key Globals

| Global | Type | Purpose |
|---|---|---|
| `client` | `TwsApiClient` | IB API client instance |
| `event_queue` | `Queue` | Tick event queue from IB |
| `order_mgr` | `OrderManager` | Manages order lifecycle |
| `db` | `DAL` | Database access layer |
| `NY_TZ` | `timezone` | New York timezone for market hours |
| `trade_time_dict` | `dict` | Tracks last trade time per `{symbol}_{right}` |
| `signal_dict` | `dict` | Stores last/current SuperTrend signal per stock |
| `STOP_TRADING` | `bool` | Flag to stop trading loop |
| `DAILY_LIMIT_HIT` | `bool` | Flag when daily P&L limit reached |
| `DAY_LOCKED` | `bool` | Locks all trading for the day |
| `CLOSE_ALL_ORDERS` | `bool` | Signal to close all open positions |

### Key Functions

| Function | Purpose |
|---|---|
| `main_call()` | Entry point — reads config, initializes all components, subscribes to market data, starts event processing |
| `start_trading(config)` | Called by GUI — sets config globals and launches `main_call()` in a subprocess |
| `stop_trading()` | Sets `STOP_TRADING = True`, terminates subprocess |
| `init_api_client(queue, order_mgr)` | Creates and connects `TwsApiClient` |
| `placeOrder(...)` | Places an options order via IB API with TP/SL setup |
| `placeAndVerifyOrder(...)` | Validates cooldown, checks locks, then calls `placeOrder()` |
| `getCallPutEngulfCheck(stock, limit, indicator)` | Detects engulfing/SuperTrend signals from candle data |
| `checkConditionsAndTrade(dataValueSet, stock_tick)` | Validates all trade conditions (position, delta, volume, ATR, VWAP) and executes |
| `checkAlgoAndTrade(stock, right)` | Validates ATR, VWAP, and EMA conditions |
| `takeTrade(stock, right, ...)` | Selects strike, calculates TP/SL, calls `placeAndVerifyOrder()` |
| `event_processor(queue)` | Main loop — processes tick events, routes to signal detection or position monitoring |
| `pnl_watchdog_thread()` | Monitors daily P&L vs limits, triggers DAY_LOCK if exceeded |
| `monitor_positions_loop()` | Iterates active orders, calls `check_and_close_position()` |
| `timeCheckAndCloseProgram(...)` | Checks if market hours ended, triggers close-all |
| `getATRValue(stock, candles)` | Calculates ATR from candle data |
| `checkVWAPValue(stock, right, candles)` | Calculates intraday VWAP and validates against signal direction |
| `get_delta_volume(stock, strike, right, expiry)` | Fetches delta and volume for an options contract |
| `getStockNearStrikes(stock, strikes, tick)` | Finds nearest ITM/OTM strikes to current price |
| `check_TRADE_COOLDOWN_SECONDS(stock, right)` | Checks if cooldown period has elapsed since last trade |

### Config Loading (at module level)

Reads `config.json` at import time into `fileData` dict, then extracts globals:
- `IP`, `PORT`, `CLIENTID` — TWS connection
- `fetchValue`, `candleTime` — historical data params
- `stockListToTrade` — dict of `{symbol: exchange}`
- `CALL_DELTA_CHECK`, `PUT_DELTA_CHECK` — delta thresholds
- `MAX_CONTRACT_AMOUNT` — max $ per contract
- `profit_amount_day`, `loss_amount_day` — daily P&L limits
- `distance_between_trade` → `TRADE_COOLDOWN_SECONDS`
- `PROFIT_INCREMENT` — trailing profit step size

---

## 2. tws_api_client.py — IB API Wrapper

**Location:** `/tws_api_client.py` (~738 lines)
**Role:** Wraps Interactive Brokers `ibapi` (EWrapper + EClient).

### Class: `TwsApiClient(EWrapper, EClient)`

**Constructor args:** `host`, `port`, `clientId`, `event_queue`, `callback`

### Key Caches

| Cache | Type | Purpose |
|---|---|---|
| `ticker_id_contract_cache` | `dict` | Maps ticker string → ticker_id |
| `tick_cache` | `dict` | Maps ticker_id → `Tick` object (live prices) |
| `ticker_contract_cache` | `dict` | Maps ticker string → `Contract` object |
| `history_cache` | `dict` | Maps reqId → `{date: BarData}` |
| `positions` | `dict` | Maps ticker → `Position` object |
| `trades_cache` | `dict` | Maps orderId → `Trade` object |
| `pnl_cache` | `dict` | `{"daily", "unrealized", "realized"}` |

### Key Methods

| Method | Purpose |
|---|---|
| `connectAck()` | On connect — starts message thread + heartbeat |
| `connectionClosed()` | On disconnect — sets `connection_closed = True` |
| `try_reconnect(max=5, delay=5)` | Reconnection loop with position re-request |
| `start_heartbeat()` | Background thread checking connection every 60s |
| `get_stock_contract(symbol)` | Creates STK contract, fetches details |
| `get_options_contract(symbol, expiry, right, strike)` | Creates OPT contract |
| `get_strikes(symbol)` | Fetches available strikes via `reqSecDefOptParams` |
| `subscribe(contract)` | Subscribes to real-time market data |
| `subscribe_historical_data(contract, fetch, bar)` | Subscribes to historical + streaming bars |
| `get_data(contract)` → `Tick` | Returns cached tick data |
| `get_bars(stock, barSize, limit)` | Returns cached historical bars |
| `get_open_position(symbol)` → `Position` | Finds open position for symbol |
| `get_pnl(account)` → `(daily, realized)` | Returns cached P&L |
| `get_options_position(symbol, expiry, right, strike)` | Finds specific options position |

### IB Callbacks (via `@iswrapper`)

| Callback | Purpose |
|---|---|
| `tickPrice(reqId, tickType, price)` | Updates bid/ask/last/close in tick_cache, pushes to event_queue |
| `tickSize(reqId, tickType, size)` | Updates volume, open interest |
| `tickOptionComputation(...)` | Updates delta for options |
| `orderStatus(orderId, status, ...)` | Routes to `process_trades_callback` (OrderManager) |
| `openOrder(orderId, contract, order)` | Tracks open orders |
| `position(account, contract, position, avgCost)` | Updates positions cache (OPT only) |
| `historicalData/Update(reqId, bar)` | Stores/updates bars in history_cache |
| `managedAccounts(accountsList)` | Captures account ID, subscribes to P&L |
| `pnl(reqId, daily, unrealized, realized)` | Updates pnl_cache |

---

## 3. order_manager.py — Order Lifecycle Management

**Location:** `/order_manager.py` (~541 lines)
**Role:** Manages entry/exit orders, TP/SL monitoring, trade cooldowns.

### Class: `OrderManager`

**Constructor:** `__init__(self, db: DAL)`

### Key Caches

| Cache | Type | Purpose |
|---|---|---|
| `orders_cache` | `dict` | All orders by ID |
| `entry_orders_cache` | `dict` | Entry orders by symbol |
| `exit_orders_cache` | `dict` | Exit orders by symbol |
| `order_id_tick_lookup` | `dict` | Maps order_id → Tick for price monitoring |
| `recent_trade_closures` | `dict` | Cooldown tracking per `{symbol}_{right}` |

### Key Methods

| Method | Purpose |
|---|---|
| `set_client(client)` | Sets the TwsApiClient reference |
| `add_entry_order(order, tick)` | Registers a new entry order in all caches |
| `del_entry_order(order, tick)` | Removes entry order from caches |
| `add_exit_order(order, tick)` | Registers exit order |
| `process_trade(trade)` | Main callback — routes by status (filled/cancelled/rejected/etc.) |
| `process_fill(trade, order, status)` | Handles fill — updates DB, links entry↔exit, records cooldown |
| `close_position(order, tick)` | Places market exit order, creates exit order object |
| `check_and_close_position(tick)` | Main TP/SL check loop — validates price data, calls check_take_profit/check_stop_loss |
| `check_take_profit(tick, order, tick)` | **Trailing profit logic** — raises target as price rises, closes when price falls back |
| `check_stop_loss(last_price, order, tick)` | Closes if exit price ≤ stoploss_price |
| `log_order_status(order, tick)` | Comprehensive debug logging |

### Trailing Profit Logic (check_take_profit)

1. Use bid price (what you can sell at) if available, else last price
2. If `exit_price >= current_profit_price`: set `profit_trigger = True`, raise target by `profit_increment`
3. If trigger active and `exit_price < (current_profit_price - profit_increment)`: CLOSE position
4. This creates a **ratcheting profit target** — price must exceed target to activate, then trails up

---

## 4. data_access.py — Database Access Layer (DAL)

**Location:** `/data_access.py` (~254 lines)
**Role:** Queue-based SQLite operations for options orders.

### Class: `DAL`

### Key Design

- Uses a dedicated `Thread` running `handle_orders_queue()` loop
- All writes go through a `Queue` — insert/update/delete are enqueued
- Thread-safe with `Lock` for actual DB operations
- Database: `db/orders.db`

### Table: `option_orders`

| Column | Type | Purpose |
|---|---|---|
| id | INTEGER PK | Order ID (from IB) |
| conId | INTEGER | Contract ID |
| symbol | TEXT | Stock symbol |
| expiration | TEXT | Expiry date |
| strike | REAL | Strike price |
| right | TEXT | CALL/PUT |
| order_type | TEXT | LMT/MKT |
| order_side | TEXT | BUY/SELL |
| order_qty | INTEGER | Quantity |
| order_price | REAL | Limit price |
| order_status | TEXT | Current status |
| executed_qty | INTEGER | Filled quantity |
| average_price | REAL | Avg fill price |
| profit_price | REAL | Initial profit target |
| stoploss_price | REAL | Stop loss price |
| profit_trigger | INTEGER | Boolean — trailing activated |
| current_profit_price | REAL | Current trailing target |
| profit_increment | REAL | Trailing step size |
| exit_placed | INTEGER | Boolean — exit order sent |
| exit_order | INTEGER | Boolean — is this an exit order |
| active | INTEGER | Boolean — order still active |
| ref_order_id | INTEGER | Links exit → entry order |

---

## 5. common.py — Shared Data Structures

**Location:** `/common.py` (~215 lines)
**Role:** Dataclasses, helper functions, logger setup.

### Dataclasses

| Class | Purpose |
|---|---|
| `OptionOrder` | Full order state — entry/exit, TP/SL, trailing profit fields |
| `Tick` | Real-time market data — bid/ask/last/delta/volume/OI, active order reference |
| `Position` | Account position — symbol, qty, strike, right, expiry |
| `PNL` | P&L data — daily, unrealized, realized |
| `Trade` | Order execution data — contract, order, status, fill prices |

### Key Functions

| Function | Purpose |
|---|---|
| `getExpiry(EXPIRY)` | Resolves "current"/"next"/"0DTE"/"1DTE" to YYYYMMDD format |
| `MarketOrder(action, qty)` | Creates IB Market Order object |
| `create_order_obj(...)` | Factory for `OptionOrder` from order params |
| `setup_logger(name)` | Creates rotating file logger in `logs/` directory |

### Global Logger

`logger = setup_logger('bot')` — used throughout the codebase via `from common import logger`.

---

## 6. Indicators.py — Technical Analysis Library

**Location:** `/Indicators.py` (~406 lines)
**Role:** Technical indicator calculations using yfinance and pandas.

### Indicators

| Function | Indicator | Input |
|---|---|---|
| `BOTSingal(data, multiplier)` | **SuperTrend** — primary signal generator | DataFrame with OHLC |
| `alphaTrend(stock, dataSet, period, interval)` | Alpha Trend (SuperTrend variant) | Stock symbol or DataFrame |
| `RSI(ticker, n, period, interval)` | Relative Strength Index | Stock symbol |
| `MACD(stock, start, end)` | Moving Average Convergence Divergence | Stock symbol |
| `ATR(stock, start, end, numDays)` | Average True Range | Stock symbol |
| `SMA(DF, days)` | Simple Moving Average | DataFrame |
| `EMA_8_13_21(df)` | Triple EMA (8/13/21) | DataFrame |
| `OBV(stock, start, end)` | On-Balance Volume | Stock symbol |
| `IchimokuCloud(stock, start, end)` | Ichimoku Cloud (base line) | Stock symbol |
| `WILLIAMS(stock, start, end, days)` | Williams %R | Stock symbol |
| `fibonacci(stock, start, end)` | Fibonacci retracement levels | Stock symbol |
| `getRSICalculate(DF, n)` | RSI calculation on DataFrame | DataFrame |
| `rsiOverSMA(ticker, n, period, interval)` | RSI over SMA (multi-timeframe) | Stock symbol |

### Usage in BOT.py

- `BOTSingal()` is the primary signal generator via `getCallPutEngulfCheck(stock, indicator="supertrend")`
- `EMA_8_13_21()` is used in `checkAlgoAndTrade()` for trend confirmation
- `getATR()` (in BOT.py, not Indicators.py) calculates ATR from IB candle data

---

## 7. logger.py — Secondary Logger

**Location:** `/logger.py` (~36 lines)
**Role:** `Loggers` class used in `BOT.py` (imported but minimally used — primary logging is via `common.py`'s `setup_logger`).

### Class: `Loggers`

- Initializes with `logFileName`
- Creates rotating file handler in `Logs/` directory
- Provides `info()`, `debug()`, `error()`, `warning()` methods
