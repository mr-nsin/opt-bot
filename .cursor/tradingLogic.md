# Trading Logic — OPT_BOT

## Overview

The bot trades **US equity options** (calls and puts) on stocks like SPY, QQQ, TSLA, AAPL, AMD, NVDA, MSFT, AMZN, BABA. It uses real-time market data from IB TWS to detect signals and execute trades automatically.

## Signal Detection

### Primary Signal: SuperTrend (`BOTSingal`)

Used when `indicator="supertrend"` (default in `getCallPutEngulfCheck`):

1. Fetch last 21 candles from IB via `client.get_bars(stock, barSize=candleTime, limit=21)`
2. Build DataFrame with Date/Close/High/Low columns
3. Calculate SuperTrend via `Indicators.BOTSingal(df)` — returns BUY/SELL signal per candle
4. Store `last_signal` and `current_signal` in `signal_dict[stock]`
5. **Signal trigger**: When `last_signal != current_signal` (signal flip)
   - If current signal is "BUY" → right = "CALL"
   - If current signal is "SELL" → right = "PUT"

### Secondary Signal: Engulfing Pattern

Used when `indicator != "supertrend"`:

1. Fetch last 8 candles
2. Analyze 7 candles (candle_0 through candle_6) for:
   - **Bullish Engulfing** patterns (CALL signals): Multiple variants:
     - A-pattern (3 candle pure bullish): c6_close >= c5_close, c5 engulfs c4, with volume confirmation
     - B-pattern (4 candle bullish): c6 engulfs across c5/c4/c3
     - C-pattern (hammer-like): Long lower wick + volume surge
     - D-pattern (medium buy): Engulfing c4 with relaxed volume
     - E-pattern (medium buy): Engulfing across c3-c6
   - **Bearish Engulfing** patterns (PUT signals):
     - A-pattern: c6 engulfs c4/c5 downward
     - B-pattern: Strong bear candle engulfing previous
     - B-heavy: c6 below c5/c4/c3 opens
3. Each pattern has **volume confirmation** thresholds (0.55x to 1.25x multipliers)
4. Returns `(matched: bool, right: str, stock: str, strength: str)`
   - Strength levels: `strongBuy`, `heavyBuy`, `normalBuy`, `mediumBuy`, `mediumSell`, `strongSell`, `normalSell`

## Trade Execution Flow

### Step 1: Signal Detection (event_processor → getCallPutEngulfCheck)

```
Tick event received → Is stock tick?
  → getCallPutEngulfCheck(stock) → signal detected?
    → Yes: checkConditionsAndTrade(signal_data, stock_tick)
```

### Step 2: Pre-Trade Validation (checkConditionsAndTrade)

Before placing any trade, the following checks are performed:

1. **Day Lock Check**: `DAY_LOCKED and CLOSE_ALL_ORDERS` → reject
2. **Existing Position Check**: `client.get_open_position(symbol)` — same right = reject
3. **Existing Order Check**: `order_mgr.get_entry_order(symbol)` — active order = reject
4. **Time Check**: `timeCheckAndCloseProgram()` — within market hours?
5. **P&L Limit Check**: Daily profit/loss limits not exceeded

### Step 3: Condition Validation (checkAlgoAndTrade)

1. **ATR Check**: `getATRValue(stock, candles)` >= `ATR_CHECKS` threshold (0.047)
2. **VWAP Check** (if enabled): 
   - CALL: `runningLast >= VWAP and runningOpen >= VWAP`
   - PUT: `runningLast < VWAP`
3. **EMA Calculation**: `EMA_8_13_21(candles)` — triple EMA for trend context

### Step 4: Strike Selection (takeTrade)

1. Get nearest strikes from `expiryStrike.json` via `getStockNearStrikes()`
2. Determine expiry:
   - Stocks: "current" or "next" weekly (Friday)
   - ETFs (SPY/QQQ): "0DTE" (today) or "1DTE" (next day)
