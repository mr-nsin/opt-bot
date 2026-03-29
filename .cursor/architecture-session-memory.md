# Architecture session memory — QuantDrift OPT_BOT

Use this file across Cursor sessions. There is no `cursor.md`; canonical pointers are `CLAUDE.md` (repo root), `.cursor/architecture.md` (legacy PyQt stack), and this note for the **shipping app**.

## Runtime stack (current product)

| Layer | Tech | Role |
|-------|------|------|
| UI | React + TS + Vite (`src/`) | Dashboard, settings, logs, license gate |
| Shell | Tauri 2 + Rust (`src-tauri/`) | Window, licensing, spawns Python sidecar |
| IPC | JSON-RPC lines on stdio | `trading-engine/protocol/` |
| Engine | Python 3.12 venv (`trading-engine/`) | `main.py` → `TradingEngine` → `BOT.py`, `order_manager`, `tws_api_client` |
| Broker | IBKR TWS / Gateway | Socket API (`ibapi`) |

**Config load order** (after merge from `mac-app-dmg`): project `config.json` paths → app-data `config.json` → bundled resource → legacy → embedded `include_str!`.

## Core execution path

1. **Ticks** → `TwsApiClient` callbacks → `event_queue` → `BOT.event_processor` (multiple worker threads).
2. **Stock tick** → `getCallPutEngulfCheck` (SuperTrend and/or engulfing) → `checkConditionsAndTrade`.
3. **Option tick** (same queue) → `OrderManager.check_and_close_position` when `tick.active_order` set — **TP/SL on option stream**.
4. **Backup** → `monitor_positions_loop` → `check_exit_conditions` per TWS position (needs `entry_orders_cache` + tick or `get_options_data` fallback).

## Key files

- `BOT.py` — signals, `takeTrade`, `placeAndVerifyOrder`, `checkConditionsAndTrade`, globals.
- `order_manager.py` — `check_take_profit`, `check_stop_loss`, `close_position`, caches.
- `tws_api_client.py` — IB connection, subscriptions, `get_open_position` (first match per symbol).
- `common.py` — `OptionOrder`, loguru `logs/bot_DATE.log` (**relative to process CWD**).
- `trading-engine/engine/trading_engine.py` — sidecar lifecycle, TWS connect, BOT bridge.

## Known architecture issues / limits

1. **`get_open_position(symbol)`** returns the **first** non-zero position for that underlying — not strike/expiry aware. Multi-leg same symbol can confuse “already in position” logic.
2. **`get_entry_order(symbol, right)`** returns **first** matching managed order — ordering depends on cache iteration.
3. **TP/SL** require **option** bid/ask/last; missing ticks → monitor fallback; still no match if no `entry_order` in cache (e.g. manual TWS trade).
4. **No cross-machine sync** — each app instance is independent (see below).
5. **`.cursor/architecture.md`** still describes **PyQt `GUI.py`**; production UI is **Tauri/React**.

---

## Trade placement & SL/TP (authoritative summary)

### Initial levels at placement (`takeTrade` in `BOT.py`)

- `tradePrice` = entry (bid for wide spread LMT, else ask/MKT rules).
- `atr_risk_cap` = `0.9 * underlying_ATR` (floor when ATR tiny).
- `base_dist` = `ATR_VALUE * atr` (default 0.99 × ATR), then `atr_dist = min(base_dist, atr_risk_cap)`.
- **Take-profit (initial target)** `profitPrice` = `tradePrice + atr_dist` (long CALL premium goes up).
- **Stop-loss** `auxPrice` = `tradePrice - atr_dist`.
- **Caps**: `max_tp_price` / `min_sl_price` bound trailing TP and widen-floor SL vs entry ± `atr_risk_cap`.
- If implied TP gain **> 20%** of premium → TP capped to **+15%** on premium (`profitPrice = tradePrice * 1.15`).

