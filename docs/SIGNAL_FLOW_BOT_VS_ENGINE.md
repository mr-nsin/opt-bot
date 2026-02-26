# Signal Generation: Original BOT vs Rust/Tauri Engine

This document compares how **signals were generated in the original BOT.py flow** (e.g. GUI → `BOT.start_trading(data)` → `main_call`) vs **the Rust/Tauri sidecar flow** (Tauri → sidecar → `trading_engine.start(config)`), and why signals can appear to "stop" after the conversion.

---

## 1. Original BOT flow (e.g. GUI / standalone)

1. **main_call(data)** runs in a separate process.
2. **Config from `data`:** `stockList`, `stock_list_to_trade`, `fetchValue`, `candleTime`, deltas, risk, etc. are set from `data` (e.g. GUI’s config).
3. **Queue and client:** `event_queue = Queue()`, then `client = init_api_client(_event_queue=event_queue, _order_mgr=order_mgr)`. The TWS client holds a reference to this queue.
4. **Connect:** `start_client(_client=client)` → client connects; TWS reader thread starts in `connectAck()`.
5. **Initialization sequence:**
   - `init_order_requests()` (reqOpenOrders, reqPositions, reqPnL)
   - `time.sleep(2.0)`
   - `init_data_feed()` — subscribes underlyings (STK/FUT), requests historical bars, builds strikes, subscribes options. Uses global `stockList`. Can take tens of seconds.
   - `dataStrike = fetch_all_strike_expiries()`
   - `synchronize_orders()`
   - **`processors = init_start_event_processors()`** — starts N threads running `BOT.event_processor(event_queue, i)`.
   - **`client.initialization_done = True`** — from this point, `tickPrice()` in `tws_api_client` puts ticks into `event_queue` (tickType 4 for all, tickType 1 for OPT only).
6. **Consumers:** Only the **BOT event_processor** threads read from `event_queue`. So any tick that arrives (before or after `initialization_done`) and is put in the queue is eventually processed by `event_processor` → `getCallPutEngulfCheck` → `checkConditionsAndTrade` → signal/trade.

**Important:** There is **no other consumer** of `event_queue`. Ticks that arrive during `init_data_feed()` sit in the queue until the processors start, then get processed.

---

## 2. Rust/Tauri engine flow (sidecar)

1. **Engine started:** `trading_engine.start(config)` runs in the sidecar process. Config comes from the frontend (e.g. `stock_list_to_trade`, same keys as BOT).
2. **Queue and client:** Engine creates `self._event_queue = Queue()` and `self._client = TwsApiClient(..., event_queue=self._event_queue, ...)`. Same `tws_api_client` class; same `tickPrice()` logic that does `event_queue.put({"tick": tick})` when `initialization_done` is True.
3. **Connect:** `_try_connect_tws()` in the engine loop; when `isConnected()`, `self.connected = True`.
4. **When connected:** `_start_data_feed_and_strategies()` runs **once**:
   - Sets BOT globals: `BOT.event_queue = self._event_queue`, `BOT.stockList = stock_list`, `BOT.stock_list_to_trade`, etc.
   - `BOT.init_order_requests()`
   - `time.sleep(2.0)`
   - `BOT.init_data_feed()` — same as original (underlyings, historical, strikes, options). Can take tens of seconds.
   - `BOT.dataStrike = BOT.fetch_all_strike_expiries()`
   - `BOT.synchronize_orders()`
   - **Starts N threads:** `threading.Thread(target=BOT.event_processor, args=(self._event_queue, i))` — same as original.
   - **`self._client.initialization_done = True`**
   - **`self._data_feed_started = True`**
5. **Engine main loop (_run_engine):** Runs in a separate thread. Every ~50 ms it does:
   - If **not** `_data_feed_started` and queue non-empty: **`event = self._event_queue.get(...)`** and **`self._process_event(event)`** (which only logs the event, no signal logic).
   - If `_data_feed_started`: it does **not** read from the queue; only BOT event_processor threads do.

---

## 3. Critical difference (bug)

- **Original BOT:** Nothing else reads from `event_queue`. All ticks that are put in the queue (after `initialization_done`) are processed by BOT’s `event_processor`.
- **Engine:** While `_data_feed_started` is **False** (i.e. during the whole of `_start_data_feed_and_strategies()`, including the long `init_data_feed()`), the **engine loop** is still running and does:
  - `if not self._data_feed_started and self._event_queue and not self._event_queue.empty(): event = self._event_queue.get(...); self._process_event(event)`  
  So it **removes events from the queue and only logs them**. It does **not** run any signal logic.

So in the engine flow, **every tick that arrives before `_data_feed_started` is set to True is consumed by the engine and discarded** (only a debug log). That can be a long window (e.g. 20+ seconds of `init_data_feed()`). If TWS sends ticks during that time, they are lost for signal generation.

After `_data_feed_started` is True, behavior matches the original: only BOT event_processor threads consume the queue, so no more discarding.

**Fix:** Do **not** consume the event queue in the engine loop when `_data_feed_started` is False. Let events accumulate; when BOT event processors start, they will process them. (Implemented: remove the `get`/`_process_event` block for `not _data_feed_started`.)

---

## 4. Why “signals stopped” in your run (log bot_2026-02-24)

Even with the above fix, your log shows:

- **Code 10197:** “No market data during competing live session” for all underlyings → **no (or almost no) live ticks** are delivered to the client. So the queue gets very few STK ticks regardless of who consumes it.
- **Code 162:** “Trading TWS session is connected from a different IP address” → **historical bar requests fail** → no candles for SuperTrend/engulfing/ATR → `getCallPutEngulfCheck` returns no trade.
- **Underlying price = -1** for all symbols → strike selection and option logic cannot run correctly.

So in that run, **signals did not generate mainly because of TWS/IBKR data (10197, 162, -1 prices), not only because of the Rust/Tauri conversion.** The conversion did introduce one behavioral bug (engine draining the queue before processors start); fixing it ensures that when ticks do arrive during startup, they are not thrown away.

---

## 5. Flow equivalence (after fix)

| Step | Original BOT | Engine (sidecar) |
|------|----------------|------------------|
| Queue | Created in main_call, passed to client | Created in engine, passed to client |
| Client | Same TwsApiClient, same event_queue | Same TwsApiClient, same _event_queue |
| Ticks into queue | tickPrice() when initialization_done | Same (initialization_done set by engine) |
| Who consumes queue | Only BOT event_processor threads | Only BOT event_processor threads (after fix: engine does not consume) |
| BOT globals | Set from data before client/init | Set from engine config in _start_data_feed_and_strategies |
| init_data_feed | Same BOT.init_data_feed(), same stockList | Same, stockList from engine config |
| Event processors | init_start_event_processors() with same queue | Same BOT.event_processor(self._event_queue, i) |

So after the fix, the **signal path** (queue → event_processor → getCallPutEngulfCheck → checkConditionsAndTrade → takeTrade/placeOrder) is equivalent; any remaining “no signals” should be explained by **data conditions** (no ticks, no bars, -1 prices) and TWS/IBKR setup (same IP, no competing session, etc.), not by the Rust/Tauri architecture.
