# Why Signals and Trades Don’t Run When “Start Trading” Is Clicked (Tauri + Rust UI)

## Summary

When you click **Start Trading** in the Tauri UI, the **trading-engine sidecar** starts and is supposed to reuse **BOT** logic (data feed, signals, orders). In practice, **BOT is never fully initialized** because **`main_call()` is never run**. All config-dependent **BOT globals** are set only inside `main_call()`. The TradingEngine sets only a subset of them, so the signal/trade path hits **missing or wrong globals** and either fails (NameError) or never passes checks. Below is a direct comparison and the exact gaps.

---

## 1. Flow comparison

| Step | BOT.py (standalone) | Tauri “Start Trading” (sidecar) |
|------|----------------------|----------------------------------|
| **Entry** | Run `BOT.start_trading(data)` → new **Process** running `main_call(data)`. | Rust `start_trading(config)` → `manager::spawn_sidecar()` → `manager::send_request(START_TRADING, { config })` → sidecar runs `TradingEngine.start(config)`. |
| **Config** | `main_call(data)` re-reads `config.json` and sets **all** BOT globals from `data` / `fileData` (IP, PORT, ATR_CHECKS, PROFIT_INCREMENT, TRADE_COOLDOWN_SECONDS, etc.). | Config comes from UI (Rust/React). TradingEngine writes `config.json` and **only sets a subset** of BOT globals; **never runs `main_call()`**. |
| **TWS** | `init_api_client()` → `start_client(client)` (client thread runs `EClient.run()`). TWS callbacks (e.g. `connectAck`) also start `run()` in tws_api_client. | TradingEngine `_init_tws_client()` → `connect()`; `run()` is started by **connectAck** in tws_api_client. So TWS message loop **does** run. |
| **Data feed** | Main loop: `init_order_requests()` → `init_data_feed()` → `dataStrike = fetch_all_strike_expiries()` → `synchronize_orders()` → `init_start_event_processors()` → `client.initialization_done = True`. Repeats every cycle if disconnect. | **Once** when `connected and not _data_feed_started`: `_start_data_feed_and_strategies()` → set BOT globals → `BOT.init_order_requests()` → `BOT.init_data_feed()` → `BOT.dataStrike = BOT.fetch_all_strike_expiries()` → `BOT.synchronize_orders()` → start `BOT.event_processor` threads → `client.initialization_done = True`. |
| **Event loop** | Multiple `event_processor(event_queue, i)` threads; each does `event_queue.get()` → if OPT tick with `active_order`: exit checks; if STK tick: `getCallPutEngulfCheck` → `checkConditionsAndTrade`. | Same: TradingEngine starts `BOT.event_processor(self._event_queue, i)` threads. So **same** event consumption and signal logic **if** BOT globals were set. |
| **Signals** | `getCallPutEngulfCheck(symbol)` uses `client.get_bars()`, `candleTime`, `signal_dict`, `indi`. All set in `main_call` or by TradingEngine. | Same code path. **Fails or misbehaves** because globals used in `checkAlgoAndTrade` / `checkConditionsAndTrade` / `takeTrade` / `placeOrder` are **not** set (see below). |
| **Trades** | `checkConditionsAndTrade` → delta/volume, cooldown (`TRADE_COOLDOWN_SECONDS`), `checkAlgoAndTrade` (ATR, VWAP, EMA) → `takeTrade` → `placeOrder`. Uses `PROFIT_INCREMENT`, `ORDER_EXPIRY_TIMER`, `USE_TIMER_IN_ORDER`, `ATR_VALUE`, `MAX_CONTRACT_AMOUNT`, etc. | Same code path. **Crashes or skips** when it hits unset globals (e.g. `TRADE_COOLDOWN_SECONDS`, `PROFIT_INCREMENT`, `ATR_CHECKS`, `ATR_VALUE`). |

So structurally the Tauri path **does** start the same BOT data feed and event processors, but **BOT is only partially initialized**.

---

## 2. BOT globals: what `main_call()` sets vs what TradingEngine sets