`OptionOrder` stores `profit_price`, `current_profit_price` (starts = initial TP), `stoploss_price` (= aux), `profit_increment` from config (`PROFIT_INCREMENT`, e.g. 0.03), `profit_trigger` (bool), `max_tp_price`, `min_sl_price`.

### Trailing take-profit (`OrderManager.check_take_profit`)

**Long (BUY option — typical long CALL/PUT premium long):**

- `exit_price` = `max(bid, last)` when both > 0 (what you’d get selling).
- While price **rises**: if `exit_price >= current_profit_price` → set `profit_trigger=True`, move target **up**: `current_profit_price = exit_price + profit_increment`, capped by `_cap_trailing_tp` vs `max_tp_price`.
- **Close** when trailing active and price **pulls back**: `exit_price < (current_profit_price - profit_increment)` → `close_position`.

**Numeric long example** (increment $0.03): Entry $1.50, initial `current_profit_price` = first TP e.g. $1.60. Price hits $1.60 → trail → `current_profit_price` = $1.63. Hits $1.65 → $1.68. Drops to $1.64 → $1.64 < $1.68 - 0.03 = $1.65? (need strict inequality) — closes when exit drops **below** trail minus one increment.

**Short side** (`order_side == "SELL"`): uses ask/min(last); trail when exit falls; close when exit rises by increment above trail (short premium logic).

### Stop-loss (`check_stop_loss`)

- Long: `exit_price` = bid (else last). Hit if `exit_price <= sl_price` where `sl_price = stoploss_price`, floored by `min_sl_price` if set.
- Short: `exit_price` = ask; hit if `exit_price >= sl_price`.
- **SL does not trail** in code — fixed from entry calculation unless you change order in DB manually.

### Why some positions don’t close when others do

- Each leg needs its own **filled** `OptionOrder` in `entry_orders_cache` and a **valid** option tick (`order_id_tick_lookup` or monitor’s `get_options_data` fallback).
- If `exit_placed` already true, or `order_status != "filled"`, checks return early.
- Invalid quotes (`bid`/`ask`/`last` -1) → warnings, no close.
- TWS position **without** matching bot entry (manual trade) → “no matching entry order” → **no automated TP/SL**.
- `tick.busy` lock — rare contention under heavy load.
- Parallel `monitor_positions_loop` — one position’s exception doesn’t stop others; check logs per symbol.

### Second signal: same symbol, same expiry, same direction

1. **`client.get_open_position(stockName)`** — any non-zero position on that **underlying** with same **right** (C/P) → **`positionAlreadyPresent`** → **no new trade**.
2. Else **`order_mgr.get_entry_order(stockName, right=...)`** with `active` → **`orderAlreadyPresent`** (pending working order).
3. **`placeAndVerifyOrder`** also blocks duplicate via same-symbol/right/expiry lock and active order on tick.
4. After a **close**, **`check_TRADE_COOLDOWN_SECONDS`** enforces **`TRADE_COOLDOWN_SECONDS`** per **`symbol_side`** (`AAPL_C`) from last **close** time — new signal same day may be skipped until cooldown expires.

So: **you do not stack two bot-opened same-direction same-underlying positions** while one is open; after close, cooldown may delay re-entry.

### Multiple machines — why trades differ

- **Separate processes**: each QuantDrift + sidecar has its own RNG timing, thread scheduling, and **local** SQLite `db/orders.db` / caches.
- **IBKR `clientId`**: must differ per connection; same account can have multiple API clients — **fills and subscriptions are per client**, not mirrored between apps.
- **No shared signal bus**: SuperTrend/engulfing use **local** bar/tick stream; micro-delays → different signal flips.
- **Config drift**: different `config.json` / UI settings → different symbols, deltas, cooldowns.
- **License / Start Trading**: one machine may not be running or licensed.

**Same fills on two machines** would require shared strategy state and coordinated clientIds — **not implemented**.

---

*Last updated: session maintenance — align with `BOT.py` `takeTrade`, `order_manager.py` TP/SL, `checkConditionsAndTrade`.*
