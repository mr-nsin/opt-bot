# Log Analysis: Why No Buy/Sell Signals & How Logs Help

This document summarizes **issues found in trading-engine logs** (e.g. `trading-engine/logs/bot_2026-02-24.log`), **why no signals are generated**, and **how logging was improved** so you can see end-to-end system health and signal flow.

---

## 1. Issues Found in the Log (bot_2026-02-24.log)

### 1.1 TWS / IBKR data problems (root cause of no signals)

| Code | Message | Effect |
|------|---------|--------|
| **162** | Historical Market Data Service error: **Trading TWS session is connected from a different IP address** | Historical bar requests fail. Strategy needs bars for SuperTrend, engulfing, ATR. No bars → no indicators → no signals. |
| **10197** | **No market data during competing live session** | All 9 underlyings (AAPL, AMD, AMZN, BABA, MSFT, NVDA, QQQ, SPY, TSLA) get this. **No live tick data** is delivered for stocks. |
| **200** | The contract description specified for AAPL is **ambiguous** | Option/contract resolution can fail for some symbols. |
| **322** | **Duplicate ticker id** | Same ticker id used for multiple option subscriptions; TWS rejects duplicates. |

### 1.2 Underlying price = -1

The log shows for every symbol:

- `AAPL UNDERLYING PRICE IS = -1`
- `AMD UNDERLYING PRICE IS = -1`
- … (same for all symbols)

Strike selection and option subscription use the underlying price. With **-1**, the strategy cannot pick valid strikes or price options correctly.

### 1.3 Market data farm / connectivity (informational)

- Codes **2103 / 2104 / 2105 / 2106 / 2157 / 2158**: Market data farm / HMDS / Sec-def “connection is broken” or “OK”. These are normal reconnection messages; they become a problem only if they persist and no data flows.
- **1100**: Connectivity between IBKR and TWS lost.
- **1102**: Connectivity restored.

---

## 2. Why There Are No Buy/Sell Signals

End-to-end flow:

1. **TWS** must send **live ticks** for **STK** (stocks). The bot’s `event_processor` only runs signal logic on **STK** ticks.
2. Because of **10197** (“No market data during competing live session”), **no (or almost no) stock ticks** are received. So the event queue gets very few STK events.
3. **Historical bars** are requested for SuperTrend, engulfing, ATR. Because of **162** (different IP / historical data error), **bar requests fail**. So `get_bars()` returns None or insufficient data → `getCallPutEngulfCheck()` returns no trade (e.g. “notrade” / “no engulf match”).
4. Even when some ticks exist, **underlying price = -1** means strike selection and option pricing are invalid, so the rest of the pipeline (delta/volume, option tick, place order) does not complete.

So:

- **No/few STK ticks** (10197) + **no historical bars** (162) + **underlying price -1** → **no signal generation** and **no trades**.

### What you need for signals to run

- **Same IP as TWS:** Resolve “Trading TWS session is connected from a different IP address” (e.g. run bot and TWS on same machine or same VPN, or fix IBKR session settings).
- **No competing live session:** Fix “No market data during competing live session” (only one live session per account for that data, or use a different client id / data type).
- After that, you should see **underlying prices &gt; 0**, **historical bars** in logs, and then **SIGNAL_CHECK** / **SIGNAL_CANDIDATE** / **SIGNAL_GENERATED** / **TRADE_PLACED** when the strategy triggers.

---

## 3. Log Improvements (What Was Added)

### 3.1 Signal and trade lifecycle (BOT.py)

- **SIGNAL_CHECK_START: symbol=X**  
  When the event processor starts checking a stock tick for a signal (entering `getCallPutEngulfCheck` path).

- **SIGNAL_CANDIDATE: symbol=X direction=CALL|PUT reason=...**  
  When engulf/SuperTrend says there is a candidate (CALL or PUT). Next step is delta/volume and algo check.