These are the globals that **BOT.main_call()** sets from config (and that the signal/trade path uses), and whether **TradingEngine** sets them.

| Global | Used in | Set in main_call? | Set in TradingEngine? |
|--------|--------|--------------------|------------------------|
| client, order_mgr, event_queue | init_data_feed, event_processor | Yes (via init) | **Yes** |
| stockList, stock_list_to_trade, fetchValue, candleTime | init_data_feed, getCallPutEngulfCheck, get_bars | Yes | **Yes** |
| SUB_ACCOUNT_ID, tradeExpiry_val, spy_qqq_tradeExpiry | checkConditionsAndTrade, takeTrade, timeCheckAndCloseProgram | Yes | **Yes** |
| CALL_DELTA_CHECK, PUT_DELTA_CHECK, VOLUME_CHECK | checkConditionsAndTrade | Yes | **Yes** |
| profit_amount_day, loss_amount_day | checkAlgoAndTrade → timeCheckAndCloseProgram | Yes | **Yes** |
| signal_dict, trade_time_dict | getCallPutEngulfCheck, checkConditionsAndTrade | Yes | **Yes** |
| **TRADE_COOLDOWN_SECONDS** | check_TRADE_COOLDOWN_SECONDS, placeAndVerifyOrder, checkConditionsAndTrade | Yes (`fileData["distance_between_trade"]`) | **No** → NameError or wrong value |
| **PROFIT_INCREMENT** | placeOrder (OptionOrder), takeTrade logs | Yes (`fileData["profit_increment"]`) | **No** → NameError in placeOrder |
| **ATR_CHECKS** | checkAlgoAndTrade | Yes | **No** → NameError in checkAlgoAndTrade |
| **ATR_VALUE** | takeTrade (profit/stop from ATR) | Yes | **No** → NameError in takeTrade |
| **ORDER_EXPIRY_TIMER** | placeOrder (getOrderExpiryTime, GTD) | Yes | **No** |
| **USE_TIMER_IN_ORDER** | placeOrder (GTD order) | Yes | **No** |
| **MAX_CONTRACT_AMOUNT** | takeTrade (option price filter) | Yes | **No** |
| **EXPIRY, useAmount, stockListDict, dataInFile** | Various | Yes | **No** (partially: stock_list_to_trade only) |
| **MARKET_START_TIME, startTime, endTime** | timeCheckAndCloseProgram | Yes | **No** |
| **VWAP_ON_OFF** | checkAlgoAndTrade → checkVWAPValue | Yes | **No** |
| **ACTIVE_VOLUME, SHARE_VOLUME, BODY, perDayTrades, USE_DIFF_EXPIRY_INDEX** | Config / future use | Yes | **No** |

So: **signals can fail in `checkAlgoAndTrade` (ATR_CHECKS, VWAP, etc.), and trades can fail in `checkConditionsAndTrade` (TRADE_COOLDOWN_SECONDS) or in `takeTrade`/`placeOrder` (PROFIT_INCREMENT, ATR_VALUE, ORDER_EXPIRY_TIMER, USE_TIMER_IN_ORDER, MAX_CONTRACT_AMOUNT).** The first time one of these is read, you get **NameError** if the global was never set.

---

## 3. Logic comparison (side by side)

### 3.1 Startup

- **BOT standalone**  
  - Process runs `main_call(data)`.  
  - Loads config from `data` / re-reads `config.json`, sets **all** globals.  
  - Creates client, order_mgr, event_queue, starts client thread.  
  - Loop: init_order_requests → init_data_feed → fetch_all_strike_expiries → synchronize_orders → init_start_event_processors → `initialization_done = True`.  

- **Tauri sidecar**  
  - `TradingEngine.start(config)` in sidecar.  
  - Writes `config.json`, sets only **some** BOT globals.  
  - Creates client, order_mgr, event_queue; TWS `connectAck` starts `run()`.  
  - **Once** when connected: same init_order_requests → init_data_feed → fetch_all_strike_expiries → synchronize_orders → start event_processor threads → `initialization_done = True`.  
  - **main_call() is never run** → many globals never set.