3. Subscribe to options contracts for nearest strikes
4. For each candidate strike:
   - Fetch delta and volume via `get_delta_volume()`
   - **Delta filter**: 
     - CALL: delta >= `CALL_DELTA_CHECK` (0.35)
     - PUT: abs(delta) >= abs(`PUT_DELTA_CHECK`) (-0.35)
   - **Volume filter**: volume >= `VOLUME_CHECK` (100)
5. Select the strike with the best delta match

### Step 5: Order Calculation

1. **Quantity**: `MAX_CONTRACT_AMOUNT / (ask_price * 100)` — max contracts within dollar limit ($350)
2. **Entry price**: Ask price for BUY
3. **Take Profit**: `entry_price + profit_increment` (configurable, default 0.03)
4. **Stop Loss**: `entry_price * (1 - stoploss_pct)` — typically 30-50% of entry
5. **Order type**: LMT (limit) for entry
6. **Order expiry**: GTD (Good Till Date) with `ORDER_EXPIRY_TIMER` seconds (15s)

### Step 6: Order Placement (placeAndVerifyOrder → placeOrder)

1. **Cooldown check**: `trade_time_dict[{symbol}_{right}]` — must exceed `TRADE_COOLDOWN_SECONDS` (610s)
2. **Lock check**: `options_tick.locked` — prevents concurrent order attempts
3. **Active order check**: No pending/submitted order for same symbol
4. Create `OptionOrder` object with all TP/SL params
5. Register in `OrderManager` caches
6. Place via `client.placeOrder(orderId, contract, order)`

## Position Management

### Trailing Take Profit

Managed in `OrderManager.check_take_profit()`:

```
entry_price = $1.50
profit_price (initial) = $1.53 (entry + 0.03 increment)
profit_increment = $0.03

Price rises to $1.55:
  → exit_price ($1.55) >= current_profit_price ($1.53)
  → profit_trigger = True
  → current_profit_price = $1.55 + $0.03 = $1.58

Price continues to $1.60:
  → exit_price ($1.60) >= current_profit_price ($1.58)
  → current_profit_price = $1.60 + $0.03 = $1.63

Price falls to $1.57:
  → profit_trigger = True AND exit_price ($1.57) < ($1.63 - $0.03 = $1.60)
  → CLOSE POSITION (locked in profit from $1.50 → ~$1.57)
```

### Stop Loss

Managed in `OrderManager.check_stop_loss()`:
- If `exit_price <= stoploss_price` → CLOSE POSITION via market order
- Uses bid price (what you can actually sell at) if available

### Position Close Mechanism

`OrderManager.close_position(order, tick)`:
1. Determine action: reverse of entry (BUY→SELL, SELL→BUY)
2. Create Market Order for `executed_qty`
3. Create exit `OptionOrder` with `exit_order=True` and `ref_order_id` pointing to entry
4. Place via `client.placeOrder()`

### On Fill (process_fill)

- **Entry fill**: Log, update DB
- **Exit fill**: Record cooldown time (`trade_time_dict[key]`), deactivate entry order, delete both from DB

## Daily P&L Risk Management

### PnL Watchdog Thread (`pnl_watchdog_thread`)

Runs every ~60 seconds:
1. Fetches `client.get_pnl(account)` → `(daily_pnl, realized_pnl)`
2. Compares against `profit_amount_day` and `loss_amount_day`
3. If limit exceeded:
   - Sets `DAY_LOCKED = True`, `CLOSE_ALL_ORDERS = True`
   - Closes all active positions
   - Blocks all new orders
   - Calls `hard_exit()` (SIGTERM) as last resort

### Time-Based Checks (`timeCheckAndCloseProgram`)

- Checks if current NY time exceeds `scriptEndTime` (default 15:45)
- If past end time: closes all positions and exits

## Trade Cooldown System

- After any position close, `trade_time_dict["{symbol}_{right}"]` records `datetime.now()`
- Before new trade: checks `(now - last_trade_time).total_seconds() < TRADE_COOLDOWN_SECONDS`
- Default cooldown: **610 seconds** (~10 minutes) between same symbol+right trades
- Prevents rapid re-entry after exits