- **NO_SIGNAL: symbol=X reason=...**  
  When there is no signal. Reasons include: `no_engulf_match`, `not_enough_candles`, `no_historical_bars`, etc.

- **SIGNAL_GENERATED: BUY|SELL direction symbol=X strike=Y expiry=Z (attempting trade)**  
  When the bot **attempts** a trade (entering `takeTrade`). So you see every real trade attempt even if it later fails (spread, price, etc.).

- **TRADE_PLACED: symbol=X right=Y strike=Z expiry=W**  
  When an order is **actually placed** successfully (after `placeOrder` succeeds).

- **NO_TRADE: symbol=X reason=...**  
  When `checkConditionsAndTrade` finishes without placing (e.g. delta/volume not matched, algo not matched, cooldown, price condition not matched).

These lines make it easy to grep for:

- `SIGNAL_GENERATED` / `TRADE_PLACED` → see all signal attempts and fills.
- `NO_SIGNAL` / `NO_TRADE` → see why no trade (no bars, no engulf, delta/volume, etc.).

### 3.2 Pipeline health (trading_engine + data_status)

- **PIPELINE_HEALTH** (about every 60 seconds) is emitted as a **log message** and summarizes:
  - **event_queue_size** – number of events waiting. If 0 for long periods and no signals, likely no ticks (e.g. 10197).
  - **symbols_with_valid_price** – how many configured symbols have at least one valid underlying price (last/bid/ask). If 0, you will see “No underlying prices yet – check TWS market data subscriptions.”
  - **data_feed_started** – whether the data feed and event processors have been started.
  - **TWS_connected** – whether the engine thinks TWS is connected.

So in one place you can see:

- Is the queue getting ticks? (queue size)
- Do we have underlying prices? (symbols_with_valid_price)
- Is the feed and TWS connection up? (data_feed_started, TWS_connected)

### 3.3 How to use logs to verify end-to-end

1. **Start the bot** – confirm “Data feed and strategies started” and “Starting event processor #1”, etc.
2. **Check PIPELINE_HEALTH** – `symbols_with_valid_price` should become &gt; 0 and stay; `event_queue_size` should sometimes &gt; 0 when market is open and data is allowed.
3. **Check for SIGNAL_CHECK_START / SIGNAL_CANDIDATE** – confirms STK ticks are being processed and engulf/SuperTrend are running.
4. **If you see NO_SIGNAL** – use `reason=` to see why (no bars, not enough candles, no engulf, etc.).
5. **If you see SIGNAL_GENERATED but no TRADE_PLACED** – look for “Order Not Placed … Because =” and “NO_TRADE: … reason=…” to see spread/price/cooldown/algo reasons.
6. **If you never see SIGNAL_CHECK_START** – event queue is not getting STK ticks; focus on TWS/IBKR (10197, 162, subscriptions, IP, competing session).

---

## 4. File locations

- **Bot / strategy logs:** `BOT.py` (event_processor, getCallPutEngulfCheck, checkConditionsAndTrade, takeTrade, placeOrder).
- **Pipeline health log:** `trading-engine/engine/trading_engine.py` (`_emit_data_status` + 60s PIPELINE_HEALTH).
- **Log file:** `trading-engine/logs/bot_YYYY-MM-DD.log` (and any UI log viewer that consumes the same stream).

## 5. Why signals seemed to stop after Rust/Tauri conversion

See **docs/SIGNAL_FLOW_BOT_VS_ENGINE.md** for a full comparison. In short:

- **Bug (fixed):** The engine main loop was consuming and discarding events from the queue whenever `_data_feed_started` was False (i.e. during the whole of `init_data_feed()` and startup). So ticks that arrived during that window were never seen by BOT’s event_processor. The engine no longer drains the queue before the BOT processors start.
- **Your log:** The main reason there were no signals in `bot_2026-02-24.log` was **TWS/IBKR** (Code 10197 = no market data, Code 162 = historical data from different IP, underlying price -1). Fixing the queue-draining bug ensures that when ticks do arrive during startup, they are not thrown away.