### 3.2 Data flow

- **Both**  
  - TWS → tickPrice/tickSize/historicalData → tick_cache / history_cache.  
  - When `initialization_done`: option/stock ticks → event_queue.  
  - `get_bars()` reads from history_cache.  
  So data path is the same; missing globals affect **how** that data is used, not whether it arrives.

### 3.3 Signal path

- **Both**  
  - event_processor gets **STK** tick → `getCallPutEngulfCheck(symbol)` → `client.get_bars(stock, candleTime, limit)` → SuperTrend or engulfing rules → update `signal_dict`, return (conditionMatch, right, stock, strength).  
  - Then `checkConditionsAndTrade((dataEngulf, dataStrike), tick)`.  

- **Difference**  
  - In `checkConditionsAndTrade` → `checkAlgoAndTrade` we use **ATR_CHECKS**, **VWAP_ON_OFF**. If these are not set → **NameError** or wrong behavior. So **signals may never complete successfully** in the Tauri flow.

### 3.4 Trade path

- **Both**  
  - Strikes from getStockNearStrikes; delta/volume from get_delta_volume; cooldown check; checkAlgoAndTrade (ATR, VWAP, EMA); then takeTrade → placeOrder.  

- **Difference**  
  - **TRADE_COOLDOWN_SECONDS**: used in check_TRADE_COOLDOWN_SECONDS and placeAndVerifyOrder. Unset → NameError.  
  - **takeTrade**: uses **ATR_VALUE**, **MAX_CONTRACT_AMOUNT**. Unset → NameError.  
  - **placeOrder**: uses **PROFIT_INCREMENT**, **ORDER_EXPIRY_TIMER**, **USE_TIMER_IN_ORDER**. Unset → NameError.  
  So **trades either crash or never get placed** in the Tauri flow.

### 3.5 Exit path

- **Both**  
  - OPT tick with active_order → `order_mgr.check_and_close_position(tick)` → check_take_profit, check_stop_loss → close_position.  
  - No dependency on the missing globals above for **exit** logic. So exits can work once an order was placed (e.g. if you fix entry and place a trade).

---

## 4. Root cause (why signals/trades don’t run from UI)

1. **`main_call()` is never executed in the sidecar**  
   All config-derived BOT globals are set only in `main_call()`. The Tauri flow only runs `TradingEngine.start()` and then `_start_data_feed_and_strategies()`, which sets a subset of globals.

2. **TradingEngine sets only part of the required BOT state**  
   It sets: client, order_mgr, event_queue, stockList, stock_list_to_trade, fetchValue, candleTime, SUB_ACCOUNT_ID, tradeExpiry_val, spy_qqq_tradeExpiry, CALL_DELTA_CHECK, PUT_DELTA_CHECK, VOLUME_CHECK, profit_amount_day, loss_amount_day, signal_dict, trade_time_dict.  
   It does **not** set: **TRADE_COOLDOWN_SECONDS**, **PROFIT_INCREMENT**, **ATR_CHECKS**, **ATR_VALUE**, **ORDER_EXPIRY_TIMER**, **USE_TIMER_IN_ORDER**, **MAX_CONTRACT_AMOUNT**, VWAP_ON_OFF, startTime, endTime, and others.

3. **First use of an unset global → NameError**  
   So the first time a signal passes the engulf check and hits `checkAlgoAndTrade` (ATR_CHECKS) or `checkConditionsAndTrade` (TRADE_COOLDOWN_SECONDS) or `takeTrade` (ATR_VALUE, MAX_CONTRACT_AMOUNT) or `placeOrder` (PROFIT_INCREMENT, ORDER_EXPIRY_TIMER, USE_TIMER_IN_ORDER), the process can crash or the thread can log an exception and skip the trade. Result: **no signals/trades when starting from the Tauri “Start Trading” button**.

4. **Empty symbol list**  
   If the UI sends `stock_list_to_trade: {}`, TradingEngine skips the data feed and never starts event processors (“No symbols in stock_list_to_trade; skipping data feed”). So no symbols → no signals/trades regardless of globals.

---

## 5. Fix: set all required BOT globals in TradingEngine

In **`trading-engine/engine/trading_engine.py`**, inside **`_start_data_feed_and_strategies()`**, after the existing BOT global assignments (e.g. after `BOT.trade_time_dict = {}`), add the same globals that **main_call()** sets from config, using `self.config` and (for keys that come from `fileData` in BOT) the same keys you already write in `to_bot_config_dict()`:

```python
# --- Required for checkAlgoAndTrade, takeTrade, placeOrder (same as main_call) ---
BOT.TRADE_COOLDOWN_SECONDS = int(getattr(self.config, "distance_between_trade", 610))
BOT.PROFIT_INCREMENT = float(getattr(self.config, "profit_increment", 0.03))
BOT.ATR_CHECKS = float(getattr(self.config, "atr_checks", 0.047))
BOT.ATR_VALUE = float(getattr(self.config, "atr_value", 0.99))
BOT.ORDER_EXPIRY_TIMER = int(getattr(self.config, "order_expiry_timer", 15))
BOT.USE_TIMER_IN_ORDER = str(getattr(self.config, "use_timer_in_order", "ON"))
BOT.MAX_CONTRACT_AMOUNT = float(getattr(self.config, "max_contract_amount", 350.0))
BOT.VWAP_ON_OFF = str(getattr(self.config, "vwap_on_off", "ON"))
BOT.MARKET_START_TIME = str(getattr(self.config, "market_start_time", "19:00:00"))
BOT.scriptStartTime = str(getattr(self.config, "script_start_time", "0935"))
BOT.scriptEndTime = str(getattr(self.config, "script_end_time", "1545"))
# Optional: set more if BOT uses them (ACTIVE_VOLUME, SHARE_VOLUME, BODY, perDayTrades, USE_DIFF_EXPIRY_INDEX, EXPIRY, useAmount, stockListDict, dataInFile)
BOT.stockListDict = getattr(self.config, "stock_list_to_trade", None) or {s: "SMART" for s in stock_list}
BOT.dataInFile = len(stock_list)
BOT.EXPIRY = str(getattr(self.config, "expiry_to_trade", "next"))
BOT.useAmount = getattr(self.config, "stock_data", {}) or {k: {"amount": getattr(self.config, "max_contract_amount", 350)} for k in stock_list}
```

Also ensure the **UI sends a non-empty `stock_list_to_trade`** (and that Rust passes it through to the sidecar config) so the engine does not skip the data feed.

After these globals are set, the same BOT signal and trade logic that runs in the standalone process can run from the Tauri “Start Trading” flow without NameErrors and with correct thresholds.

---

## 6. Quick reference: two codebases

| Item | temp_OPT_BOT/opt-bot (BOT.py) | OPT_BOT (Tauri app) |
|------|-------------------------------|----------------------|
| **Purpose** | Standalone bot: run `BOT.main_call(data)` in a Process. | Desktop app: Tauri + React; “Start Trading” starts sidecar and sends START_TRADING to TradingEngine. |
| **Entry** | `start_trading(data)` → Process(target=main_call, args=(data,)).start() | Rust start_trading(config) → spawn_sidecar() → send_request(START_TRADING, { config }) → TradingEngine.start(config) |
| **Config** | main_call reads config and sets all BOT globals. | TradingEngine gets config from Rust/UI, writes config.json, sets only some BOT globals. |
| **BOT used?** | Yes; main_call runs fully. | Yes, but only init_data_feed + event_processor; main_call never runs → globals missing. |
| **Result** | Signals and trades run. | Signals/trades fail or crash until all required BOT globals are set in TradingEngine. |

This document and the suggested fixes explain why “Start Trading” from the Tauri + Rust UI does not produce signals or place trades and how to align the sidecar with BOT’s logic.
