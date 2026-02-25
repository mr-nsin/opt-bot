# QuantDrift – Complete Product Roadmap

This document is the **single source of truth** for what the app currently has, known issues, and planned features (backend, frontend, and a **unique modern UI** direction). It is intended for product and engineering alignment.

---

# PART I – What the App Currently Has

## 1.1 Backend (Rust / Tauri)

### Commands (invoke from frontend)

| Command | Module | Purpose |
|---------|--------|---------|
| `validate_license` | license | Validate stored license on load |
| `get_license_status` | license | Return valid, expiry, days_remaining, tier |
| `activate_license` | license | Activate with key + email; hardware-bound |
| `deactivate_license` | license | Clear license from storage |
| `get_hardware_id` | license | Return machine fingerprint (for support) |
| `start_trading` | trading | Spawn sidecar, send config, start trading |
| `stop_trading` | trading | Graceful stop; kill sidecar |
| `emergency_stop` | trading | Force kill sidecar, reset state |
| `get_trading_status` | trading | status, sidecar_running, connected_to_tws, daily_pnl, total_trades, winning_trades, losing_trades |
| `get_config` | config | Load trading config (project + app data merge) |
| `save_config` | config | Save to app data + project config.json (BOT.py format) |
| `get_settings` | config | Load app settings (theme, font_size, etc.) |
| `save_settings` | config | Save app settings |
| `get_settings_file` | config | Raw JSON from config/settings.json for Settings UI |
| `get_positions` | positions | All positions from app state |
| `close_position` | positions | Close by symbol (via sidecar) |
| `close_all_positions` | positions | Close all (via sidecar) |
| `get_logs` | logs | Log buffer (level/category/limit), chronological |
| `clear_logs` | logs | Clear in-memory log buffer |
| `get_log_stats` | logs | total, errors, warnings, info counts |
| `get_account_metrics` | trading | Last IBKR account summary snapshot (tag → number) |

### Managed state (Rust)

- **AppState** (Arc&lt;Mutex&lt;AppState&gt;&gt;): `config` (trading config + settings), `trading` (status, sidecar_running, connected_to_tws, daily_pnl, positions, trades_today, win/loss counts, last_signal, data_status), `license` (cached status). Loaded from disk on setup (config + settings).

### Events emitted to frontend

| Event | Source | Payload |
|-------|--------|---------|
| `trading:log_message` | Sidecar → Rust → emit | timestamp, level, category, message |
| `trading:pnl_update` | Sidecar → Rust (AppState) → emit | daily_pnl, unrealized_pnl, realized_pnl |
| `trading:account_metrics` | Sidecar → Rust (AppState) → emit | IBKR account summary (tag → number) |
| `trading:position_update` | Sidecar | position object |
| `trading:trade_executed` | Sidecar | trade record |
| `trading:trade_closed` | Sidecar | pnl, symbol, etc. |
| `trading:connection_status` | Sidecar | connected (bool) |
| `trading:engine_status` | Sidecar | status string |
| `trading:signal_detected` | Sidecar | signal data |
| `trading:data_status` | Sidecar | symbols, tick counts, stock_ticks, etc. |
| `sidecar-error` | Rust (stderr) | line string |
| `sidecar-terminated` | Rust | exit code |
| `license:validated` / `license:expired` | License flow | status |

### Plugins

- **tauri-plugin-shell** – Sidecar spawn, IPC (stdio).
- **tauri-plugin-fs** – File system (if used).
- **tauri-plugin-dialog** – Native dialogs.
- **tauri-plugin-process** – Process utilities.

### Config & license

- **Config load order:** Project `config.json` (BOT.py source of truth) → app data `config.json` → legacy `./config.json`. Optional merge from `config/settings.json` (symbols only when config has none; broker, UI, strategy merged).
- **Save:** App data + project `config.json` in BOT.py key format (stockListToTrade, IP, PORT, etc.).
- **License:** Hardware ID (hostname, CPU, memory, OS), AES-GCM encrypted `license.enc` in app data, HMAC-signed payload; validate on startup and when showing license UI.

---

## 1.2 Frontend (React + TypeScript)

### Pages & routes

| Route | Page | Content |
|-------|------|---------|
| `/` | DashboardPage | LiveStats, DataFeedStatus, TradingControls, TradeParameters, RiskManagement, ConnectionConfig, StockList, ActivityLog |
| `/analytics` | AnalyticsPage | PnLChart, EquityCurve, WinLossChart, PerformanceMetrics |
| `/positions` | PositionsPage | Open positions list, PositionHistory (today’s trades) |
| `/logs` | LogsPage | Filter (level, category), log list, auto-scroll, clear |
| `/settings` | SettingsPage | Theme, live trading toggle, notifications, update interval, show charts, config/settings.json display, broker from file, license (status, activate, deactivate) |

### Component structure

- **layout:** AppShell, Header (clock, P&L, trades, license, theme), Sidebar (nav + status: TWS, license, mode).
- **dashboard:** LiveStats (daily P&L, realized, unrealized, win rate, engine status), DataFeedStatus, TradingControls (Start/Stop/Emergency), TradeParameters (expiry, deltas, quantity, ATR, candle, cooldown, body mult), RiskManagement (profit target, loss limit, max trades, max contract $, trailing inc, P&L, trades count), ConnectionConfig (IP, port, account, client ID, order expiry, transmit), StockList (symbols + add/remove), **AccountSummary** (IBKR account summary: Net Liquidation, Cash, Buying Power, margins, Realized/Unrealized P&L, etc.), ActivityLog (last 50 logs).
- **analytics:** PnLChart (bar), EquityCurve (cumulative), WinLossChart, PerformanceMetrics (win rate, avg win/loss, etc.).
- **positions:** PositionRow, PositionHistory; close position / close all.
- **logs:** LogFilter, LogsPage (filtered list).
- **settings:** Cards for theme, toggles, config/settings.json (trading, strategy, broker, logging), license.
- **license:** LicenseGate (wrap app when unlicensed), LicenseStatus, LicenseInput.
- **common:** StatCard, StatusBadge, ThemeToggle, ModeToggle (Demo/Live), ConfirmDialog, ErrorBoundary, Toaster.
- **ui:** button, card, input, badge, switch, progress, separator (shadcn-style).

### State (Zustand)

- **configStore:** trading config (symbols, broker, params, risk, expiry, etc.), settings (theme, font_size, update_interval, show_charts, etc.); load on app init.
- **tradingStore:** status, sidecarRunning, connectedToTws, dailyPnl (realized, unrealized, total), totalTrades, winningTrades, losingTrades, lastSignal, todayTrades, dataStatus; updated via events.
- **logStore:** logs array, filterLevel, filterCategory, autoScroll; addLog (from event), setLogs (from API), clearLogs.

### Hooks & API

- **tauri-commands.ts:** config.get/save, getSettings, saveSettings, getSettingsFile; logs.get/clear/getStats; trading.start/stop/emergencyStop/getStatus; positions.getAll/close/closeAll; license.validate/getStatus/activate/deactivate/getHardwareId.
- **useTradingEvents:** subscribe to trading:pnl_update, connection_status, engine_status, trade_executed, trade_closed, data_status, log_message; update stores.
- **useLicense, useTheme, useTradingEngine:** license state, theme toggle, start/stop wiring.

### UI stack (current)

- **Framework:** React 19, TypeScript, Vite.
- **Styling:** Tailwind CSS, CSS variables for theming (light/dark).
- **Fonts:** Inter (sans), JetBrains Mono (mono); base font-size 14px, clamp 12–24 from settings.
- **Theme:** Light (gray/blue tint) and dark (slate/blue); primary blue (220 90% 56% / 217 92% 65%); sidebar dark; success/warning/destructive standard.
- **Patterns:** Cards (lighter: border/70, shadow-sm), grid layouts, badges, stat cards, scrollable log/activity; glass utility; live-dot animation for “trading active”; fade-up and dialog animations; custom scrollbar. Update intervals and "Started in X.Xs" shown on Dashboard and Controls.

---

## 1.3 Sidecar (Python trading-engine)

### Protocol

- **Transport:** JSON-RPC over stdio (one JSON object per line).
- **Commands (Rust → sidecar):** START_TRADING (config), STOP_TRADING, EMERGENCY_STOP, GET_STATUS, GET_POSITIONS, CLOSE_POSITION (symbol), CLOSE_ALL, UPDATE_CONFIG, PING.
- **Events (sidecar → stdout):** JSON with `{"type":"event","event":"<name>","data":{...}}`. Names: pnl_update, account_metrics, position_update, trade_executed, trade_closed, connection_status, engine_status, signal_detected, data_status, log (with level, category, message).
- **Responses:** JSON with id, result or error.

### Engine behavior

- **TradingEngine** (trading_engine.py): start(config) → init DB, order manager, TWS client; connect TWS; set BOT globals; run BOT.init_order_requests, init_data_feed, synchronize_orders; start event_processor threads. Main loop: reconnect if needed, sync connection state, start data feed once when connected, _emit_pnl_update, _emit_data_status every ~10s, drain event queue when feed not started.
- **TWS:** tws_api_client (root); connect; after managedAccounts: reqPnL (subscription kept open) → pnl_cache (daily, unrealized, realized); reqAccountSummary (All, 12 tags) → account_summary_cache; subscribe/get_data for STK/OPT/FUT; BOT.init_data_feed subscribes underlyings + options chain (STK only for options).
- **BOT.py:** Signal logic (SuperTrend, engulfing, ATR), strike selection, placeOrder, order_mgr; event_processor consumes tick queue; PnL watchdog thread (day limits).

### Data flow

- TWS → tick/position callbacks → tick_cache, positions, pnl_cache, account_summary_cache → engine reads caches and emits pnl_update (every loop), account_metrics (every 5s), data_status (every 10s) → sidecar stdout → Rust parses and emits to frontend → React stores and UI.

### Start Trading flow (why it takes time and what we show)

1. **User clicks Start Trading** → Frontend uses `tradingConfig` from configStore (loaded at app init). If not loaded, "Configuration not loaded" is thrown.
2. **Rust `start_trading(config)`** → If sidecar not running: **spawn_sidecar()** (main delay: Python process start + all imports: BOT, tws_api_client, order_manager, etc.). Then **send_request(START_TRADING, { config })** (writes to sidecar stdin; Rust does not wait for response).
3. **Sidecar** receives START_TRADING → **engine.start(config)** in a thread: parse config, init DB, order manager, TWS client, connect (with 0.2s pause), start engine loop. UI is already "Running" by then; TWS connection and data feed continue in background.
4. **UI:** Button shows "Loading config & engine…" while starting; after start completes, shows **"Started in X.Xs"** (time from click until Rust returns). Dashboard shows **"Updates: PnL ~1s · Account summary ~5s · Data status ~10s"** so users know refresh rates.

**Update intervals (documented in UI):**

| Data | Backend emit | Frontend display |
|------|--------------|------------------|
| PnL | Engine every ~50ms; frontend throttled to **1s** | Header, LiveStats, Risk; label: "PnL ~1s" |
| Account summary | Every **5s** | Account Summary card; label: "Account summary ~5s" |
| Data status | Every **10s** | DataFeedStatus; label: "Data status ~10s" |

### IBKR data shown in the UI (verified)

- **Daily PnL (from reqPnL):** TWS pushes `pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)` → `pnl_cache` (keys: daily, unrealized, realized). Engine emits `pnl_update` every loop (~50ms) when connected. Rust updates `daily_pnl` and emits `trading:pnl_update`. Frontend shows:
  - **Header:** P&L = `dailyPnl.total`
  - **LiveStats:** Daily P&L, Realized, Unrealized (all three from store)
  - **RiskManagement:** P&L progress vs profit target
  - **PerformanceMetrics (Analytics):** Net P&L
- **Account summary (from reqAccountSummary):** After `managedAccounts`, engine requests 12 tags: NetLiquidation, TotalCashValue, GrossPositionValue, BuyingPower, AvailableFunds, ExcessLiquidity, MaintMarginReq, InitialMarginReq, RealizedPnL, UnrealizedPnL, SettledCash, EquityWithLoanValue. Stored in `account_summary_cache`; engine emits `account_metrics` every 5s. Rust stores snapshot and emits `trading:account_metrics`; frontend **Account Summary (IBKR)** card on Dashboard shows all received tags (with labels and `formatCurrency`). `get_account_metrics` command returns last snapshot for reconnect/tab-focus refresh.

---

## 1.4 Config, License, Build

- **Config:** See §1.1; project config.json is source of truth for BOT; UI saves back in same format.
- **License:** See README and docs/LICENSE_SYSTEM.md; hardware-bound, encrypted store, expiry, deactivate.
- **Build:** Tauri 2, Vite build; Windows (NSIS + msi) and macOS (dmg + app) via GitHub Actions; trading-engine PyInstaller binary per platform in src-tauri/binaries/.

---

# PART II – Known Issues & Technical Debt

| Area | Issue | Severity |
|------|--------|----------|
| **PnL** | Engine was expecting per-account objects in pnl_cache; TWS uses flat dict. Fixed: _emit_pnl_update now handles flat daily/unrealized/realized and emits to frontend. | Fixed |
| **BOT.py** | TODOs: “MUST REMOVE FOLLOWING CODE” and commented blocks in checkConditionsAndTrade (around 1056, 1158). | Medium |
| **Config** | No strict validation of numeric ranges (deltas, quantity, risk limits) in Rust or UI before save. | Low |
| **Errors** | Some Tauri command errors may not surface as user-visible toasts; sidecar errors go to stderr and log. | Low |
| **Types** | Frontend sometimes uses `unknown` for config/settings file; Settings page uses type assertions. | Low |
| **Logs** | No persistence; buffer only in memory; clear on restart. | Low |
| **Performance** | UI hang on tab switch: **Partially fixed** – PnL throttled to 1s in frontend, lazy route loading, memo Header/Sidebar, virtualized Logs/ActivityLog. Remaining: optional page-level memo, further tuning if needed. | Low |
| **IBKR fetch timing** | Account info and P&L took several seconds to appear after Start Trading: **Fixed** – see §2.1 (IBKR fetch timing: deep analysis and fixes). | Fixed |

### 2.1 IBKR fetch timing after Start Trading (deep analysis and fixes)

**Why account info, P&L, and other IBKR data took time to display after clicking Start Trading:**

1. **Flow:** Start Trading → Rust starts sidecar → engine starts → TWS client connects. TWS sends **managedAccounts** on connection; the client then calls **reqPnL** and **reqAccountSummary**. TWS responds asynchronously with **pnl()** and **accountSummary()** callbacks, which fill `pnl_cache` and `account_summary_cache`. The engine emits **pnl_update** every loop (~50 ms) and **account_metrics** on an interval.

2. **Root causes of delay:**
   - **Account metrics:** The engine only emitted **account_metrics** on a fixed **5 s** interval. So even when the cache was filled 1–2 s after connection, the UI could wait up to **5 s** for the first emission.
   - **Frontend:** Account Summary called **get_account_metrics()** once when status became Running/connected; if that ran before the first engine emission, it got an empty snapshot and then relied only on the next 5 s event.
   - **PnL** appears as soon as TWS sends **pnl()** and the engine emits (every 50 ms); remaining delay is TWS connection + first **managedAccounts** + first **pnl()** response.

3. **Fixes implemented:**
   - **Backend (trading-engine):** Emit **account_metrics** **as soon as** `account_summary_cache` has data (first time after connection), then continue every 5 s. Added `_account_metrics_first_emit_done`; reset on connect/disconnect so each connection gets an immediate first emit when data is available.
   - **Frontend (AccountSummary):** When status becomes Running/connected, call **get_account_metrics()** once, then **short polling** at 600 ms and 1.6 s so the first backend emit is shown without waiting for the next 5 s event. Clean up timeouts on effect cleanup.

**Remaining (unavoidable) delay:** TWS connection time + time for TWS to send **managedAccounts** and first **accountSummary** / **pnl()** (typically under ~2 s if TWS is local and responsive).

---

# PART III – New Features: Backend

## 3.1 Continuous IBKR PnL & Account Metrics (P0) — **Done**

- **Persistent reqPnL:** Subscription kept open after managedAccounts; TWS pushes pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL) → pnl_cache. Engine emits pnl_update every loop (~50ms) when connected; Rust emits trading:pnl_update; Header, LiveStats, RiskManagement, and Analytics show daily/realized/unrealized.
- **reqAccountSummary:** Requested after managedAccounts with 12 tags: NetLiquidation, TotalCashValue, GrossPositionValue, BuyingPower, AvailableFunds, ExcessLiquidity, MaintMarginReq, InitialMarginReq, RealizedPnL, UnrealizedPnL, SettledCash, EquityWithLoanValue. accountSummary/accountSummaryEnd store in account_summary_cache; engine emits account_metrics **as soon as cache has data (first time)** then every 5s; Rust stores snapshot and emits trading:account_metrics; get_account_metrics command returns last snapshot.
- **Frontend:** Account Summary (IBKR) card on Dashboard shows all tags with labels and formatCurrency; useTradingEvents subscribes to trading:account_metrics; on load when engine running, get_account_metrics plus short polling (600ms, 1.6s) so first IBKR data appears quickly after Start Trading (see ROADMAP §2.1).
- See docs/IBKR_METRICS.md for API details.

## 3.2 New Tauri commands (candidates)

- **get_account_metrics** – Return last account summary snapshot (after §3.1).
- **export_trades** – Trigger export of trades to CSV (path from dialog or default); backend or sidecar writes file.
- **health** – Return sidecar alive, TWS connected, last data_status time (for “stale” indicator).

## 3.3 Sidecar protocol extensions

- **account_metrics** event with full account summary payload.
- **Optional:** Per-position PnL via reqPnLSingle and position_update enrichment.

## 3.4 Validation & persistence

- Validate config (ranges, required fields) in Rust before save; return clear errors to UI.
- Optional: persist last N log lines to disk for post-restart view.

---

# PART IV – New Features: Frontend

## 4.1 Account / Summary view — **Done (Dashboard card)**

- Dashboard section **Account Summary (IBKR)** shows Net Liquidation, Total Cash, Equity w/ Loan, Gross Position Value, Buying Power, Available Funds, Excess Liquidity, Settled Cash, Maint/Initial Margin Req, Realized P&L, Unrealized P&L (event-driven: first emit as soon as TWS data is available, then every ~5s; get_account_metrics on load + short polling at 0.6s and 1.6s after Start Trading so data appears quickly).
- Optional later: dedicated page or configurable refresh interval.

## 4.2 Alerts & notifications

- In-app toasts for: TWS connect/disconnect, day P&L limit hit, trade filled/closed, critical errors.
- Optional: Tauri system notifications and sound for important events.

## 4.3 Export & reporting

- Export trades (and optionally P&L summary) to CSV/Excel from Analytics or Positions; use backend export command or file save dialog + frontend CSV generation.

## 4.4 UX improvements

- Keyboard shortcuts (e.g. Start/Stop, focus search).
- Confirmation for Emergency Stop and Close All.
- Clear “stale data” indicator if no data_status or PnL update for N seconds.
- Optional: compact/dense layout mode for more data on screen.

## 4.5 Performance & optimizations (tab switch / general)

**Goal:** Eliminate UI hang or sluggishness when clicking between Dashboard, Analytics, Positions, Logs, and Settings.

| Area | Recommendation | Notes |
|------|----------------|--------|
| **Route code splitting** | Lazy-load page components with `React.lazy()` and `<Suspense>` so only the active route's JS is loaded and executed on first visit. | Reduces initial bundle and avoids mounting all pages on every tab click. |
| **High-frequency store updates** | Throttle PnL-driven re-renders: e.g. in the frontend, update a "display PnL" state at most every 1–2s from `trading:pnl_update`, or throttle in Rust/engine so UI receives PnL at ~1–2s instead of every 50ms. | PnL currently emitted every engine loop (~50ms); every update triggers store write and re-renders of Header, Sidebar, LiveStats, RiskManagement, etc. |
| **Layout components** | Memoize **Header** and **Sidebar** with `React.memo` and ensure they subscribe to minimal store slices (e.g. selectors) so they don't re-render on every PnL or log tick. | Both use `useTradingStore()` and re-render on any trading store change. |
| **Heavy lists** | Virtualize **Logs** page and **ActivityLog**: render only visible rows (e.g. `react-window`, `@tanstack/react-virtual`, or similar) instead of mapping over full `logs` / `recentLogs`. | LogsPage fetches up to 500 entries and maps over filtered list; ActivityLog shows last 50; no virtualization. |
| **List item keys** | Use stable IDs for log/position rows (e.g. `id` or `timestamp+index`) instead of array index to avoid unnecessary DOM churn when list updates. | Currently `key={i}` in LogsPage and ActivityLog. |
| **Page-level isolation** | Wrap page components in `React.memo` or use route-level wrappers so a tab's page doesn't re-render due to store updates that only other pages care about (e.g. Analytics page shouldn't re-render on every PnL if it only shows a snapshot). | Optional; combine with selective subscriptions. |
| **Event listener overhead** | Keep `useTradingEvents()` at root; ensure each listener does minimal work and avoids triggering unnecessary state updates (e.g. don't set state if value is unchanged). | Already at root; consider shallow compare before `setDailyPnl` / `setAccountMetrics` to avoid no-op re-renders. |

**Implemented:** (1) PnL throttled to 1s in useTradingEvents; (2) Lazy routes + Suspense; (3) Header/Sidebar memoized with selective store subscriptions; (4) Logs and ActivityLog virtualized with @tanstack/react-virtual; stable list keys. Dashboard shows "Updates: PnL ~1s · Account summary ~5s · Data status ~10s".

## 4.6 Optimization techniques (deep analysis)

Deep pass over the codebase: where time is spent, what triggers re-renders, and what can be improved. Ordered by impact vs effort.

### Already implemented (summary)

| Technique | Where | Effect |
|-----------|--------|--------|
| PnL throttle (1s) + shallow compare | useTradingEvents.ts | Cuts store writes from ~20/s to 1/s; avoids no-op setDailyPnl/setAccountMetrics. |
| Lazy routes + Suspense | App.tsx | Only active route’s chunk loads; faster tab switch and smaller initial JS. |
| Memo + selectors for layout | Header.tsx, Sidebar.tsx | Re-render only when status/dailyPnl/connectedToTws/settings change. |
| Virtualized lists | LogsPage.tsx, ActivityLog.tsx | Only visible rows rendered; stable keys `${timestamp}-${index}`. |
| Lighter cards | card.tsx, index.css | border/70, shadow-sm; lighter --border. |

### Frontend – store subscriptions and re-renders

| Location | Current behavior | Recommendation | Priority |
|----------|------------------|----------------|----------|
| **LiveStats** | `useTradingStore()` → destructures dailyPnl, totalTrades, winningTrades, losingTrades. Any trading store change re-renders. | Use 4 selectors: `(s) => s.dailyPnl`, `(s) => s.totalTrades`, etc. Re-render only when those slices change. | P2 |
| **DataFeedStatus** | `useTradingStore()` → `{ dataStatus }`. Re-renders on any trading store change. | Use `useTradingStore((s) => s.dataStatus)`. | P2 |
| **AccountSummary** | `useTradingStore()` → accountMetrics, status, connectedToTws. | Use selectors: `(s) => s.accountMetrics`, `(s) => s.status`, `(s) => s.connectedToTws`. | P2 |
| **RiskManagement** | `useTradingStore()` + `useConfigStore()` for dailyPnl, totalTrades, tradingConfig. | Use selectors for trading store; config already narrow. | P2 |
| **PerformanceMetrics, PnLChart, EquityCurve, WinLossChart** | useTradingStore() for todayTrades / winningTrades / losingTrades. Charts recompute data every render. | Use `(s) => s.todayTrades` (and win/loss selectors); **useMemo** for chart data (e.g. `chartData = useMemo(() => todayTrades.filter(...).map(...), [todayTrades])`) so Recharts doesn’t get new array every render. | P2 |
| **ConnectionConfig** | tradingConfig + connectedToTws. | Selectors for both stores. | P2 |

### Frontend – event handlers and stores

| Location | Current behavior | Recommendation | Priority |
|----------|------------------|----------------|----------|
| **usePositions** | On `trading:position_update`, uses `positions` from closure and `setPositions([...positions, data])`. If two events before next render, second can overwrite first (stale closure). | Use `usePositionStore.getState()` inside the event callback to always read latest positions, then update (or use functional setState with updater). | P2 |
| **logStore.addLog** | Every `trading:log_message` does `set({ logs: [...state.logs, entry].slice(-500) })`. High log volume → many store updates → ActivityLog/LogsPage re-render often. | **Batch logs**: collect entries in a ref, flush every 150–300ms (requestAnimationFrame or setInterval). Single store update per batch. | P2 |
| **useTradingEvents** | Subscribes to many events; each listener calls one or more setters. | Already minimal (throttle PnL, shallow compare account_metrics). Optional: skip setDataStatus if payload deep-equals current (data_status is ~10s so less critical). | P3 |

### Backend – trading engine (Python)

| Location | Current behavior | Recommendation | Priority |
|----------|------------------|----------------|----------|
| **Engine main loop** | `_emit_pnl_update()` every 50ms when connected; each emit is one JSON line to Rust. | **Throttle in engine**: e.g. only call emit_pnl every 1s (track last emit time). Reduces IPC and Rust/frontend work; frontend already throttles to 1s. | P2 |
| **Engine _try_connect_tws** | `time.sleep(0.2)` after connect. | Already reduced from 0.5s; keep 0.2s. | Done |
| **BOT / data feed** | Heavy work on every tick (Indicators, strategy). | Out of scope for “UI/config” optimizations; consider profiling if tick processing is slow. | P3 |
| **emit_log** | Every log line goes to stdout (protocol) and is forwarded to frontend. | Optional: in sidecar, batch log lines (e.g. buffer 50ms) and emit one event with array of entries; frontend then batch-adds to logStore. Reduces event traffic. | P3 |

### Rust – sidecar message handling

| Location | Current behavior | Recommendation | Priority |
|----------|------------------|----------------|----------|
| **handle_sidecar_message** | Every event locks AppState, updates, then emits to frontend. High event rate (e.g. pnl every 50ms before frontend throttle) still causes many lock/emit cycles. | Frontend throttle already limits visible updates. Optional: batch pnl_update in Rust (e.g. coalesce to 1s) before emitting; or leave as-is since frontend handles it. | P3 |
| **push_log** | Every log_message pushes to in-memory log buffer and then we emit to frontend. | If frontend batches log adds, Rust can stay as-is. Optional: batch log events in Rust (e.g. send every 100ms) to reduce IPC. | P3 |

### Summary table (optimization backlog)

| Category | Item | File(s) | Priority |
|----------|------|---------|----------|
| Frontend | LiveStats / DataFeedStatus / AccountSummary / RiskManagement use selectors | LiveStats.tsx, DataFeedStatus.tsx, AccountSummary.tsx, RiskManagement.tsx | P2 |
| Frontend | useMemo for PnLChart / EquityCurve chart data | PnLChart.tsx, EquityCurve.tsx | P2 |
| Frontend | usePositions: use getState() in event callback to avoid stale closure | usePositions.ts | P2 |
| Frontend | Batch addLog (e.g. 150–300ms) in useTradingEvents or logStore | useTradingEvents.ts or logStore.ts | P2 |
| Backend | Throttle _emit_pnl_update to 1s in engine | trading_engine.py | P2 |
| Backend | Optional: batch emit_log in sidecar | protocol/emitter.py or main.py | P3 |
| Rust | Optional: batch or throttle pnl/log events before emit | manager.rs | P3 |

---

# PART V – Modern & Unique UI Direction

**Goal:** Move away from a generic “AI slop” look (Inter, default blue/gray, standard card grids) toward a **distinctive, professional trading identity** that still feels modern and usable.

## 5.1 Current UI critique

- **Typography:** Inter is ubiquitous; little hierarchy beyond weight/size.
- **Color:** Standard blue primary and gray neutrals; could be more memorable and thematic.
- **Layout:** Dense but conventional; no strong “trading floor” or “terminal” character.
- **Motion:** Minimal (live-dot, fade-up); could reinforce status and feedback.

## 5.2 Unique UI: directions (pick a coherent set)

### Typography

- **Headings / identity:** Use a **distinct sans or serif** for app title and section headers (e.g. **Satoshi**, **Geist**, **Instrument Sans**, or **Fraunces**) so the product is recognizable at a glance.
- **Data & numbers:** Keep **monospace** for all financial figures (already JetBrains Mono); consider a second mono for logs (e.g. **IBM Plex Mono**) for a “terminal” feel.
- **Body:** Either keep Inter for readability or switch to a neutral but less overused sans (e.g. **DM Sans**, **Plus Jakarta Sans**).

### Color & theme

- **Option A – Deep quant:** Dark-first; primary accent **teal/cyan** (#0d9488 / 170 75% 35%) for actions and positive PnL; warm amber for warnings; red for loss. Sidebar and header very dark (near black) with subtle border.
- **Option B – Warm trading floor:** Warm neutrals (stone/amber tint); primary **amber/gold** for CTAs and key metrics; green/red for PnL. Feels “active” and high-contrast.
- **Option C – Terminal / pro:** High contrast; off-white on dark charcoal; accent **single bright color** (e.g. green or cyan) for live data and buttons; minimal decoration; grid or scan-line subtle texture.
- **Avoid:** Generic purple/violet gradients and “AI” blue that looks like every other SaaS.

### Layout & density

- **Optional compact mode:** Toggle that reduces padding and font size to show more stats and symbols without scrolling (e.g. 12px base, tighter cards).
- **Header:** Consider a **ticker-style** strip for key numbers (P&L, trades, connection) that scrolls or cycles on small width.
- **Dashboard:** Optional **grid of resizable panels** (react-grid-layout or similar) so power users can rearrange.

### Motion & feedback

- **Status transitions:** When status goes Idle → Running or TWS disconnected → connected, use a short **scale + fade** or **slide** so the change is noticeable.
- **PnL updates:** When daily P&L value changes, brief **highlight** (e.g. background flash green/red) then fade; avoid constant animation.
- **Reduced motion:** Respect `prefers-reduced-motion` for all non-essential animations.

### Identity elements

- **Logo/mark:** A simple, recognizable mark (e.g. “Q” or chart-like shape) used in sidebar and window title.
- **Data viz:** Charts (PnL, equity) with a **consistent palette** (e.g. emerald/red only) and optional subtle grid; avoid default Recharts rainbow.
- **Glass/cards:** Current glass utility is good; consider **slightly stronger border** or **inner shadow** on cards so they feel more “tactile” in dark mode.

## 5.3 Implementation priorities (UI)

| Priority | Item |
|----------|------|
| P1 | Choose and apply **one** typography set (heading font + mono for numbers). |
| P1 | Define **one** thematic color direction (Option A, B, or C) and implement in CSS variables + Tailwind. |
| P2 | Add **micro-interactions** (status change, PnL update flash) and respect reduced-motion. |
| P2 | Optional compact mode and/or resizable dashboard panels. |
| P3 | Ticker strip, logo refinement, chart palette consistency. |

---

# PART VIII – Performance Deep-Dive: Data Fetching, Signal Generation, Engine Speed

## 8.1 SuperTrend / BOTSingal — CRITICAL BOTTLENECK

**Current state (Indicators.py `BOTSingal`, line 181):** The SuperTrend calculation uses **5 separate `for i, row in data.iterrows()` loops** — this is the slowest possible way to iterate a pandas DataFrame (100–1000× slower than vectorized numpy). It is called on **every STK tick** via `event_processor → getCallPutEngulfCheck → indi.BOTSingal(new_df)`.

**Impact:** For 21 candles, 5 iterrows loops ≈ 105 row iterations. With 9 symbols, each generating ticks every ~250ms, that's ~36 SuperTrend calculations/s — each taking 2–5ms (iterrows overhead) = **~100ms/s** of pure CPU just for SuperTrend. This is the #1 CPU bottleneck.

**Fixes (ordered by impact):**

| Fix | Description | Speedup |
|-----|-------------|---------|
| **Vectorize ATR** | Replace `for i, row in data.iterrows(): ATR[i] = (ATR[i-1]*13 + TR[i])/14` with `data['ATR'] = data['TR'].ewm(alpha=1/14, min_periods=1, adjust=False).mean()` | 50–100× |
| **Vectorize FUB/FLB/ST** | Replace iterrows loops with `np.where()` chains or `numba.jit` compiled function | 50–100× |
| **Vectorize BUY_SELL** | Replace iterrows with `np.where(data['ST'] < data['Close'], 'BUY', 'SELL')` | 50× |
| **Cache & incremental update** | Only recalculate SuperTrend when a **new bar closes** (not on every tick). Cache the last SuperTrend state per symbol. On new bar: append new row, update last 2 rows only. | 10–20× (avoids redundant calls) |
| **Skip if signal unchanged** | After calculating, compare with cached signal. If no flip (BUY→SELL or SELL→BUY), return immediately without further processing. | 2–5× |

**alphaTrend (line 250)** has the exact same 5 iterrows loops — same fix applies.

## 8.2 Data Feed Initialization — 15+ SECONDS of Hard Sleeps

**Current state (BOT.py `init_data_feed`):**
```
subscribe underlyings (STK/FUT)  →  time.sleep(3.0)  ← HARD WAIT
subscribe options snapshots       →  time.sleep(10)   ← HARD WAIT
subscribe live options            →  (done)
```
Plus: `init_order_requests: time.sleep(2.0)`, `init_api_client: time.sleep(0.5)`.

**Total: ~15.5 seconds of blocking sleeps during startup.**

| Fix | Description | Time saved |
|-----|-------------|------------|
| **Event-based underlying wait** | Replace `time.sleep(3.0)` with `threading.Event` that fires when all STK subscriptions receive first tick (or 3s timeout). Usually ticks arrive in <1s. | ~2s |
| **Parallel options subscription** | Subscribe all options contracts using `ThreadPoolExecutor` instead of sequential loop. Currently subscribes ~80+ contracts one by one. | Marginal (IB rate limit) |
| **Event-based snapshot wait** | Replace `time.sleep(10)` with `threading.Event` that fires when snapshot data received for all contracts (or 10s timeout). TWS usually responds in 2–4s for snapshots. | ~6–8s |
| **Async contract resolution** | `get_contract_detail()` polls with `time.sleep(0.5)` up to 5s. Replace with `threading.Event` set by `contractDetails` callback. | ~1–3s per symbol |
| **Parallel symbol init** | Subscribe to multiple symbols simultaneously using thread pool for `get_stock_contract` + `subscribe` + `subscribe_historical_data`. | ~1–2s |

**Expected improvement: Startup from 15s → 4–6s.**

## 8.3 get_strikes() / get_contract_detail() — BLOCKING POLLS

**Current state (tws_api_client.py):**
- `get_strikes()` (line 235): `while self.ticker_strike_fetched != True: time.sleep(0.5)` — polls every 500ms.
- `get_contract_detail()` (line 281): `while not self.contract_detail_fetched and waited < max_wait: time.sleep(0.5)` — up to 5s.
- Both use single shared flags (`ticker_strike_fetched`, `contract_detail_fetched`) — **not thread-safe** for concurrent calls.

**Fix:** Replace shared flags with per-request `threading.Event` objects stored in a dict keyed by `reqId`. Callback sets the event; caller waits with `event.wait(timeout=5.0)`. Enables parallel contract resolution.

## 8.4 Event Processing Architecture

**Current state (BOT.py `event_processor`, line 1952):**
```python
event_data = event_queue.get(block=False, timeout=0.20)  # block=False ignores timeout
tick: Tick = event_data["tick"]
if tick.contract.secType == "STK":
    dataEngulf = getCallPutEngulfCheck(tick.contract.symbol)  # Full SuperTrend recalc!
```

**Problems:**
1. `block=False` with `timeout=0.20` — `block=False` means timeout is ignored; it either returns immediately or raises `Empty`. Should be `block=True, timeout=0.20`.
2. **Every STK tick triggers full SuperTrend recalculation** (21 candles → DataFrame → 5 iterrows loops). Signals only change on **bar close** events, not on every tick.
3. **4 event processor threads compete** on the same queue with no priority — OPT ticks (TP/SL checks) are equally delayed as STK ticks.
4. **No deduplication** — if 3 ticks arrive for SPY before processing, all 3 trigger separate SuperTrend calculations with identical bar data.

**Fixes:**

| Fix | Description | Impact |
|-----|-------------|--------|
| **Bar-close triggered signals** | Only run `getCallPutEngulfCheck` when `historicalDataUpdate` fires (new bar close), not on every tick. Use a per-symbol flag/event. | 90% reduction in signal calculations |
| **Separate OPT and STK queues** | OPT ticks (TP/SL checks) are time-critical; STK ticks (signal detection) are bar-interval. Use priority queue or two queues. | Lower TP/SL latency |
| **Deduplicate STK ticks** | Before processing, check if a newer tick for the same symbol is in the queue; skip stale ones. | Fewer redundant calculations |
| **Fix block parameter** | `event_queue.get(block=True, timeout=0.20)` so threads sleep properly instead of busy-spinning. | Lower CPU usage |

## 8.5 Indicators.py — Yahoo Finance HTTP Calls (External Dependency)

**Current state:** Several indicator functions (`RSI`, `MACD`, `OBV`, `IchimokuCloud`, `WILLIAMS`, `ATR`, `fibonacci`) call `yfinance.download()` or `yf.Ticker().history()` — these make HTTP requests to Yahoo Finance servers. Each call takes 200–2000ms.

**These are NOT used in the main SuperTrend flow** but exist as utility functions. If any strategy or code path calls them, it will cause severe latency.

**Fix:** Replace all yfinance-based indicators with TWS-data-based versions that use `history_cache` from `tws_api_client`. All the data needed (OHLCV) is already being streamed from TWS.

## 8.6 IPC Pipeline Optimizations

**Current state:**
- PnL emitted **every engine loop (~50ms)** — 20 writes/s per metric
- Each `emit_log()` = 1 `json.dumps()` + 1 `sys.stdout.write()` + 1 `sys.stdout.flush()` = 3 syscalls
- `_emit_data_status()` iterates **entire tick_cache under lock** every 10s — blocks tick processing

| Fix | Description | Impact |
|-----|-------------|--------|
| **Throttle PnL emit to 1s in Python** | Only emit if `time.time() - last_pnl_emit > 1.0`. Currently frontend throttles but engine still does 20 JSON writes/s. | -95% IPC volume |
| **Batch log emissions** | Buffer log lines for 100–200ms, then emit one event with array of entries. | -80% log IPC |
| **Lightweight data_status** | Don't iterate full tick_cache; just emit counts and cached prices. Or move heavy iteration to a background thread. | Lower lock contention |
| **Use msgpack instead of JSON** | msgpack is 2–5× faster to serialize than json.dumps for structured data. | ~50% faster IPC |

---

# PART IX – Professional Trading UI: New Features & Data Display

## 9.1 Dashboard — New Panels & Data

| Feature | Description | Data Source | Priority |
|---------|-------------|-------------|----------|
| **Real-time Options Greeks** | Show per-position delta, gamma, theta, vega. Professional traders need these. | TWS `reqMktData` with genericTickList "106" (implied vol) + "100" (option greeks) | P1 |
| **Intraday P&L Curve** | Time-series line chart of cumulative P&L throughout the day (x=time, y=cumulative $). Way more useful than bar chart of individual trades. | Collect P&L snapshots every 30s–1min into an array; persist in memory. | P1 |
| **Signal History Timeline** | Visual timeline showing detected signals with icons (▲ CALL, ▼ PUT), outcome (taken / skipped / won / lost), and timestamps. | Emit `signal_detected` events with outcome tracking. | P1 |
| **Market Overview Mini-panel** | SPY, QQQ, VIX sparkline mini-charts with current price, daily change %, and trend arrow. Gives market context at a glance. | TWS tick data for SPY/QQQ + VIX (subscribe as background symbols). | P2 |
| **Position P&L Cards** | Per-position card: entry price, current price, TP/SL levels as a horizontal bar/gauge, unrealized P&L, time held, Greeks. | Combine positions data + tick_cache for current prices + order_manager for TP/SL levels. | P1 |
| **Risk Gauges** | Visual gauges/progress bars for: daily P&L vs limits (how close to lock), margin utilization %, position concentration, buying power used. | Account metrics + config limits. | P2 |
| **Strategy Performance** | Win rate, avg P&L, trade count broken down by strategy type (SuperTrend vs Engulfing) and signal strength (strongBuy vs normalBuy). | Tag trades with strategy/signal_strength in DB; aggregate on frontend. | P2 |
| **Heat Map** | P&L heatmap by symbol × hour-of-day. Shows which symbols perform at what times. | Historical trade data aggregated. | P3 |
| **Order Flow Panel** | Real-time order lifecycle: Pending → Submitted → Filled → TP/SL Monitoring → Closed. Visual pipeline/timeline. | Order status events from order_manager. | P2 |

## 9.2 Logs — Professional Trading Terminal

| Feature | Description | Priority |
|---------|-------------|----------|
| **Trade Lifecycle Groups** | Collapsible log groups that link all logs for a single trade: signal → entry → TP/SL checks → exit. Click to expand. Use trade ID as group key. | P1 |
| **Structured Log Categories** | Visual category badges with distinct colors and icons: 🔌 System (gray), 📊 Trading (blue), 💰 Orders (green), 📡 Data (cyan), ⚙️ Strategy (purple), ⚠️ Error (red). | P1 |
| **Log Search & Regex** | Full-text search bar with regex support. Filter by symbol, order ID, time range. Highlight matches. | P1 |
| **Log Export** | Download filtered logs as CSV or JSON. Button in log toolbar. | P2 |
| **Log Persistence** | Write logs to disk (SQLite or rotating log files). Load last N entries on restart. Currently logs are lost on restart. | P2 |
| **Audio Alerts** | Configurable sound alerts for: trade fill (ka-ching), stop loss hit (alert), TWS disconnect (warning), P&L limit (alarm). Toggle per event type in Settings. | P2 |
| **Terminal-style Viewer** | Dark monospace viewer with syntax highlighting: prices in green/red, symbols bold, timestamps dimmed, errors red background. | P2 |
| **Log Severity Sidebar Badge** | Show error count badge on Logs sidebar item. Flash/pulse when new errors arrive. | P1 |
| **Trade-linked Log Navigation** | From Positions page, click "View Logs" on a position to jump to Logs page filtered to that trade's lifecycle. | P2 |
| **Compact vs Verbose Toggle** | Toggle to show/hide DEBUG level messages. Compact mode shows only trade-relevant logs. | P2 |

## 9.3 Analytics — Advanced Metrics

| Feature | Description | Priority |
|---------|-------------|----------|
| **Drawdown Chart** | Line chart showing drawdown from peak over time. Critical risk metric. | P1 |
| **Risk Metrics Panel** | Sharpe ratio, Sortino ratio, max drawdown %, expectancy (avg win × win rate - avg loss × loss rate), profit factor, recovery factor. | P1 |
| **Trade Distribution Charts** | Histogram by time of day, day of week, holding duration. Identify best trading windows. | P2 |
| **Symbol-level Breakdown** | Table/chart showing P&L, win rate, avg trade per symbol. Identify best/worst symbols. | P2 |
| **Cumulative Multi-day View** | Equity curve spanning multiple days (requires persistent trade DB). Show daily returns, running total. | P2 |
| **Strategy Comparison** | Side-by-side comparison of SuperTrend vs Engulfing: win rate, avg P&L, trade count, profit factor. | P2 |
| **Trade Execution Quality** | Measure slippage: signal price vs fill price, time from signal to fill. Identify execution issues. | P3 |
| **Session Summary Card** | Auto-generated end-of-day summary: total trades, P&L, best/worst trade, win rate, time in market. | P2 |

## 9.4 Positions — Enhanced Display

| Feature | Description | Priority |
|---------|-------------|----------|
| **Live P&L per Position** | Show current unrealized P&L with bid/ask/last prices updating in real-time (not just on 5s refresh). | P1 |
| **TP/SL Visual Gauge** | Horizontal bar showing entry → current price → TP and SL levels. Green zone (profit), red zone (loss). | P1 |
| **Greeks per Position** | Delta, gamma, theta, vega columns in position table. | P1 |
| **Time Held** | Show how long each position has been open (e.g. "12m 34s"). | P2 |
| **Position Sizing Info** | Show contract cost, max risk (entry - SL × qty × 100), risk as % of account. | P2 |
| **Quick Adjust TP/SL** | Inline edit TP and SL values from the positions table without going to settings. | P2 |
| **Position Alerts** | Visual alert when position is within 10% of TP or SL (glow/pulse effect). | P2 |

---

# PART X – Engine & Backend Improvements

## 10.1 Trading Engine Refactoring

| Item | Description | Priority |
|------|-------------|----------|
| **Class-based BOT** | Refactor BOT.py's 30+ globals into a TradingEngine class with proper state management. Eliminates race conditions and enables testing. | P1 |
| **Consolidated DB** | Merge dual databases (db/orders.db + database/trades.db) into one with migrations. Add trade_id linking. | P1 |
| **Fix SQL Injection** | data_access.py `update_option_order()` uses f-strings for SQL. Switch to parameterized queries. | P0 (security) |
| **Consolidated Loggers** | Merge 3 logger implementations (common.py, logger.py, utils/logger.py) into one with structured output. | P2 |
| **Threading.Event for waits** | Replace all `time.sleep()` polling loops with `threading.Event` or `asyncio`. | P1 |
| **Config validation** | Validate config in Rust before sending to sidecar: numeric ranges, required fields, symbol format. | P2 |

## 10.2 New Sidecar Events & Commands

| Event/Command | Direction | Description | Priority |
|---------------|-----------|-------------|----------|
| **greeks_update** | Sidecar → Rust | Per-position Greeks (delta, gamma, theta, vega) every 5s | P1 |
| **signal_history** | Sidecar → Rust | Full signal with outcome (taken/skipped/won/lost) | P1 |
| **order_lifecycle** | Sidecar → Rust | Detailed order state transitions for Order Flow panel | P2 |
| **bar_close** | Sidecar → Rust | Notify frontend when a new candle bar closes (for chart updates) | P2 |
| **health** | Rust → Sidecar | Health check: alive, TWS connected, queue size, last signal time | P1 |
| **export_trades** | Rust → Sidecar | Export trades to CSV/JSON file | P2 |
| **session_summary** | Sidecar → Rust | End-of-day trading summary | P2 |
| **tick_stream** | Sidecar → Rust | Optional: stream real-time tick prices for subscribed symbols (for live position P&L) | P2 |

## 10.3 TWS Data Enhancements

| Data | TWS API | Current | Needed For | Priority |
|------|---------|---------|------------|----------|
| **Option Greeks** | `reqMktData` with genericTickList "100,106" | Not requested | Position Greeks, Greeks per position | P1 |
| **reqPnLSingle** | `reqPnLSingle(reqId, account, "", conId)` | Not used | Per-position P&L from TWS (more accurate than manual calc) | P1 |
| **VIX data** | Subscribe to VIX as background symbol | Not subscribed | Market overview panel | P2 |
| **Execution details** | `reqExecutions` | Not used | Trade execution quality metrics, slippage analysis | P2 |
| **Historical data (multi-day)** | `reqHistoricalData` with "5 D" or more | "1 D" only | Multi-day analytics, drawdown chart | P2 |
| **Market depth** | `reqMktDepth` | Not used | Optional: Level 2 display for advanced users | P3 |

---

# PART VI – Priorities Summary (Updated)

| Priority | Area | Item |
|----------|------|------|
| ~~P0~~ | Backend | ~~Continuous PnL + full IBKR account metrics (§3.1)~~ **Done** |
| **P0** | **Security** | **Fix SQL injection in data_access.py** (§10.1) |
| **P1** | **Performance** | **Vectorize SuperTrend/BOTSingal** — replace 5 iterrows loops with numpy/ewm (§8.1) |
| **P1** | **Performance** | **Bar-close triggered signals** — only run signal detection on new bar close, not every tick (§8.4) |
| **P1** | **Performance** | **Remove hard sleeps in init_data_feed** — replace 15s of time.sleep() with Event-based waits (§8.2) |
| **P1** | **Performance** | **Throttle PnL emit to 1s in Python engine** (§8.6) |
| **P1** | **Performance** | **Fix event_queue.get()** — block=True with timeout instead of block=False (§8.4) |
| P1 | Backend | Remaining commands: export_trades, health (§3.2); get_account_metrics done |
| **P1** | **Backend** | **Options Greeks from TWS** — reqMktData genericTick "100,106" + greeks_update event (§10.3) |
| **P1** | **Backend** | **reqPnLSingle for per-position P&L** (§10.3) |
| P1 | Frontend | Account/Summary view (§4.1) **Done** (Dashboard card); Alerts & notifications (§4.2) |
| **P1** | **Frontend** | **Intraday P&L Curve** — time-series cumulative P&L chart (§9.1) |
| **P1** | **Frontend** | **Signal History Timeline** — visual signal timeline with outcomes (§9.1) |
| **P1** | **Frontend** | **Position P&L Cards with TP/SL gauge** — live per-position display (§9.1, §9.4) |
| **P1** | **Frontend** | **Trade Lifecycle Log Groups** — collapsible grouped logs per trade (§9.2) |
| **P1** | **Frontend** | **Log Search & Severity Badges** — regex search, error count badge (§9.2) |
| **P1** | **Frontend** | **Drawdown Chart + Risk Metrics** — Sharpe, Sortino, max DD, expectancy (§9.3) |
| ~~P1~~ | Frontend | ~~**Performance:** Fix UI hang on tab switch (§4.5)~~ **Done** |
| P1 | UI | Unique typography + thematic color (§5.2, §5.3) |
| **P2** | **Performance** | **Event-based contract resolution** — replace polling in get_strikes/get_contract_detail (§8.3) |
| **P2** | **Performance** | **Separate OPT/STK queues** — priority queue for TP/SL checks (§8.4) |
| **P2** | **Performance** | **Replace yfinance indicators with TWS data** (§8.5) |
| **P2** | **Performance** | **Batch log emissions in sidecar** (§8.6) |
| P2 | Backend | Config validation (§3.4); class-based BOT refactor (§10.1); consolidated DB + loggers (§10.1) |
| **P2** | **Backend** | **New events: order_lifecycle, bar_close, session_summary** (§10.2) |
| P2 | Frontend | Export & reporting (§4.3); UX (shortcuts, confirmations, stale indicator) (§4.4) |
| P2 | Frontend | **Optimizations:** store selectors, useMemo chart data, usePositions getState fix, batch addLog (§4.6) |
| **P2** | **Frontend** | **Market Overview Mini-panel** — SPY/QQQ/VIX sparklines (§9.1) |
| **P2** | **Frontend** | **Risk Gauges** — visual margin/P&L limit gauges (§9.1) |
| **P2** | **Frontend** | **Strategy Performance Breakdown** — per-strategy analytics (§9.1) |
| **P2** | **Frontend** | **Order Flow Panel** — order lifecycle visualization (§9.1) |
| **P2** | **Frontend** | **Log Persistence + Export + Audio Alerts** (§9.2) |
| **P2** | **Frontend** | **Symbol-level Analytics + Session Summary** (§9.3) |
| **P2** | **Frontend** | **Quick Adjust TP/SL from Positions** (§9.4) |
| P2 | UI | Motion and feedback; compact mode (§5.3) |
| P3 | All | BOT.py TODO cleanup; tests; code signing; docs |
| **P3** | **Performance** | **msgpack IPC, lightweight data_status, numba-compiled SuperTrend** (§8.6, §8.1) |
| **P3** | **Frontend** | **Heat Map, Trade Distribution, Execution Quality** (§9.1, §9.3) |
| **P3** | **Backend** | **Market depth, multi-day historical data** (§10.3) |

---

# PART XI – UI Library Evaluation & Professional Trading System Modernization

## 11.1 Current UI Stack Audit

The app already has a solid foundation:

| Layer | Current | Version | Status |
|-------|---------|---------|--------|
| **Framework** | React | 19.0.0 | ✅ Latest |
| **Bundler** | Vite | 6.0.0 | ✅ Latest |
| **Styling** | Tailwind CSS | 3.4.17 | ✅ Good — CSS variable theming, HSL colors, dark/light mode |
| **Components** | shadcn/ui (partial) | — | ⚠️ Only 7 of 40+ components installed: button, card, badge, input, progress, separator, switch |
| **Charts** | Recharts | 2.15.0 | ⚠️ Good for analytics; **not suitable for candlestick/OHLCV trading charts** |
| **State** | Zustand | 5.0.0 | ✅ Lightweight, performant |
| **Virtualization** | @tanstack/react-virtual | 3.13.18 | ✅ Used in Logs & ActivityLog |
| **Animation** | Framer Motion | 11.15.0 | ✅ Used minimally |
| **Icons** | Lucide React | 0.469.0 | ✅ Consistent icon set |
| **Fonts** | Inter (sans), JetBrains Mono (mono) | — | ⚠️ Inter is ubiquitous; could be more distinctive |
| **Data Tables** | Raw HTML `<table>` | — | ❌ No sorting, filtering, resizing, pagination |
| **Notifications** | Basic custom Toaster | — | ❌ No action-capable toasts, no stacking, no persistence |
| **Command Palette** | None | — | ❌ No keyboard-driven navigation |
| **Candlestick Charts** | None | — | ❌ No OHLCV charting, no indicator overlays |
| **Loading States** | None (spinner text only) | — | ❌ No skeleton screens, no shimmer loading |

## 11.2 Library Comparison: shadcn/ui vs MUI vs DaisyUI

### ⭐ Verdict: **Keep shadcn/ui + Tailwind CSS (already in use) — extend with trading-specific libraries**

| Criteria | **shadcn/ui + Tailwind** | **MUI (Material-UI)** | **DaisyUI** |
|----------|--------------------------|----------------------|-------------|
| **Bundle size** | ~0 KB runtime (copy-paste components, no lib import) | ~150–300 KB gzipped (core + DataGrid) | ~20 KB (Tailwind plugin) |
| **Customizability** | ⭐⭐⭐⭐⭐ Full source code ownership; every pixel customizable | ⭐⭐⭐ Theme overrides but constrained by Material Design | ⭐⭐⭐ Tailwind-based but pre-styled, less granular |
| **Dark mode** | ⭐⭐⭐⭐⭐ CSS variable-based, already implemented | ⭐⭐⭐⭐ Theme provider, works but heavier | ⭐⭐⭐⭐ data-theme attribute, easy swap |
| **Real-time data perf** | ⭐⭐⭐⭐⭐ No runtime overhead; React.memo friendly | ⭐⭐⭐ Emotion/styled-components re-render cost | ⭐⭐⭐⭐ Tailwind = no runtime style overhead |
| **Data grid/tables** | ❌ No built-in (needs TanStack Table) | ⭐⭐⭐⭐⭐ MUI DataGrid (sorting, filtering, virtual scroll, grouping) | ❌ Basic HTML table styling only |
| **Financial components** | ❌ No built-in (custom build) | ⚠️ Some via DataGrid, no chart-specific | ❌ None |
| **Accessibility** | ⭐⭐⭐⭐⭐ Radix UI primitives (WAI-ARIA compliant) | ⭐⭐⭐⭐ Material spec compliant | ⭐⭐⭐ Basic aria attributes |
| **Trading platform usage** | TradingView alternatives, Crypto exchanges (Kraken, Coinbase Pro), Fintech startups | Bloomberg-like institutional terminals, Enterprise trading desks | Not used by known trading platforms |
| **Ecosystem** | 40+ components, growing fast | 50+ components, enterprise mature | ~50 components, general purpose |
| **Migration cost for this project** | **Zero** — already using it; extend what's there | **High** — complete restyle, new dependencies, theme rewrite | **Medium** — can overlay but conflicts with existing shadcn patterns |
| **TypeScript** | ⭐⭐⭐⭐⭐ First-class TypeScript | ⭐⭐⭐⭐ Good TypeScript support | ⚠️ CSS-only, no TS components |

### Why NOT switch to MUI or DaisyUI:
1. **Already invested in shadcn/ui** — 7 components, full CSS variable theming, Tailwind integration. Switching = rewrite.
2. **MUI is too heavy** for a Tauri desktop app where every KB matters and real-time data updates at 1s intervals. Emotion (MUI's CSS-in-JS) recalculates styles on each render.
3. **DaisyUI is too generic** — its pre-built component styles look good for SaaS apps but lack the data-density and precision needed for trading terminals.
4. **shadcn/ui gives you the code** — you can tune every pixel for trading use cases (monospace pricing, P&L coloring, ticker animations).

## 11.3 Recommended Library Stack (Definitive)

### Core (Already Installed — Extend)

| Library | Purpose | Status |
|---------|---------|--------|
| **shadcn/ui** | Full component library — install ALL remaining components | ⚠️ Extend (7→40+ components) |
| **Tailwind CSS 3** | Utility-first styling, CSS variables | ✅ Already configured |
| **Zustand 5** | State management | ✅ Already in use |
| **Framer Motion** | Animations and transitions | ✅ Already installed |
| **Lucide React** | Icon system | ✅ Already in use |
| **@tanstack/react-virtual** | List virtualization | ✅ Already in Logs |

### New Libraries to Add

| Library | npm Package | Purpose | Bundle Size | Priority |
|---------|-------------|---------|-------------|----------|
| **TradingView Lightweight Charts** | `lightweight-charts` | Professional candlestick/OHLCV charts with indicator overlays, crosshair, volume bars. Industry standard. | ~45 KB gzipped | **P0** |
| **TanStack Table v8** | `@tanstack/react-table` | Headless data table: sorting, filtering, column resizing/pinning, row selection, pagination. For positions, order history, trades. | ~15 KB gzipped | **P0** |
| **Sonner** | `sonner` | Professional toast notifications with stacking, actions, progress, rich content. Created by shadcn author (Emil Kowalski). | ~5 KB gzipped | **P1** |
| **cmdk** | `cmdk` | Command palette (⌘+K / Ctrl+K). Instant keyboard navigation: search symbols, run commands, switch pages, emergency stop. Power-user essential. | ~4 KB gzipped | **P1** |
| **Vaul** | `vaul` | Drawer/sheet component. Slide-out panels for position details, trade drilldowns on mobile/compact mode. | ~3 KB gzipped | **P2** |
| **react-resizable-panels** | `react-resizable-panels` | Resizable dashboard panels. Let power users customize layout: expand chart, shrink logs, etc. | ~8 KB gzipped | **P2** |
| **nuqs** | `nuqs` | URL-based state management for filters (log level, symbol, date range). Shareable/bookmarkable filter states. | ~3 KB gzipped | **P3** |

**Total new bundle:** ~83 KB gzipped — acceptable for a Tauri desktop app.

### Libraries Explicitly NOT Recommended

| Library | Reason NOT to use |
|---------|-------------------|
| **MUI / Material-UI** | Too heavy (+300 KB), CSS-in-JS runtime cost, conflicts with Tailwind theming. Overkill when TanStack Table + shadcn covers the same use cases. |
| **DaisyUI** | Overlaps and conflicts with existing shadcn/ui components. Pre-styled approach contradicts shadcn's "own your components" philosophy. |
| **Ant Design** | Very heavy (+400 KB), Chinese design language may feel foreign, Moment.js dependency, non-trivial tree-shaking. |
| **AG Grid** | Powerful but commercial license for advanced features ($2K+/dev); TanStack Table + shadcn/ui achieves same result for free. |
| **D3.js** | Too low-level for typical trading charts; TradingView Lightweight Charts provides better out-of-box experience with 10× less code. |
| **Chart.js** | Less suited for financial data than Recharts (already in use) or Lightweight Charts. No built-in candlestick support. |
| **react-hot-toast** | Sonner is newer, lighter, better designed by same ecosystem (Emil Kowalski / shadcn). |

## 11.4 shadcn/ui Component Installation Plan

### Phase 1 — Critical (install immediately)

These components are needed for the trading-specific features in Parts IX and XI:

| Component | Usage in Trading App |
|-----------|---------------------|
| **dialog** | Order confirmation, trade details, position close, emergency stop confirmation |
| **dropdown-menu** | Position actions (close, adjust TP/SL, view logs), symbol context menu |
| **select** | Strategy selector, timeframe picker, symbol filter, expiry selector |
| **tabs** | Dashboard sub-sections (Overview / Signals / Activity), Analytics views |
| **tooltip** | Chart data points, column headers, abbreviated metric explanations |
| **table** | Shadcn table primitives for styled position/trade/order tables |
| **skeleton** | Loading states for account metrics, positions, charts on startup |
| **alert** | System alerts (TWS disconnect, P&L limit near, margin warning) |
| **collapsible** | Trade lifecycle log groups (expand to see all events for one trade) |
| **scroll-area** | Custom scrollable regions in activity log, log viewer, position list |
| **toast** (Sonner) | Trade fills, errors, connection events — with actions and rich content |
| **command** (cmdk) | Command palette for power users (⌘K / Ctrl+K) |

### Phase 2 — Enhanced UX

| Component | Usage |
|-----------|-------|
| **popover** | Quick details on hover (position Greeks, signal breakdown, metric formula) |
| **sheet** | Slide-out panel for position details, trade drill-down, settings quick-access |
| **hover-card** | Rich preview on symbol hover (last price, daily change, mini-chart) |
| **slider** | Quick adjust TP/SL from positions table, volume filter in analytics |
| **context-menu** | Right-click on position row for actions (close, adjust, view logs, chart) |
| **toggle-group** | Timeframe selector (1m / 5m / 15m / 1h / 1D), view mode (list / grid / compact) |
| **aspect-ratio** | Consistent chart proportions across screen sizes |
| **avatar** | Account/user indicator in header |

### Phase 3 — Polish

| Component | Usage |
|-----------|-------|
| **resizable** | Resizable dashboard panels (expand chart, shrink log area) |
| **accordion** | Settings categories, strategy parameter groups |
| **navigation-menu** | Enhanced sidebar with sub-menus |
| **menubar** | Top menu bar (File, Trading, View, Help) for desktop-native feel |
| **calendar** + **date-picker** | Date range filter for trades, logs, analytics |
| **data-table** | Full shadcn data table pattern (TanStack Table + shadcn table primitives + pagination + column header dropdowns) |

## 11.5 TradingView Lightweight Charts — Integration Plan

**Why this is the #1 missing library:** Professional trading platforms are defined by their chart. Recharts is fine for analytics bar/line charts, but options traders need **candlestick charts with indicator overlays**.

### What Lightweight Charts provides:

- **Candlestick series** — OHLCV with proper wicks, body coloring (green/red)
- **Line series** — For SuperTrend bands, EMA overlays, support/resistance
- **Histogram series** — Volume bars below candlestick chart
- **Area series** — For P&L equity curve with gradient fill
- **Markers** — Signal entry/exit markers directly on chart (▲ BUY, ▼ SELL)
- **Crosshair** — Professional hover with OHLCV + indicator values in legend
- **Time scale** — Proper financial time axis (skip weekends/after-hours)
- **Real-time updates** — `series.update()` for live bar updates from TWS stream
- **Themes** — Full color customization matching our dark/light themes
- **Lightweight** — ~45 KB gzipped, WebGL rendered, handles 100K+ data points

### Components to build:

```
src/components/charts/
├── TradingChart.tsx          -- Main wrapper: candlestick + volume + indicator overlays
├── MiniChart.tsx             -- Sparkline version for market overview (SPY/QQQ/VIX)
├── PnLEquityCurve.tsx        -- Area chart for intraday cumulative P&L
├── useChartTheme.ts          -- Hook to sync chart colors with app theme
├── indicators/
│   ├── SuperTrendOverlay.tsx  -- SuperTrend line + signal markers on chart
│   ├── EMAOverlay.tsx         -- EMA 8/13/21 lines
│   └── VolumeHistogram.tsx    -- Volume bars below main chart
└── utils/
    ├── chartData.ts           -- Transform TWS bar data → chart format
    └── timeScale.ts           -- Financial time helpers
```

### Data flow for live chart updates:

```
TWS → historicalDataUpdate callback → history_cache → engine emits bar_close event
→ Rust forwards trading:bar_close → React useTradingEvents → chart store
→ TradingChart.tsx calls series.update(newBar) → WebGL re-render (< 1ms)
```

## 11.6 TanStack Table — Professional Data Grid Plan

**Why needed:** Current positions/trades use raw HTML `<table>` with no sorting, filtering, or column management. Professional trading terminals (Bloomberg, Thinkorswim, Interactive Brokers) all have powerful, configurable data grids.

### Features to implement:

| Feature | Trading Use Case |
|---------|------------------|
| **Column sorting** | Sort positions by P&L (best/worst first), sort trades by time, symbol |
| **Column filtering** | Filter positions by symbol, type (CALL/PUT), P&L range |
| **Column resizing** | Users resize columns to see what matters (expand P&L, shrink IDs) |
| **Column pinning** | Pin Symbol and P&L columns so they stay visible when scrolling horizontally |
| **Row selection** | Select multiple positions for batch close |
| **Pagination** | Trade history can grow to 100s of entries; paginate at 25/50/100 rows |
| **Row grouping** | Group trades by symbol or by day |
| **Virtual scrolling** | Combine with @tanstack/react-virtual for 1000+ row performance |
| **Custom cell renderers** | P&L cells with color, Greeks with formatting, TP/SL gauges inline |
| **Row expansion** | Click to expand position row → show trade lifecycle, Greeks breakdown, chart |

### Tables to upgrade:

| Current Location | Current State | Upgrade To |
|-----------------|---------------|------------|
| **PositionsPage** — Active positions | Raw `<table>`, 9 columns, no sort/filter | TanStack Table + shadcn table + column sort + row expand |
| **PositionHistory** — Closed trades | Simple list | TanStack Table + pagination + symbol filter + P&L sort |
| **LogsPage** — System logs | Virtualized flat list | TanStack Table with column filter (level, category) + search |
| **AccountSummary** — IBKR metrics | Key/value cards | Keep cards (already good) |
| **StockList** — Symbols | Simple list with add/remove | TanStack Table with inline edit and real-time prices |

## 11.7 Professional Trading Terminal Design System

### Color System Update

Extend the current HSL variable system with trading-specific semantic colors:

```css
/* ─── Trading Colors (add to index.css) ─── */
:root {
  --profit: 160 84% 39%;        /* Emerald — already defined as success */
  --loss: 0 84% 60%;            /* Red — already defined as destructive */
  --bid: 160 84% 39%;           /* Green for bid prices */
  --ask: 0 84% 60%;             /* Red for ask prices */
  --signal-call: 160 84% 39%;   /* Green for CALL signals */
  --signal-put: 0 84% 60%;      /* Red for PUT signals */
  --signal-neutral: 220 9% 46%; /* Gray for no signal */
  --chart-up: 160 84% 39%;      /* Candle body up */
  --chart-down: 0 84% 60%;      /* Candle body down */
  --chart-volume: 217 92% 65%;  /* Volume histogram */
  --chart-grid: 220 12% 93%;    /* Chart grid lines */
  --greeks-delta: 217 92% 65%;  /* Blue for delta */
  --greeks-gamma: 280 65% 60%;  /* Purple for gamma */
  --greeks-theta: 38 92% 50%;   /* Amber for theta */
  --greeks-vega: 160 84% 39%;   /* Teal for vega */
}
```

### Typography Enhancement

| Element | Current | Recommended | Why |
|---------|---------|-------------|-----|
| **App title / brand** | Inter bold | **Geist Sans** or **Satoshi** | More distinctive than Inter; used by modern fintech |
| **Section headers** | Inter semibold | **DM Sans** or keep Inter | Slightly warmer, more readable at small sizes |
| **Financial numbers** | JetBrains Mono | **JetBrains Mono** (keep) | ✅ Already excellent for tabular numbers |
| **Log viewer** | JetBrains Mono 10px | **IBM Plex Mono** (secondary mono) | Terminal-grade readability; distinguish logs from data |
| **Prices / P&L** | JetBrains Mono with .tabular-nums | Keep + add **proportional-nums for large hero numbers** | Hero P&L should use proportional spacing for visual weight |

### Micro-interactions for Trading

| Trigger | Animation | Purpose |
|---------|-----------|---------|
| **P&L value changes** | Brief background flash (green/red → transparent, 300ms ease-out) | Draw eye to P&L update without being distracting |
| **New trade fill** | Sonner toast slides in from right with confetti icon for profit | Celebrate wins, professional-feeling confirmation |
| **Stop loss hit** | Toast with warning icon + brief header pulse red (200ms) | Urgent but not alarming — this is expected behavior |
| **TWS connected** | Sidebar status chip does a brief scale-up (1.05→1.0, 200ms) | Visible confirmation of connection |
| **TWS disconnected** | Header gets a subtle red top-border (animated in 300ms) that stays until reconnect | Persistent visual warning without blocking UI |
| **Signal detected** | Signal badge in Activity area does a brief glow/pulse (one cycle, 500ms) | Catch attention for important trading events |
| **Position near TP/SL** | Position row gets a pulsing left border (emerald for near-TP, red for near-SL) | Pre-alert before TP/SL hits |
| **Emergency stop** | Full-screen flash (red, 100ms) then instant stop | Matches the urgency of the action |
| **Tab/page switch** | Page content fades in (opacity 0→1, 150ms) | Already have fade-up; make it snappier |

### Command Palette (cmdk) Design

Professional trading terminals (Bloomberg, Thinkorswim) are keyboard-driven. Add ⌘K/Ctrl+K command palette:

```
Groups:
├── Navigation
│   ├── Go to Dashboard           (Ctrl+1)
│   ├── Go to Analytics           (Ctrl+2)
│   ├── Go to Positions           (Ctrl+3)
│   ├── Go to Logs                (Ctrl+4)
│   └── Go to Settings            (Ctrl+5)
│
├── Trading Actions
│   ├── Start Trading             (Ctrl+Shift+S)
│   ├── Stop Trading              (Ctrl+Shift+X)
│   ├── Emergency Stop            (Ctrl+Shift+E)
│   ├── Close All Positions       (Ctrl+Shift+C)
│   └── Refresh Positions         (Ctrl+R)
│
├── Quick Search
│   ├── Search symbol: SPY...     (type to filter)
│   ├── Search logs: error...     (type to filter)
│   └── Search trades: AAPL...    (type to filter)
│
├── View
│   ├── Toggle Dark Mode          (Ctrl+D)
│   ├── Toggle Compact Mode       (Ctrl+Shift+D)
│   └── Toggle Auto-scroll Logs   (Ctrl+L)
│
└── Export
    ├── Export Trades CSV
    ├── Export Logs JSON
    └── Export Settings
```

## 11.8 Professional Dashboard Layout Redesign

### Current layout issues:

1. **Linear vertical stack** — all cards stack top to bottom; wastes horizontal space on wide monitors.
2. **No chart** — the #1 thing a trader wants to see is a chart with price action and signals.
3. **Config panels dominate** — TradeParameters, ConnectionConfig, StockList are config panels that take up 50% of dashboard space. These should be in Settings or a collapsible sidebar.
4. **No market overview** — no SPY/QQQ/VIX context visible.

### Proposed layout (3-panel professional trading terminal):

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ HEADER: [Trading Active] │ P&L: +$420.50 │ Trades: 5 │ Win: 80% │ Clock ET │
├──────────────────────────────────────────────────────────────────────────────┤
│ SIDEBAR │  MAIN AREA (resizable panels)                                     │
│         │                                                                    │
│ Dashboard│  ┌──────────────────────┬────────────────────────────────────┐    │
│ Analytics│  │  LiveStats (6 cards) │  Market Overview (SPY/QQQ/VIX)    │    │
│ Positions│  ├──────────────────────┴────────────────────────────────────┤    │
│ Logs    │  │                                                            │    │
│ Settings│  │  TRADING CHART (candlestick + SuperTrend + volume)         │    │
│         │  │  [1m] [5m] [15m] [1h] [1D]     Symbol: SPY ▾              │    │
│         │  │                                                            │    │
│ ─────── │  ├────────────────────────────┬───────────────────────────────┤    │
│ TWS ●   │  │  ACTIVE POSITIONS          │  SIGNAL ACTIVITY              │    │
│ Engine ● │  │  (TanStack Table)         │  (Signal timeline + log)      │    │
│ DEMO    │  │  Sort/Filter/Expand        │  ▲ CALL SPY 14:32 strongBuy  │    │
│         │  │  SPY 590C +$120 ███████░░  │  ▼ PUT QQQ 14:28 mediumSell  │    │
│         │  │  AAPL 185P -$40 ██░░░░░░░  │  ▲ CALL TSLA 14:15 normalBuy│    │
│         │  └────────────────────────────┴───────────────────────────────┤    │
│         │  TRADING CONTROLS + ACCOUNT SUMMARY (collapsible bottom bar)  │    │
└─────────┴───────────────────────────────────────────────────────────────────┘
```

**Key changes from current layout:**

| Change | Current | Proposed | Why |
|--------|---------|----------|-----|
| **Add trading chart** | No chart on dashboard | Candlestick chart with SuperTrend overlay | This is what traders look at 90% of the time |
| **Move config panels** | TradeParameters, ConnectionConfig, StockList on dashboard | Move to Settings page | Config rarely changes during trading; dashboard is for monitoring |
| **Add signal activity** | Only Activity Log (generic) | Dedicated signal timeline panel | Signals are the core decision driver; deserve prominent placement |
| **Market overview** | None | SPY/QQQ/VIX mini-charts in header area | Market context is essential for options trading |
| **Resizable panels** | Fixed grid | react-resizable-panels | Power users customize their workspace |
| **Trading controls** | Full card with Start/Stop/Emergency | Compact bar or keep in sidebar | Start/Stop used once per session; doesn't need large card |

## 11.9 Implementation Phases & Priorities

### Phase 0 — Foundation (1–2 days, no visual change)

| Task | Details |
|------|---------|
| ~~Install shadcn/ui components (no Radix deps)~~ | ~~`tabs`, `tooltip`, `skeleton`, `alert` — pure Tailwind implementations~~ **✅ Done** |
| Install missing shadcn/ui components (Radix) | `dialog`, `dropdown-menu`, `select`, `collapsible`, `scroll-area` — need Radix deps |
| Install new libraries | `lightweight-charts`, `@tanstack/react-table`, `sonner`, `cmdk` |
| ~~Set up trading color tokens~~ | ~~`--bid`, `--ask`, `--signal-call`, `--signal-put`, `--greeks-*` CSS vars + Tailwind `trading.*`, `signal.*`, `greeks.*` colors~~ **✅ Done** |
| Create chart wrapper | `TradingChart.tsx` with Lightweight Charts initialization + theme sync |
| Create data-table wrapper | `DataTable.tsx` combining TanStack Table + shadcn table primitives |

### Phase 1 — Core Trading UI (1–2 weeks)

| Task | Component(s) | Status |
|------|-------------|--------|
| **Trading chart on dashboard** | `TradingChart.tsx`, `SuperTrendOverlay.tsx` | 🔴 TODO — highest UX impact |
| ~~**Skeleton loading states**~~ | ~~StatCard, LiveStats, AccountSummary, PositionsPage~~ | **✅ Done** |
| **Sonner toast notifications** | Replace custom Toaster; trade fills, errors, connections | TODO (needs npm install) |
| **Position table upgrade** | `PositionsPage.tsx` with TanStack Table + sort + filter | TODO (needs npm install) |
| ~~**P&L flash animations**~~ | ~~Header, StatCard, PnLValue — green/red flash on value change~~ | **✅ Done** |

### Phase 2 — Professional Features (2–3 weeks)

| Task | Component(s) | Status |
|------|-------------|--------|
| **Command palette** | cmdk integration, keyboard shortcuts | TODO (needs npm install) |
| ~~**Signal history timeline**~~ | ~~`SignalActivity.tsx` — visual signal feed with direction icons, strength badges, timestamps~~ | **✅ Done** |
| ~~**Market overview panel**~~ | ~~`MarketOverview.tsx` — live tick data grid with bid/ask, priority symbol sorting~~ | **✅ Done** |
| ~~**Position P&L gauge**~~ | ~~`PositionRow.tsx` — horizontal gauge bar per position with color-coded fill~~ | **✅ Done** |
| ~~**Dashboard layout redesign**~~ | ~~`DashboardPage.tsx` — tabbed layout (Overview, Signals & Market, Configuration, Activity)~~ | **✅ Done** |
| ~~**Log severity badges**~~ | ~~Error count in Sidebar, structured log categories with icons, log search in LogsPage~~ | **✅ Done** |

### Phase 3 — Advanced & Polish (3–4 weeks)

| Task | Component(s) | Impact |
|------|-------------|--------|
| **Greeks display** | Per-position delta/gamma/theta/vega columns | Options trader essential |
| **Intraday P&L curve** | Lightweight Charts area series for cumulative P&L | Performance tracking |
| **Drawdown chart** | Equity high-water mark with drawdown shading | Risk visualization |
| **Trade lifecycle groups** | Collapsible log groups per trade ID | Debug and audit |
| **Audio alerts** | Configurable sound per event type | Hands-free monitoring |
| **Export (CSV/JSON)** | Trades, logs, settings export | Compliance and analysis |
| **Typography refresh** | Geist/Satoshi for headings, IBM Plex Mono for logs | Distinctive brand identity |
| **Compact mode toggle** | Reduce padding/font for data density | Power user mode |

### Phase 4 — Premium Features (4+ weeks)

| Task | Component(s) |
|------|-------------|
| Order flow panel (order lifecycle pipeline) | Custom component |
| Symbol-level analytics breakdown | TanStack Table + Recharts |
| Multi-day equity curve | Lightweight Charts + persistent DB |
| P&L heatmap (symbol × hour) | Custom canvas or Recharts heatmap |
| Strategy comparison dashboard | Side-by-side analytics |
| Resizable dashboard panels | react-resizable-panels |
| Calendar-based trade history | shadcn calendar + date-picker |

---

# PART XIII – NinjaTrader & TradingView Gap Analysis

## 13.1 Component-by-Component Comparison

Deep comparison of every UI component against NinjaTrader (NT) and TradingView (TV) professional trading terminals.

| Component | Current Grade | NT/TV Standard | Key Gaps |
|-----------|:---:|:---:|---|
| **Dashboard Layout** | B- | A+ | No chart, tab-based not panel-based, config panels dominate |
| **Trading Chart** | F (none) | A+ | No candlestick chart at all — this is the #1 gap |
| **Header** | B+ | A | Missing market ticker strip, market hours countdown |
| **Sidebar** | B | A | No watchlist, navigation-only |
| **Positions Table** | C+ | A | No sort/filter, missing columns (Greeks, time held, strategy) |
| **Analytics Charts** | B- | A | No zoom/pan, no candlestick, no drawdown chart |
| **Logs** | B+ | A | No trade lifecycle groups, no regex search |
| **Settings** | B | B+ | No tree organization, no search within settings |
| **Notifications** | D | A | Barely used toaster, no trade fill alerts |
| **Keyboard Navigation** | F (none) | A+ | Zero shortcuts, no command palette |
| **Market Overview** | B | A | No mini charts/sparklines, basic grid |
| **Risk Dashboard** | C+ | A | No portfolio Greeks, no margin gauge, basic progress bars |
| **Account Summary** | A- | A | Good — just needs refresh indicator |
| **Signal Activity** | B+ | A | Good foundation — needs outcome tracking (won/lost) |
| **Data Feed Status** | B+ | B+ | Good — could add latency/throughput metrics |
| **Live Stats** | A- | A | Good — skeleton + flash working well |

## 13.2 Critical Gaps (Must-Have for Professional Trading Terminal)

### 🔴 Gap 1: No Candlestick/Price Chart (HIGHEST PRIORITY)

**What NT/TV have:** Chart occupies 60-70% of screen. OHLCV candlestick with indicator overlays (SuperTrend bands, EMA lines, volume histogram), signal entry/exit markers (▲ BUY, ▼ SELL), real-time bar updates, crosshair with OHLC+indicator values, timeframe selector (1m/5m/15m/1h/1D), symbol switcher.

**What we have:** Zero price chart anywhere in the app. The dashboard shows stat cards, config panels, and market overview grid — but no visual representation of price action. This is the single biggest gap between our app and a professional trading terminal. Traders stare at charts 90% of the time.

**Implementation:** TradingView Lightweight Charts (`lightweight-charts`, ~45 KB gzipped, WebGL rendered). Build `TradingChart.tsx` wrapping the library. Data: `history_cache` bars from TWS → engine emits `bar_close` event → Rust → frontend → `series.update()`. Overlays: SuperTrend line, EMA bands, volume histogram, buy/sell signal markers. Theme sync via `useChartTheme` hook mapping our CSS variables → chart config.

### 🔴 Gap 2: No Command Palette / Keyboard Shortcuts

**What NT/TV have:** NinjaTrader is fully configurable with hotkeys for orders, chart manipulation, workspace switching. TradingView has ⌘K search, keyboard shortcuts for drawing tools, timeframe switching, indicator toggle. Bloomberg Terminal is entirely keyboard-driven.

**What we have:** Zero keyboard shortcuts. Mouse-only navigation. No ⌘K/Ctrl+K search. No hotkeys for Start/Stop/Emergency, no Ctrl+1-5 for page navigation.

**Implementation:** `cmdk` (~4 KB) for command palette. `useEffect` keyboard listeners for: Ctrl+1-5 (navigate pages), Ctrl+Shift+S (start trading), Ctrl+Shift+X (stop), Ctrl+Shift+E (emergency stop), Ctrl+Shift+C (close all), Ctrl+D (toggle dark mode), Ctrl+K (command palette), Ctrl+L (toggle log auto-scroll).

### 🔴 Gap 3: Dashboard Layout is Tab-Based, Not Panel-Based

**What NT/TV have:** Dockable, resizable panels — chart, positions, DOM, time & sales all visible simultaneously. TradingView has multi-pane layout with drag-to-resize. NinjaTrader workspace tabs contain multiple docked panels per tab.

**What we have:** Tab layout means you can only see one section at a time (Overview OR Signals OR Config). During live trading, a trader needs chart + positions + signals visible simultaneously.

**Implementation:** `react-resizable-panels` (~8 KB) wrapping dashboard content into a chart-first multi-panel layout:
- **Top panel (60%):** TradingChart + LiveStats
- **Bottom-left panel (25%):** Active positions (TanStack Table)
- **Bottom-right panel (25%):** Signal activity + activity log
- Panels are resizable via drag handles. Config panels move to Configuration tab or Settings page.

### 🔴 Gap 4: Data Tables Have No Sorting/Filtering/Resizing

**What NT/TV have:** NinjaTrader Grid Pro: sort by any column, filter by symbol/P&L, resize columns, pin columns, row grouping, row expansion for details. TradingView: sortable watchlists, filterable screeners. IBKR TWS: sortable portfolio with column customization.

**What we have:** Raw HTML `<table>` in PositionsPage, PositionHistory, StockList — no sorting, no filtering, no column resize, no pagination. Positions cannot be sorted by P&L to see worst performers first.

**Implementation:** `@tanstack/react-table` (~15 KB) headless data table with shadcn table primitives. Features: column sorting (click header), column filtering (dropdown), column resizing (drag), column pinning (Symbol + P&L always visible), row expansion (click → details), row selection (batch close), pagination (trade history), virtual scroll (for 100+ rows).

## 13.3 High-Impact UI Improvements

### 🟡 Gap 5: No Toast/Notification System for Trade Events

**What NT/TV have:** NinjaTrader: audio + visual alerts on trade fill, stop loss hit, order rejection, connection events. TradingView: configurable alert system with push notifications, email, webhooks.

**What we have:** Custom `Toaster.tsx` exists but barely used. No notifications for trade fills, SL/TP hits, TWS connection changes, P&L limit warnings.

**Implementation:** `sonner` (~5 KB) — rich toasts with actions, stacking, progress bars, custom icons. Events: trade_executed → success toast with P&L, trade_closed (SL/TP) → warning toast, TWS disconnect → persistent error toast, P&L limit near → warning toast, Emergency stop → destructive toast.

### 🟡 Gap 6: Header Missing Market Context Ticker Strip

**What NT/TV have:** TradingView: scrolling ticker strip showing watchlist prices. NinjaTrader: market analyzer bar with key indices. Bloomberg: running ticker tape.

**What we have:** Header shows P&L, trades, clock — good but no quick market context. SPY/QQQ prices are buried in MarketOverview on Signals tab.

**Implementation (no new deps):** Add inline mini-tickers in Header showing SPY/QQQ/VIX last price + change from `dataStatus.stock_ticks_sample`. Compact format: `SPY 590.42 +0.3%`. Updates with data_status events (~10s).

### 🟡 Gap 7: No Bottom Status Bar

**What NT/TV have:** NinjaTrader: bottom bar showing connection latency, memory usage, processing status, market session hours. TradingView: bottom bar with market status (pre-market/open/closed), time to close.

**What we have:** TWS status buried in sidebar footer. No global status bar.

**Implementation (no new deps):** Slim 24px status bar below main content: TWS connection status, engine uptime, event queue size, market hours countdown ("Closes in 2h 34m"), data freshness timestamp, theme label. Monospace font, muted colors, border-t separator.

### 🟡 Gap 8: Sidebar is Navigation-Only

**What NT/TV have:** NinjaTrader: sidebar with watchlist, order management, account tabs. TradingView: sidebar with alerts, ideas, watchlist, news.

**What we have:** 5 nav links + connection status + session stats. No market data in sidebar.

**Implementation (no new deps):** Add a "Watchlist" section below navigation showing subscribed symbols with live prices from `dataStatus.stock_ticks_sample`. Show symbol, last price, change direction arrow. Clicking a symbol could switch the chart.

### 🟡 Gap 9: Missing Position Table Columns

**What NT/TV have:** NinjaTrader: Time in trade, Greeks (delta, gamma, theta, vega), risk %, entry time, strategy name, order type, commission. TradingView: cost basis, unrealized %, day change.

**Current columns (9):** Symbol, Type, Strike, Expiry, Qty, Avg, Current, P&L, Close.

**Missing columns:** Time held (e.g. "12m 34s"), Delta, Entry time/date, Strategy name (SuperTrend/Engulfing), Risk % of account (P&L / NetLiquidation), Max risk (entry-SL × qty × 100).

### 🟡 Gap 10: No Options Chain View

**What NT have:** Full options chain grid: strikes as rows, calls on left, puts on right. Columns: bid, ask, last, volume, OI, delta, gamma, theta, IV for each side. Expiry tabs across top.

**What we have:** StockList component showing symbol badges. No options chain display.

**Implementation:** New `OptionsChain.tsx` component. Data: already available from TWS via `client.get_strikes()` and option subscriptions. Show as a table with strike prices centered, calls on left, puts on right, with bid/ask/delta/volume.

### 🟡 Gap 11: Analytics Charts Need Interactivity

**What TV have:** Zoom with mouse wheel, pan with drag, crosshair with OHLCV legend, multi-timeframe toggle, time range buttons (1D/1W/1M/YTD).

**Current:** Recharts charts are static — basic tooltip on hover, no zoom, no pan, no time range selection. Fixed 220px height.

**Improvement (no new deps):** Add time range buttons (last 10/25/50/all trades), larger chart height (300px+), better Recharts tooltips showing more context (symbol, entry/exit time, strategy). Later: replace with Lightweight Charts for full interactivity.

### 🟡 Gap 12: No Risk/Exposure Dashboard

**What NT have:** Risk dashboard with margin utilization %, portfolio Greeks (total delta, gamma, theta, vega), sector/symbol exposure pie chart, max drawdown, VaR.

**Current:** Basic risk card with profit target/loss limit inputs + two progress bars (P&L vs target, trades vs max).

**Missing:** Portfolio-level Greeks summary, margin utilization gauge (MaintMarginReq / NetLiquidation), position concentration (% of portfolio per symbol), buying power utilization (used / available), daily drawdown from high-water mark.

## 13.4 Polish & Quality-of-Life Improvements

### 🟢 No-Install Improvements (Existing Dependencies Only)

| # | Feature | Description | Component(s) | Effort |
|---|---------|-------------|--------------|--------|
| 1 | **Market hours countdown** | "Closes in 2h 34m" / "Opens in 14h 5m" in header or status bar | Header.tsx or new StatusBar.tsx | Small |
| 2 | **Stale data indicator** | Badge showing "STALE" when last data_status > 30s ago; dim data values | DataFeedStatus, MarketOverview, LiveStats | Small |
| 3 | **Reduced motion support** | `@media (prefers-reduced-motion: reduce)` disabling all non-essential animations | index.css | Small |
| 4 | **Compact/density mode toggle** | Setting to switch between comfortable (14px) and compact (12px, tighter padding) mode | Settings, AppShell, index.css | Medium |
| 5 | **Position row expand** | Click position row → expand to show entry time, strategy, order ID, TP/SL levels, trade timeline | PositionRow.tsx | Medium |
| 6 | **Hover cards for symbols** | Hover over any symbol text → popup showing last price, daily change, bid/ask, volume | New HoverSymbolCard.tsx | Medium |
| 7 | **Session summary card** | Auto-generated end-of-day summary: total trades, P&L, best/worst, win rate, time in market | New SessionSummary.tsx | Medium |
| 8 | **Animated number counters** | Smooth count-up animation when stat values change (not just flash) | StatCard.tsx | Small |
| 9 | **Better empty state CTAs** | Add actionable buttons in empty states (e.g. "Start Trading" button in empty positions) | PositionsPage, AnalyticsPage | Small |
| 10 | **Table header sorting (basic)** | Click-to-sort with useState for position/trade tables (before TanStack upgrade) | PositionsPage, PositionHistory | Medium |
| 11 | **Header mini market tickers** | SPY/QQQ inline prices from dataStatus in header bar | Header.tsx | Small |
| 12 | **Sidebar watchlist** | Mini symbol price list below navigation using dataStatus ticks | Sidebar.tsx | Medium |
| 13 | **Right-click context menus** | Position row: Close, Adjust TP/SL, View Logs, Copy Symbol | PositionRow.tsx (needs shadcn dropdown-menu) | Medium |
| 14 | **Chart grid background** | Subtle dot/grid pattern in dark mode for chart/card backgrounds | index.css | Small |
| 15 | **Signal outcome tracking** | Show won/lost/skipped status on signal entries in SignalActivity | SignalActivity.tsx | Medium |
| 16 | **Time held per position** | Calculate elapsed time from trade execution timestamp, show "12m 34s" | PositionRow.tsx | Small |
| 17 | **Progress ring for risk** | Circular progress gauge for margin utilization, daily P&L vs limit | New ProgressRing.tsx | Medium |
| 18 | **Trade execution replay** | Click closed trade → mini chart showing entry/exit price markers | PositionHistory.tsx (needs Lightweight Charts) | Large |
| 19 | **Log regex search** | Upgrade log search from simple includes to regex-capable | LogsPage.tsx | Small |
| 20 | **Settings search** | Search/filter within settings page | SettingsPage.tsx | Medium |

## 13.5 Feature Priority Matrix (NinjaTrader/TradingView Parity)

| Phase | Features | Libraries Needed | UX Impact |
|-------|----------|-----------------|-----------|
| **Phase A — Chart-First** | TradingView candlestick chart, multi-panel dashboard layout, timeframe selector, symbol switcher | `lightweight-charts`, `react-resizable-panels` | 🔴 **Transformational** — single biggest UX improvement |
| **Phase B — Keyboard Power** | Command palette (⌘K), global hotkeys (Ctrl+1-5, Ctrl+Shift+S/X/E), bottom status bar | `cmdk` | 🔴 **Essential** — pro traders are keyboard-first |
| **Phase C — Data Grid** | TanStack Table for positions/trades, column sort/filter/resize/pin, row expansion, pagination | `@tanstack/react-table` | 🟡 **Major** — data management and analysis |
| **Phase D — Notifications** | Sonner toasts for trade fills, SL/TP, connection, P&L alerts, audio support | `sonner` | 🟡 **Professional** — real-time event awareness |
| **Phase E — No-Install Polish** | Header tickers, status bar, compact mode, market hours countdown, hover cards, stale data, reduced motion, position expand, watchlist sidebar, signal outcomes | None | 🟢 **Quality** — polished professional feel |
| **Phase F — Advanced** | Options chain view, risk/exposure dashboard, portfolio Greeks, trade execution replay, right-click menus, session summary | Mixed | 🟢 **Premium** — power user features |

---

# PART XIV – Modern UI Design System Specification

A pixel-perfect design system specification to transform QuantDrift from a functional trading dashboard into a **Bloomberg/NinjaTrader/TradingView-class** professional trading terminal. Every detail below is actionable and mapped to existing components.

## 14.1 Design Philosophy

**Core Principles:**
- **Data Density** — maximize information per pixel; traders want to see everything at once
- **Glanceable** — critical data (P&L, positions, signals) readable in < 1 second
- **Keyboard-First** — every action reachable via keyboard; mouse is secondary
- **Zero Surprise** — consistent patterns, predictable animations, no layout shifts
- **Dark-First** — dark theme is the default for professional traders (reduces eye strain on multi-monitor setups)

**Design Language:**
- **No rounded corners > 8px** — sharp, technical feel (reduce --radius from 0.625rem to 0.375rem)
- **Monospace for all numbers** — tabular-nums everywhere financial data appears
- **High contrast text** — foreground/muted ratio minimum 4.5:1 (WCAG AA)
- **Minimal color palette** — only P&L green/red, signal blue/purple, and neutral grays
- **1px borders everywhere** — clean separation, no heavy shadows

## 14.2 Typography System

### Font Stack (Current → Target)

| Use | Current | Target | Reason |
|-----|---------|--------|--------|
| **UI Text** | Inter | **Inter** (keep) | Industry standard for data-dense UIs |
| **Numbers/Prices** | JetBrains Mono | **JetBrains Mono** (keep) | Excellent tabular figures, clear $ and decimal alignment |
| **Branding** | Inter | **Geist** (add) | Modern, sharp, pairs well with Inter for headings |
| **Logs/Terminal** | JetBrains Mono | **IBM Plex Mono** (add) | Better readability at small sizes for log output |

### Type Scale (Pixel-Perfect)

| Token | Size | Line Height | Weight | Use |
|-------|------|-------------|--------|-----|
| `text-3xs` | 9px (0.5625rem) | 12px | 500 | Micro labels (timestamp seconds, gauge ticks) |
| `text-2xs` | 10px (0.625rem) | 14px | 500 | Labels, badges, secondary info |
| `text-xs` | 11px (0.6875rem) | 16px | 400/500 | Default body text, table cells |
| `text-sm` | 12px (0.75rem) | 18px | 400/600 | Card titles, nav items |
| `text-base` | 13px (0.8125rem) | 20px | 400 | Primary content |
| `text-lg` | 15px (0.9375rem) | 22px | 600 | Page titles |
| `text-xl` | 18px (1.125rem) | 24px | 700 | Hero numbers (total P&L) |
| `text-2xl` | 22px (1.375rem) | 28px | 700 | Dashboard hero stat |
| `text-3xl` | 28px (1.75rem) | 32px | 800 | Splash/onboarding numbers |

### Typography Rules

1. **All financial numbers** use `font-mono tabular-nums` — no exceptions
2. **Currency values** always show 2 decimal places: `$1,234.56`
3. **Percentages** show 1 decimal: `+12.3%`
4. **Large numbers** use compact notation above 10K: `$12.3K`, `$1.2M`
5. **Negative values** use color (red) + minus sign, not parentheses
6. **Timestamps** in log: `HH:mm:ss.SSS` format (24-hour, milliseconds)
7. **Dates** in header: `Mon Feb 25` (short weekday, short month)

## 14.3 Color System (Complete Token Specification)

### Base Palette (Dark Theme — Primary)

```
Background layers (darkest → lightest):
  --bg-0:     hsl(230, 21%, 6%)     // App background
  --bg-1:     hsl(228, 22%, 9%)     // Card / sidebar
  --bg-2:     hsl(226, 20%, 12%)    // Elevated cards, modals
  --bg-3:     hsl(224, 18%, 16%)    // Hover states, active items

Border hierarchy:
  --border-0: hsl(223, 16%, 14%)    // Subtle (between same-level)
  --border-1: hsl(223, 16%, 20%)    // Default (cards, inputs)
  --border-2: hsl(223, 16%, 28%)    // Emphasized (focused, active)

Text hierarchy:
  --text-0:   hsl(213, 31%, 91%)    // Primary text
  --text-1:   hsl(215, 20%, 65%)    // Secondary text
  --text-2:   hsl(218, 11%, 45%)    // Tertiary / muted
  --text-3:   hsl(218, 11%, 30%)    // Disabled / decorative
```

### Semantic Trading Colors

```
P&L / Direction:
  --profit:       hsl(160, 84%, 39%)   // #10B981 — emerald-500
  --profit-muted: hsl(160, 84%, 39% / 0.15)
  --loss:         hsl(0, 63%, 55%)     // #DC5656
  --loss-muted:   hsl(0, 63%, 55% / 0.15)

Signal:
  --signal-call:  hsl(160, 84%, 39%)   // Same as profit
  --signal-put:   hsl(0, 63%, 55%)     // Same as loss
  --signal-strong: hsl(217, 92%, 65%)  // Blue — high confidence

Order Status:
  --order-pending:  hsl(38, 92%, 50%)  // Amber
  --order-filled:   hsl(160, 84%, 39%) // Green
  --order-rejected: hsl(0, 63%, 55%)   // Red
  --order-partial:  hsl(217, 92%, 65%) // Blue

Greeks:
  --delta:  hsl(217, 92%, 65%)   // Blue
  --gamma:  hsl(280, 65%, 60%)   // Purple
  --theta:  hsl(38, 92%, 50%)    // Amber (time decay = warm)
  --vega:   hsl(160, 84%, 39%)   // Green (volatility)

Chart:
  --candle-up-body:    hsl(160, 84%, 39%)
  --candle-up-wick:    hsl(160, 84%, 39% / 0.6)
  --candle-down-body:  hsl(0, 63%, 55%)
  --candle-down-wick:  hsl(0, 63%, 55% / 0.6)
  --chart-grid:        hsl(223, 16%, 14%)
  --chart-crosshair:   hsl(218, 11%, 45%)
  --chart-volume:      hsl(217, 92%, 65% / 0.3)
  --chart-supertrend:  hsl(280, 65%, 60%)
  --chart-ema:         hsl(38, 92%, 50% / 0.6)

Severity (Logs):
  --log-error:   hsl(0, 63%, 55%)
  --log-warn:    hsl(38, 92%, 50%)
  --log-info:    hsl(217, 92%, 65%)
  --log-debug:   hsl(218, 11%, 45%)
  --log-trade:   hsl(160, 84%, 39%)
  --log-signal:  hsl(280, 65%, 60%)
```

### Light Theme Adjustments

```
Background: swap direction (lightest → darkest)
  --bg-0: hsl(220, 16%, 96%)
  --bg-1: hsl(0, 0%, 100%)
  --bg-2: hsl(0, 0%, 100%)
  --bg-3: hsl(220, 14%, 96%)

Text: invert brightness
  --text-0: hsl(224, 71%, 4%)
  --text-1: hsl(220, 9%, 36%)
  --text-2: hsl(220, 9%, 56%)
  --text-3: hsl(220, 9%, 76%)

Trading colors: increase saturation for light backgrounds
  --profit: hsl(160, 84%, 32%)  // Darker green on white
  --loss:   hsl(0, 84%, 48%)    // Darker red on white
```

## 14.4 Spacing & Layout System

### Spacing Scale

| Token | Value | Use |
|-------|-------|-----|
| `space-0.5` | 2px | Inline gaps (icon + text) |
| `space-1` | 4px | Tight padding (badges, small buttons) |
| `space-1.5` | 6px | Default icon-text gap |
| `space-2` | 8px | Card internal padding (compact mode) |
| `space-2.5` | 10px | Input padding, small gaps |
| `space-3` | 12px | Default card padding |
| `space-4` | 16px | Section gaps, card headers |
| `space-5` | 20px | Page padding (main content) |
| `space-6` | 24px | Major section separation |
| `space-8` | 32px | Page-level spacing |

### Layout Grid

```
┌─────────────────────────────────────────────────────────────────┐
│ Header (h-12, 48px)                                             │
│ [LIVE] [P&L +$234.56] [R:$180 U:$54] [Trades: 7]  [SPY 590.42 +0.3%] [QQQ 510.21 -0.1%] [VIX 14.2]  [10:34:22 ET Mon Feb 25] [Demo/Live] [☾] │
├──────────┬──────────────────────────────────────────────────────┤
│ Sidebar  │ Main Content Area                                     │
│ (w-220)  │                                                       │
│          │ ┌─────────────────────────────────────────────────┐   │
│ [Logo]   │ │ Chart Panel (50-60% height)                     │   │
│          │ │ [OHLCV Candlestick + SuperTrend + Signals]      │   │
│ ─ Menu   │ │ [Timeframe: 1m|5m|15m|1h] [Symbol: SPY▾]       │   │
│ Dashboard│ └─────────────────────────────────────────────────┘   │
│ Analytics│ ┌──────────────────────┬──────────────────────────┐   │
│ Positions│ │ Positions Panel      │ Signals & Account Panel  │   │
│ Logs     │ │ (30% height)         │ (30% height)             │   │
│ Settings │ │ [Active positions]   │ [Signal timeline]        │   │
│          │ │ [Sort/Filter/Expand] │ [Account summary]        │   │
│ ─ Watch  │ └──────────────────────┴──────────────────────────┘   │
│ SPY 590  │                                                       │
│ QQQ 510  │                                                       │
│          │                                                       │
│ ─ Status │                                                       │
│ TWS: ✓   │                                                       │
│ License  │                                                       │
│ LIVE     │                                                       │
├──────────┴──────────────────────────────────────────────────────┤
│ Status Bar (h-6, 24px)                                           │
│ [TWS: Connected ✓] [Engine: 45m 12s] [Queue: 0] [Closes in 2h 34m] [Data: 2s ago] [v1.0.0] │
└─────────────────────────────────────────────────────────────────┘
```

### Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| `sm` | < 768px | Not supported (desktop app) |
| `md` | 768-1024px | Sidebar collapsed (icons only, w-14), single-column panels |
| `lg` | 1024-1440px | Full sidebar, 2-column panels below chart |
| `xl` | 1440-1920px | Full layout, 3-column stat cards |
| `2xl` | > 1920px | Ultra-wide: chart + side panel side-by-side |

### Compact Mode (Trading Density)

| Property | Normal | Compact |
|----------|--------|---------|
| Base font | 14px | 12px |
| Card padding | 12px | 8px |
| Table row height | 36px | 28px |
| Button height | 36px | 28px |
| Input height | 36px | 28px |
| Stat card padding | 16px | 10px |
| Section gap | 16px | 8px |
| Header height | 48px | 36px |
| Sidebar width | 220px | 180px |

Implementation: CSS class `.compact` on `<html>` element, toggled from Settings.

## 14.5 Component Design Specifications

### Card Component (Current → Modern)

**Current issues:**
- Generic white/dark card with thick rounded corners (radius 10px)
- No visual hierarchy between card types
- Inconsistent padding

**Modern spec:**
```
.card-base {
  background: var(--bg-1);
  border: 1px solid var(--border-1);
  border-radius: 6px;                  // Reduced from 10px
  box-shadow: none;                    // Remove shadow in dark mode
  transition: border-color 0.15s;
}
.card-base:hover {
  border-color: var(--border-2);       // Subtle hover feedback
}
.card-header {
  padding: 10px 12px;                  // Tighter
  border-bottom: 1px solid var(--border-0);
  background: var(--bg-1);
}
.card-content {
  padding: 12px;
}
```

**Card variants:**
| Variant | Use | Visual |
|---------|-----|--------|
| `default` | Most cards | bg-1, border-1 |
| `elevated` | Modals, popovers | bg-2, border-2, shadow-elevated |
| `accent` | Active/selected | border-primary/30, subtle primary glow |
| `danger` | Emergency, errors | border-destructive/30, red-tinted bg |
| `glass` | Overlays on chart | bg-1/80, backdrop-blur-12 |

### Button Component (Current → Modern)

**Current issues:**
- Buttons look generic, no trading-specific variants
- Start/Stop/Emergency have same visual weight

**Modern spec — additional variants:**

| Variant | Use | Style |
|---------|-----|-------|
| `trading-start` | Start Trading | bg-emerald-600, font-bold, h-11, uppercase, letter-spacing-wider |
| `trading-stop` | Stop Trading | border-2 border-amber-500, text-amber-500, h-11 |
| `trading-emergency` | Emergency Stop | bg-red-600, animate-pulse-subtle on hover, h-11 |
| `icon-sm` | Toolbar actions | h-7 w-7, rounded-md, ghost hover |
| `chip` | Filter toggles | h-6, rounded-full, bg-muted, text-2xs |

### Input Component (Current → Modern)

**Modern spec:**
```
height: 32px (compact: 28px)
padding: 0 8px
font-size: 12px
background: var(--bg-0)           // Slightly recessed
border: 1px solid var(--border-1)
border-radius: 4px                // Sharper
focus: ring-2 ring-primary/20, border-primary/50

Numeric inputs:
  font-family: 'JetBrains Mono'
  text-align: right
  tabular-nums
```

### Table Component (Current → Modern)

**Current issues:**
- Basic HTML table, no sort/filter
- No column resizing or pinning
- No zebra striping or hover highlight
- No expandable rows

**Modern spec (before TanStack Table):**
```
Header:
  height: 32px
  background: var(--bg-0)
  font: 10px/14px uppercase, tracking-wider, 600 weight
  color: var(--text-2)
  border-bottom: 1px solid var(--border-1)
  cursor: pointer (sortable columns)
  sort indicator: ▲/▼ next to active column

Row:
  height: 36px (compact: 28px)
  border-bottom: 1px solid var(--border-0)
  hover: bg-muted/30
  transition: background 0.1s

  Active/selected row:
    bg-primary/5, border-l-2 border-primary

Cell types:
  .cell-symbol { font-mono, font-bold, text-sm }
  .cell-price  { font-mono, tabular-nums, text-right }
  .cell-pnl    { font-mono, tabular-nums, color by sign }
  .cell-badge  { centered badge }
  .cell-action { opacity-0 → opacity-100 on row hover }

Expandable row:
  Click row → animate-expand panel below
  Shows: entry time, strategy, order type, TP/SL levels, order timeline
  Background: var(--bg-0), border-l-2 border-primary
```

### Badge Component (New Variants)

| Variant | Use | Style |
|---------|-----|-------|
| `signal-call` | CALL signals | bg-emerald-500/15, text-emerald-500, border-emerald-500/20 |
| `signal-put` | PUT signals | bg-red-500/15, text-red-500, border-red-500/20 |
| `signal-strong` | High confidence | bg-blue-500/15, text-blue-500, border-blue-500/20 |
| `filled` | Order filled | bg-emerald-500/15 |
| `pending` | Order pending | bg-amber-500/15, animate-pulse |
| `rejected` | Order rejected | bg-red-500/15 |
| `live` | Live dot | h-2 w-2 rounded-full bg-emerald-500 animate-pulse |
| `stale` | Data is old | bg-amber-500/15, text-amber-500 |
| `count` | Number pill | h-5 min-w-5 rounded-full bg-destructive text-white text-2xs |

## 14.6 Animation & Motion System

### Animation Principles
1. **Functional, not decorative** — every animation communicates state change
2. **Duration: 100-300ms max** — traders don't wait for animations
3. **Ease: ease-out for entrances, ease-in for exits**
4. **Reduced motion: all animations respect `prefers-reduced-motion: reduce`**

### Animation Catalog

| Name | Duration | Easing | Trigger | CSS |
|------|----------|--------|---------|-----|
| `pnl-flash-profit` | 600ms | ease-out | P&L value increases | bg-emerald-500/18 → transparent |
| `pnl-flash-loss` | 600ms | ease-out | P&L value decreases | bg-red-500/18 → transparent |
| `count-up` | 300ms | ease-out | Number changes | opacity + translateY(4px→0) + number interpolation |
| `fade-up` | 200ms | ease-out | Content enters | opacity(0→1) + translateY(4px→0) |
| `slide-in-right` | 200ms | ease-out | Panel enters | opacity(0→1) + translateX(8px→0) |
| `signal-glow` | 1500ms | ease-in-out, once | New signal detected | box-shadow pulse 0→4px→0 |
| `live-pulse` | 2000ms | ease-in-out, infinite | Live indicator dot | scale(1→0.8→1) + opacity(1→0.4→1) |
| `skeleton-shimmer` | 1800ms | ease-in-out, infinite | Loading state | gradient slide left→right |
| `expand-down` | 200ms | ease-out | Row expand | height(0→auto) + opacity(0→1) |
| `toast-in` | 200ms | ease-out | Toast appears | translateY(100%→0) + opacity(0→1) |
| `toast-out` | 150ms | ease-in | Toast dismisses | translateY(0→100%) + opacity(1→0) |
| `chart-crosshair` | 0ms | instant | Mouse move on chart | CSS pointer tracking (no animation) |
| `tab-underline` | 150ms | ease-out | Tab switch | width + translateX |
| `progress-fill` | 300ms | ease-out | Progress change | width transition |
| `border-pulse` | 2000ms | ease-in-out, 3× | Error/warning state | border-color opacity pulse |

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .live-dot { animation: none; opacity: 1; }
  .skeleton { animation: none; background: var(--muted); }
}
```

## 14.7 Micro-Interaction Specifications

### 1. P&L Value Change (Header, StatCard, PositionRow)
```
Trigger: value changes
Behavior:
  1. Compare new vs old value
  2. If increased: apply .pnl-flash-profit (green bg flash 600ms)
  3. If decreased: apply .pnl-flash-loss (red bg flash 600ms)
  4. Number smoothly transitions via CSS transition (color, font-weight)
```

### 2. Trade Fill Toast
```
Trigger: trading:trade_executed event
Behavior:
  1. Sonner toast slides up from bottom-right
  2. Icon: CheckCircle (green) for profit, XCircle (red) for loss
  3. Content: "CALL SPY 590 +$45.20" (direction, symbol, strike, P&L)
  4. Auto-dismiss: 5 seconds
  5. Click: navigate to /positions
  6. Audio: optional short chime (configurable in Settings)
```

### 3. Signal Detected Glow
```
Trigger: trading:signal_detected event
Behavior:
  1. SignalActivity panel: new entry slides in from right
  2. Entry has box-shadow glow animation (1.5s, once)
  3. Badge shows "CALL" or "PUT" with strength (Strong/Medium/Weak)
  4. Optional: toast notification "CALL signal detected on SPY"
```

### 4. TWS Connection State
```
Trigger: trading:connection_status event
Behavior:
  Connected:
    - Header: remove tws-disconnected-border
    - Sidebar: green badge, "TWS Connected"
    - Toast: "Connected to TWS" (info, 3s)
  Disconnected:
    - Header: add 2px red top border (animated)
    - Sidebar: red badge, "TWS Disconnected", "Reconnecting…" subtitle
    - Toast: "TWS Disconnected — reconnecting…" (error, persistent until reconnect)
    - Status bar: "TWS: ✗ Disconnected" in red
```

### 5. Button State Transitions
```
Start Trading:
  Idle → hover: slight scale(1.01), bg brightens
  Click → Starting: spinner animation, text changes to "Starting…"
  Started: brief green flash, text "LIVE"

Emergency Stop:
  Hover: subtle pulse animation on border
  Click: immediate red flash, text "Stopping…"
  Confirmation dialog: slide-down with overlay fade
```

### 6. Position Row Interactions
```
Hover:
  - Background: var(--bg-3) transition 100ms
  - Close button fades in (opacity 0→1, 100ms)
  - Trend icon appears (▲/▼ next to symbol)
  - Cursor: pointer if expandable

Click (with TanStack):
  - Row expands downward (expand-down 200ms)
  - Shows: entry time, strategy, TP/SL, order timeline
  - Blue left border on expanded row

P&L cell:
  - Value change: flash animation (same as header P&L)
  - Gauge bar: smooth width transition (300ms)
```

## 14.8 Icon System

### Icon Library: Lucide React (current, keep)

**Icon sizing rules:**
| Context | Size | Class |
|---------|------|-------|
| Nav items | 18px | `h-[18px] w-[18px]` |
| Card headers | 14px | `h-3.5 w-3.5` |
| Inline with text | 12px | `h-3 w-3` |
| Status indicators | 8-10px | `h-2 w-2` to `h-2.5 w-2.5` |
| Page titles | 20px | `h-5 w-5` |
| Hero/empty states | 32px | `h-8 w-8` |
| Tooltip triggers | 14px | `h-3.5 w-3.5` |

### Trading-Specific Icon Mapping

| Concept | Icon | Color |
|---------|------|-------|
| CALL/Long | `TrendingUp` | emerald-500 |
| PUT/Short | `TrendingDown` | red-500 |
| Neutral | `Minus` | muted-foreground |
| Signal detected | `Zap` | amber-500 |
| Order filled | `CheckCircle` | emerald-500 |
| Order rejected | `XCircle` | red-500 |
| Order pending | `Clock` | amber-500 |
| SuperTrend | `Activity` | violet-500 |
| Engulfing | `CandlestickChart` | blue-500 |
| Risk/Warning | `AlertTriangle` | amber-500 |
| Critical error | `AlertOctagon` | red-500 |
| P&L | `DollarSign` | foreground |
| Win rate | `Target` | emerald-500 |
| Trading active | `Radio` | emerald-500 + live-dot |

## 14.9 Component-by-Component Modernization Plan

### Header.tsx — Modernization Details

**Current state:** P&L display, clock, mode toggle, theme toggle

**Additions:**
1. **Market tickers strip** (between left stats and right clock)
   - Format: `SPY 590.42 ▲ +0.31%  ·  QQQ 510.21 ▼ -0.12%  ·  VIX 14.2 ▼ -2.1%`
   - Data: extract from `dataStatus.stock_ticks_sample` (already available)
   - Update: every data_status event (~10s)
   - Size: `text-2xs font-mono tabular-nums`
   - Color: green/red based on change direction
   
2. **Market hours countdown**
   - Format: `Closes in 2h 34m` (during market hours) or `Opens in 14h 22m` (after hours)
   - Calculate from current ET time vs 9:30 AM / 4:00 PM ET
   - Position: next to clock, muted text
   - Pre-market (7:00-9:30): show `Pre-market · Opens in Xh Xm`
   - After hours (4:00-8:00): show `After hours · Opens in Xh Xm`

3. **Stale data indicator**
   - If last `data_status` event > 30s ago: show amber `⚠ Data stale` badge
   - If > 60s: show red `⚠ No data` badge
   - Track with `useRef(Date.now())` updated on each data_status event

### Sidebar.tsx — Modernization Details

**Current state:** Nav, session stats, TWS status, license, mode

**Additions:**
1. **Collapsible on medium screens** (< 1024px)
   - Toggle button at top: expand/collapse
   - Collapsed: w-14, show only icons + tooltips
   - Expanded: w-220 (current)
   - Animate with `transition-all duration-200`

2. **Watchlist section** (below navigation, above session stats)
   - Title: "WATCHLIST" (2xs, uppercase, tracking-widest)
   - Symbols from `tradingConfig.symbols`
   - Each row: `SPY  590.42  ▲` (symbol, price, direction)
   - Price from `dataStatus.stock_ticks_sample`
   - Click: future — switch chart symbol
   - Limit: show max 8 symbols, scroll if more

3. **Active position count** on Positions nav item
   - Badge showing number of active positions (like error count on Logs)
   - Only show when > 0

### DashboardPage.tsx — Modernization Details (Multi-Panel Layout)

**Current:** Tab-based layout with Overview/Signals/Config/Activity tabs

**Target:** Multi-panel layout (Phase A dependency: `react-resizable-panels`)

**Interim improvements (no new deps):**
1. Move chart placeholder to top of Overview tab (future candlestick area)
2. Add "No chart yet — coming soon" placeholder with trading chart wireframe
3. Move Config tab content to Settings page entirely
4. Make Overview the default and primary view
5. Reduce tab count from 4 → 2 (Overview, Activity)

**Final layout (with react-resizable-panels):**
```
<PanelGroup direction="vertical">
  <Panel defaultSize={55} minSize={30}>  <!-- Chart -->
    <TradingChart />
  </Panel>
  <PanelResizeHandle />
  <Panel defaultSize={45} minSize={20}>
    <PanelGroup direction="horizontal">
      <Panel defaultSize={60}>  <!-- Positions -->
        <PositionsPanel />
      </Panel>
      <PanelResizeHandle />
      <Panel defaultSize={40}>  <!-- Signals + Account -->
        <Tabs>
          <SignalActivity />
          <AccountSummary />
          <ActivityLog />
        </Tabs>
      </Panel>
    </PanelGroup>
  </Panel>
</PanelGroup>
```

### PositionRow.tsx — Modernization Details

**Current:** Basic row with P&L gauge, hover close button

**Additions:**
1. **Time held column**: `12m 34s` calculated from `position.entry_time` (requires backend to include entry timestamp)
2. **Expandable detail panel** (click row):
   - Entry time, exit target (TP), stop loss (SL)
   - Strategy that triggered (SuperTrend/Engulfing)
   - Order type and status
   - Mini order timeline (placed → filled → monitoring → TP/SL)
3. **Inline TP/SL quick edit**: double-click TP/SL values to edit in-place
4. **Row priority coloring**: positions near TP glow green, near SL glow red

### LogsPage.tsx — Modernization Details

**Current:** Level filter, search, severity badges, category icons

**Additions:**
1. **Regex search toggle**: button next to search input to switch between simple/regex mode
2. **Log groups**: group consecutive logs from same trade lifecycle (entry → fill → monitor → exit)
3. **Timestamp precision**: show milliseconds (`10:34:22.145`) for debugging
4. **Copy log line**: hover → copy icon → click to copy full log JSON to clipboard
5. **Log level quick filters**: clickable badges at top that toggle filter
6. **Export**: button to download filtered logs as JSON/CSV
7. **Auto-scroll lock**: toggle to pause auto-scroll when user scrolls up
8. **Performance**: already virtualized; add estimated row count in footer

### SettingsPage.tsx — Modernization Details

**Current:** Basic cards with toggles and inputs

**Additions:**
1. **Settings search**: fuzzy search input at top, highlights matching settings
2. **Categories with icons**: group into Appearance, Trading, Connection, Strategy, UI, License
3. **Reset to defaults**: button per section
4. **Font size preview**: live preview of font size changes
5. **Keyboard shortcuts section**: display current bindings, allow customization
6. **Import/Export config**: button to export all settings as JSON, import from file
7. **Compact mode toggle**: with live preview
8. **Sound settings**: toggle audio alerts, select alert sounds
9. **Data update intervals**: configurable per data type (PnL, account, data status)

### AnalyticsPage.tsx — Modernization Details

**Current:** Tabs with Recharts bar/line/pie charts

**Improvements:**
1. **Time range selector**: buttons for Last 10 / 25 / 50 / All trades
2. **Chart height increase**: from 220px → 320px for better readability
3. **Better tooltips**: show symbol, entry/exit time, strategy on hover
4. **Drawdown chart** (new): visualize max drawdown over time
5. **Trade distribution** (new): scatter plot of P&L by time of day
6. **Symbol breakdown** (new): pie chart of trades by symbol
7. **Cumulative P&L with benchmark**: overlay SPY performance for comparison

## 14.10 Status Bar Specification

**Position:** Fixed at bottom of AppShell, below main content area

**Height:** 24px (6 units)

**Background:** `var(--bg-1)`, border-top: 1px solid `var(--border-0)`

**Font:** `text-2xs font-mono`

**Layout (left → right):**

```
[TWS: Connected ✓] | [Engine: 1h 23m] | [Queue: 0] | [Market: Open · Closes in 2h 34m] | [Data: 2s ago] | [Theme: Dark] | [v1.0.0]
```

| Section | Data Source | Update | Color |
|---------|-----------|--------|-------|
| TWS status | `connectedToTws` store | Real-time | Green/Red |
| Engine uptime | Track start time on `start_trading` | 1s interval | muted |
| Event queue | `data_status.queue_size` (if available) | 10s | muted |
| Market hours | Calculate from ET clock | 1m interval | muted/amber |
| Data freshness | Track last `data_status` timestamp | 1s interval | muted/amber/red |
| App version | From `package.json` | Static | muted |

## 14.11 Command Palette Specification

**Trigger:** `Ctrl+K` (Windows) / `⌘K` (Mac)

**Library:** `cmdk` (requires npm install)

**Design:**
```
Centered modal, 480px wide, max-h-[340px]
Background: var(--bg-2), border: var(--border-2)
Border-radius: 8px
Box-shadow: var(--shadow-elevated)
Backdrop: overlay var(--bg-0)/60, blur(4px)
```

**Search input:** Monospace, placeholder "Type a command…"

**Command Groups:**

| Group | Commands |
|-------|----------|
| **Navigation** | Go to Dashboard, Analytics, Positions, Logs, Settings |
| **Trading** | Start Trading, Stop Trading, Emergency Stop, Close All Positions |
| **View** | Toggle Theme, Toggle Compact Mode, Toggle Sidebar |
| **Data** | Refresh Positions, Clear Logs, Export Trades |
| **Quick** | Copy P&L, Copy Account ID, Show Keyboard Shortcuts |

**Keyboard shortcuts (global):**

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Open command palette |
| `Ctrl+1` | Go to Dashboard |
| `Ctrl+2` | Go to Analytics |
| `Ctrl+3` | Go to Positions |
| `Ctrl+4` | Go to Logs |
| `Ctrl+5` | Go to Settings |
| `Ctrl+Shift+S` | Start Trading |
| `Ctrl+Shift+X` | Stop Trading |
| `Ctrl+Shift+E` | Emergency Stop |
| `Ctrl+D` | Toggle Theme |
| `Ctrl+.` | Toggle Compact Mode |
| `Escape` | Close dialog/palette |

## 14.12 Toast Notification System

**Library:** `sonner` (requires npm install)

**Position:** bottom-right

**Max visible:** 3 stacked

**Auto-dismiss:** 5 seconds (configurable)

| Event | Type | Title | Description | Action |
|-------|------|-------|-------------|--------|
| Trade executed | success | "CALL Filled" | "SPY 590 C × 1 @ $2.45" | Click → /positions |
| Trade closed (profit) | success | "Trade Closed +$45.20" | "SPY 590 C — TP hit" | Click → /positions |
| Trade closed (loss) | error | "Trade Closed -$23.10" | "SPY 590 C — SL hit" | Click → /positions |
| Signal detected | info | "Signal: CALL SPY" | "SuperTrend — Strong" | Click → dashboard signals tab |
| TWS connected | success | "TWS Connected" | "" | 3s auto-dismiss |
| TWS disconnected | error | "TWS Disconnected" | "Reconnecting…" | Persistent until reconnect |
| P&L limit near | warning | "P&L Limit Warning" | "Daily P&L at 80% of target" | Click → risk panel |
| Emergency stop | destructive | "Emergency Stop" | "Engine killed, check positions" | Persistent |
| Config saved | success | "Config Saved" | "" | 2s auto-dismiss |
| License expiring | warning | "License Expiring" | "3 days remaining" | Click → /settings |

## 14.13 Glassmorphism & Visual Effects

### Glass Cards (for chart overlays)
```css
.glass-card {
  background: hsl(var(--bg-1) / 0.75);
  backdrop-filter: blur(12px) saturate(150%);
  -webkit-backdrop-filter: blur(12px) saturate(150%);
  border: 1px solid hsl(var(--border-1) / 0.5);
}
```

### Chart Grid Background
```css
.chart-grid-bg {
  background-image: radial-gradient(
    circle at 1px 1px,
    hsl(var(--border-0)) 1px,
    transparent 0
  );
  background-size: 24px 24px;
}
```

### Subtle Gradient Accents
```css
.gradient-profit {
  background: linear-gradient(135deg, hsl(160 84% 39% / 0.08), transparent);
}
.gradient-loss {
  background: linear-gradient(135deg, hsl(0 63% 55% / 0.08), transparent);
}
.gradient-hero {
  background: linear-gradient(180deg, hsl(var(--primary) / 0.05), transparent 60%);
}
```

### Focus Rings
```css
.focus-ring {
  outline: 2px solid hsl(var(--ring) / 0.3);
  outline-offset: 2px;
  border-color: hsl(var(--primary) / 0.5);
}
```

## 14.14 Accessibility Specifications

| Requirement | Implementation |
|-------------|----------------|
| **Color contrast** | All text meets WCAG AA (4.5:1 for normal, 3:1 for large) |
| **Focus visible** | Every interactive element has visible focus ring |
| **Keyboard nav** | Tab order follows visual layout, skip-to-main link |
| **Screen reader** | All icons have `aria-label`, status updates use `aria-live` |
| **Reduced motion** | All animations respect `prefers-reduced-motion` |
| **Color-blind safe** | P&L uses color + icon (▲/▼) + ±sign — never color alone |
| **Font scaling** | Layout works from 12px to 24px base font (Settings) |
| **High contrast** | Support `prefers-contrast: more` with increased border weights |

## 14.15 Performance Budget

| Metric | Target | Current Estimate |
|--------|--------|-----------------|
| **First Contentful Paint** | < 500ms | ~400ms (Vite + lazy routes) |
| **Time to Interactive** | < 1.5s | ~1s |
| **Re-render on PnL update** | < 2 components | 2-3 (throttled to 1s) |
| **Bundle size (gzip)** | < 250KB | ~180KB |
| **Lightweight Charts** | +45KB gzip | Lazy-loaded |
| **TanStack Table** | +15KB gzip | Lazy-loaded |
| **Sonner** | +5KB gzip | Lazy-loaded |
| **cmdk** | +4KB gzip | Lazy-loaded |
| **Total with all libs** | < 320KB gzip | ~249KB |
| **60fps during trading** | No frame drops | Monitor with React Profiler |
| **Memory (30min session)** | < 200MB | Track log buffer, position history |

---

# PART XII – Updated Priorities (Including UI Modernization)

| Priority | Area | Item | Section |
|----------|------|------|---------|
| ~~P0~~ | Backend | ~~Continuous PnL + IBKR account metrics~~ **Done** | §3.1 |
| **P0** | **Security** | **Fix SQL injection in data_access.py** | §10.1 |
| ~~P0~~ | Frontend | ~~Install shadcn/ui Phase 1 components (skeleton, tabs, alert, tooltip)~~ **Done** (no external deps, pure Tailwind) | §11.4 |
| **P0** | **Frontend** | **Install Lightweight Charts + TanStack Table + Sonner + cmdk** (requires npm install) | §11.3 |
| **P0** | **Frontend** | **Add TradingView candlestick chart to Dashboard** — single biggest UX gap vs NT/TV (§13.2 Gap 1) | §11.5, §11.8, §13.2 |
| **P0** | **Frontend** | **Multi-panel dashboard layout** — replace tabs with resizable chart-first panels (§13.2 Gap 3) | §13.2, §13.5 Phase A |
| **P1** | **Performance** | **Vectorize SuperTrend/BOTSingal** | §8.1 |
| **P1** | **Performance** | **Bar-close triggered signals** | §8.4 |
| **P1** | **Performance** | **Remove hard sleeps in init_data_feed** | §8.2 |
| **P1** | **Performance** | **Throttle PnL emit to 1s in engine** | §8.6 |
| **P1** | **Performance** | **Fix event_queue.get() block=True** | §8.4 |
| ~~P1~~ | Frontend | ~~Skeleton loading states for StatCard, LiveStats, AccountSummary, PositionsPage~~ **Done** | §11.9 Phase 1 |
| ~~P1~~ | Frontend | ~~P&L flash animations (Header, StatCard, PnLValue component)~~ **Done** | §11.9 Phase 1 |
| **P1** | **Frontend** | **Command palette (cmdk) + global keyboard shortcuts** — pro traders are keyboard-first (§13.2 Gap 2) | §11.7, §13.2, §13.5 Phase B |
| **P1** | **Frontend** | **Sonner toasts** — trade fill, SL/TP, connection, P&L alerts (§13.3 Gap 5) | §11.9, §13.3 |
| **P1** | **Frontend** | **Upgrade position/trade tables with TanStack Table** — sort, filter, resize, expand (§13.2 Gap 4) | §11.6, §13.2 |
| ~~P1~~ | Frontend | ~~Signal history timeline panel (SignalActivity component)~~ **Done** | §9.1, §11.9 Phase 2 |
| **P1** | **Frontend** | **Intraday P&L Curve** | §9.1 |
| ~~P1~~ | Frontend | ~~Position P&L gauge bar (PositionRow)~~ **Done** | §9.4 |
| ~~P1~~ | Frontend | ~~Log search + severity badges (LogsPage, ActivityLog, Sidebar)~~ **Done** | §9.2 |
| **P1** | **Frontend** | **Drawdown chart + risk metrics** | §9.3 |
| **P1** | **Frontend** | **Bottom status bar** — engine uptime, market hours countdown, data freshness (§13.3 Gap 7) | §13.3, §13.4 |
| **P1** | Backend | Options Greeks from TWS + greeks_update event | §10.3 |
| **P1** | Backend | reqPnLSingle for per-position P&L | §10.3 |
| **P1** | Backend | export_trades, health commands | §3.2 |
| ~~P1~~ | UI | ~~Trading color tokens (CSS variables) + thematic Tailwind colors~~ **Done** | §11.7, §5.2 |
| **P1** | **UI** | **Header mini market tickers** — SPY/QQQ/VIX inline prices (§13.3 Gap 6) | §13.3, §13.4 |
| **P1** | **UI** | **Stale data indicator** — badge when data_status > 30s old (§13.4) | §13.4 |
| **P1** | **UI** | **Market hours countdown** — "Closes in 2h 34m" in header/status bar (§13.4, §14.9) | §13.4, §14.9 |
| **P1** | **UI** | **Status bar component** — TWS, uptime, queue, market hours, data freshness, version (§14.10) | §14.10 |
| **P1** | **UI** | **Reduced border-radius** — 10px→6px for sharper pro terminal feel (§14.1, §14.5) | §14.5 |
| **P1** | **UI** | **Complete color token system** — bg-0/1/2/3, border-0/1/2, text-0/1/2/3 hierarchy (§14.3) | §14.3 |
| ~~P2~~ | Frontend | ~~Dashboard layout redesign (tabbed: Overview, Signals & Market, Config, Activity)~~ **Done** → to be replaced by multi-panel layout (§13.2) | §11.8 |
| ~~P2~~ | Frontend | ~~Market overview panel (live tick data grid)~~ **Done** | §9.1 |
| **P2** | **Frontend** | **Greeks per position display** | §9.4 |
| **P2** | **Frontend** | **Trade lifecycle log groups** | §9.2 |
| **P2** | **Frontend** | **Audio alerts + log persistence/export** | §9.2 |
| **P2** | **Frontend** | **Order flow panel** | §9.1 |
| **P2** | **Frontend** | **Quick adjust TP/SL from positions** | §9.4 |
| **P2** | **Frontend** | **Position row expand** — click to show entry time, strategy, TP/SL, order timeline (§13.4) | §13.4 |
| **P2** | **Frontend** | **Missing position columns** — time held, delta, strategy, risk % (§13.3 Gap 9) | §13.3 |
| **P2** | **Frontend** | **Options chain view** — strikes grid with calls/puts, bid/ask, greeks, volume (§13.3 Gap 10) | §13.3 |
| **P2** | **Frontend** | **Risk/exposure dashboard** — portfolio Greeks, margin gauge, concentration (§13.3 Gap 12) | §13.3 |
| **P2** | **Frontend** | **Sidebar watchlist** — mini symbol prices below navigation (§13.3 Gap 8) | §13.3, §13.4 |
| **P2** | **Frontend** | **Signal outcome tracking** — won/lost/skipped on signals (§13.4) | §13.4 |
| **P2** | **UI** | **Compact/density mode toggle** — 12px compact vs 14px comfortable (§13.4) | §13.4 |
| **P2** | **UI** | **Reduced motion support** — prefers-reduced-motion CSS (§13.4, §14.6) | §13.4, §14.6 |
| **P2** | **UI** | **Hover cards for symbols** — rich popup with price/change/bid/ask (§13.4) | §13.4 |
| **P2** | **UI** | **Glassmorphism effects** — glass cards for chart overlays, grid backgrounds (§14.13) | §14.13 |
| **P2** | **UI** | **Toast notification system** — Sonner with 10 event types mapped (§14.12) | §14.12 |
| **P2** | **UI** | **Type scale refinement** — text-3xs (9px), numeric inputs right-aligned mono (§14.2) | §14.2 |
| **P2** | **Frontend** | **Collapsible sidebar** — icons-only at <1024px with tooltips (§14.9) | §14.9 |
| **P2** | **Frontend** | **Settings page overhaul** — search, categories, reset, import/export (§14.9) | §14.9 |
| **P2** | **Frontend** | **Log groups + export** — trade lifecycle grouping, JSON/CSV export (§14.9) | §14.9 |
| **P2** | **Frontend** | **Analytics time range** — Last 10/25/50/All, chart height 320px, better tooltips (§14.9) | §14.9 |
| P2 | Performance | Event-based contract resolution, separate queues, batch logs | §8.3, §8.4, §8.6 |
| P2 | Backend | Config validation, class-based BOT, consolidated DB + loggers | §10.1 |
| ~~P2~~ | Frontend | ~~Store selectors (LiveStats, Header, Sidebar use individual selectors)~~ **Done** | §4.6 |
| ~~P2~~ | UI | ~~Micro-interactions (P&L flash, signal glow, TWS disconnect border, hover effects)~~ **Done** | §11.7 |
| **P3** | **Frontend** | **Session summary card** — auto end-of-day report (§13.4) | §13.4 |
| **P3** | **Frontend** | **Trade execution replay** — mini chart with entry/exit markers (§13.4) | §13.4 |
| **P3** | **Frontend** | **Right-click context menus** — position actions, symbol actions (§13.4) | §13.4 |
| **P3** | **Frontend** | **Settings search** — filter within settings page (§13.4) | §13.4 |
| **P3** | **Frontend** | **Log regex search** — upgrade from includes to regex (§13.4, §14.9) | §13.4, §14.9 |
| **P3** | **UI** | **Count-up animation** — smooth number interpolation for stat changes (§14.6) | §14.6 |
| **P3** | **UI** | **Accessibility audit** — WCAG AA contrast, aria-labels, focus rings, high-contrast mode (§14.14) | §14.14 |
| **P3** | **UI** | **Chart grid dot pattern** — subtle radial-gradient background for cards/chart area (§14.13) | §14.13 |
| **P3** | **Frontend** | **P&L heatmap, trade distribution, execution quality** | §9.1, §9.3 |
| **P3** | **Frontend** | **Strategy comparison, calendar trade history** | §9.3, §11.9 |
| P3 | Performance | msgpack IPC, numba SuperTrend | §8.6, §8.1 |
| P3 | Backend | Market depth, multi-day history | §10.3 |
| P3 | All | BOT.py TODO cleanup, tests, code signing | — |

---

# PART VII – Changelog (Roadmap)

- **Modern UI Design System Specification (v7):** Added **Part XIV – Modern UI Design System Specification** with 15 sub-sections covering every pixel-level detail for transforming QuantDrift into a Bloomberg/NinjaTrader/TradingView-class terminal: (§14.1) Design philosophy — 5 core principles (data density, glanceable, keyboard-first, zero surprise, dark-first) and design language rules (reduced radius 10px→6px, monospace for all numbers, 1px borders, minimal color); (§14.2) Complete typography system — font stack (Inter + JetBrains Mono + Geist headings + IBM Plex Mono logs), 10-level type scale (9px–28px) with line heights and weights, 7 typography rules for financial data formatting; (§14.3) Full color token specification — 35+ semantic tokens organized into background layers (bg-0/1/2/3), border hierarchy (border-0/1/2), text hierarchy (text-0/1/2/3), P&L, signal, order status, Greeks, chart (candle up/down, wick, grid, crosshair, volume, SuperTrend, EMA), and log severity colors, plus light theme adjustments; (§14.4) Complete spacing and layout system — 10-level spacing scale, detailed ASCII wireframe of target multi-panel layout, responsive breakpoints (md/lg/xl/2xl), and comprehensive compact mode specification (14 property differences); (§14.5) Component design specs — Card (5 variants: default/elevated/accent/danger/glass, reduced radius, tighter padding), Button (5 new trading variants: trading-start/stop/emergency/icon-sm/chip), Input (reduced height, recessed bg, monospace for numbers), Table (complete header/row/cell/expandable spec), Badge (10 new variants: signal-call/put/strong, filled/pending/rejected, live/stale/count); (§14.6) Animation system — 14 named animations with duration/easing/trigger/CSS specs, reduced-motion media query implementation; (§14.7) 6 micro-interaction specifications (P&L flash, trade fill toast, signal glow, TWS connection states, button transitions, position row hover/expand); (§14.8) Icon system — sizing rules for 7 contexts, 14 trading-specific icon-to-concept mappings with colors; (§14.9) Component-by-component modernization plan — Header (3 additions: market tickers, market hours, stale indicator), Sidebar (3 additions: collapsible, watchlist, position count badge), DashboardPage (interim 5-point improvement + final react-resizable-panels layout code), PositionRow (4 additions: time held, expandable panel, inline TP/SL edit, proximity coloring), LogsPage (8 additions: regex, groups, ms timestamps, copy, quick filters, export, auto-scroll lock, row count), SettingsPage (9 additions: search, categories, reset, preview, shortcuts, import/export, compact, sound, intervals), AnalyticsPage (7 additions: time range, height, tooltips, drawdown, distribution, symbol breakdown, benchmark); (§14.10) Status bar spec — 24px fixed bar with 7 sections (TWS, uptime, queue, market, data freshness, theme, version); (§14.11) Command palette spec — 480px modal, 5 command groups (25+ commands), 12 global keyboard shortcuts; (§14.12) Toast notification system — 10 event types mapped with type/title/description/action/dismiss; (§14.13) Glassmorphism effects — glass cards, chart grid dots, gradient accents, focus rings; (§14.14) Accessibility — 8 requirements (contrast, focus, keyboard, screen reader, reduced motion, color-blind safe, font scaling, high contrast); (§14.15) Performance budget — 10 metrics with targets (FCP <500ms, bundle <320KB with all libs). **Updated Part XII** with 15+ new priority items from Part XIV at P1-P3 levels.
- **NinjaTrader & TradingView Gap Analysis (v6):** Added **Part XIII – NinjaTrader & TradingView Gap Analysis** with 5 sub-sections: (§13.1) Component-by-component grading (Dashboard B-, Trading Chart F, Header B+, Sidebar B, Positions C+, Analytics B-, Logs B+); (§13.2) 4 critical gaps: (1) No candlestick chart — NT/TV dedicate 60-70% of screen to charts with OHLCV, signal markers, indicator overlays; (2) No keyboard shortcuts / command palette — NT has 50+ hotkeys, TV has universal search; (3) Tab-based layout instead of resizable multi-panel — NT uses dockable panels, TV uses drag-snap; (4) Position table missing sort/filter/expand — NT has full data grids with Greeks, strategy, time held; (§13.3) 8 high-impact gaps: (5) No toast notifications — NT/TV show fill confirmations, SL/TP hits in real-time; (6) No market ticker strip — TV header shows major indices ticking live; (7) No status bar — NT has engine uptime, data freshness, market hours at bottom; (8) No sidebar watchlist — TV has persistent symbol list with mini-prices; (9) Position columns missing time held, delta, strategy, risk %; (10) No options chain view — NT has full chain with strikes grid; (11) No signal outcome tracking — no way to verify signal accuracy; (12) No risk/exposure dashboard — no portfolio Greeks, margin usage, concentration; (§13.4) 17 "polish-to-pro" items including position row expand, compact mode, hover cards, stale data indicators, market hours countdown, session summary, trade replay, right-click menus, reduced motion, settings search, log regex; (§13.5) 6-phase implementation roadmap (A: Chart-First, B: Keyboard Power, C: Data Grid, D: Notifications, E: No-Install Polish, F: Advanced). **Updated Part XII priority table** with 20+ new items from gap analysis integrated at P0-P3 levels.
- **UI Modernization Implementation (v5):** Implemented core UI improvements without installing new npm packages — all using existing Tailwind + CVA + clsx + Lucide stack. **New UI primitives (4):** `skeleton.tsx` (shimmer animation, pre-built StatCard/Card/TableRow skeletons), `tabs.tsx` (pure React context-based tabs, no Radix dependency), `alert.tsx` (6 variants incl. signal/destructive, auto-icons), `tooltip.tsx` (pure CSS hover tooltip, 4 directions). **New trading components (3):** `PnLValue.tsx` (animated P&L display with green/red flash on value change, ±sign, percentage, size variants), `SignalActivity.tsx` (signal timeline panel showing detected signals + executed trades with direction icons, strength badges, timestamps, glow animation), `MarketOverview.tsx` (live tick data grid with bid/ask, priority symbol sorting, volume display). **CSS system:** Added 14 trading-specific CSS custom properties (profit/loss, bid/ask, signal-call/put, greeks-delta/gamma/theta/vega, chart-up/down/volume) in both light and dark themes; added `pnl-flash-green`/`pnl-flash-red` animations, `skeleton-shimmer` animation, `signal-glow` animation, `tws-disconnected-border`, P&L gauge utility classes, severity classes (critical/error/warn/info/debug/trade/signal/order), category icon classes. Added Tailwind `trading.*`, `signal.*`, `greeks.*` color tokens and `fade-up`/`slide-in-right` keyframe animations. **Component improvements (11 files):** `StatCard` — added skeleton loading, P&L flash, hover effects, info tooltip; `LiveStats` — memoized with individual store selectors, skeleton on Starting, flash on Running, engine status with TWS connection subtitle; `ActivityLog` — category-specific icons (Zap/ShoppingCart/Database/Settings2), level icons, error/warning count badges, empty state with CTA; `DashboardPage` — tabbed layout (Overview: account+controls+risk+data; Signals & Market: market overview+signals+data; Configuration: all config panels; Activity: full log); `Header` — P&L flash animation, realized/unrealized mini display, TWS disconnect top border, trend direction icon; `Sidebar` — error count badge on Logs nav item, session mini-stats (trades/wins/losses), license expiry warning styling, TWS reconnecting state; `AccountSummary` — skeleton loading, tiered layout (primary metrics prominent, P&L with color + trend icons, secondary compact), connected badge; `PositionRow` — P&L gauge bar, trend icon on hover, close button on hover only, bold symbol; `PositionsPage` — summary cards (active/totalPnL/calls/puts), skeleton loading, better empty state; `LogsPage` — level summary badges, inline search field, row numbers, category-specific icons + colors, left-border for errors; `AnalyticsPage` — tabbed charts (All Charts/P&L Analysis/Distribution), info alert when no trades, trade count display; `PerformanceMetrics` — 8 metrics (added best trade + expectancy), info tooltips. Updated `App.tsx` suspense fallback with branded loading spinner. Updated ROADMAP Part XII priorities (12 items marked Done) and Phase 1/2 tables.
- **UI Library Evaluation & Modernization Plan (v4):** Added **Part XI – UI Library Evaluation & Professional Trading System Modernization** with 9 sub-sections: (§11.1) Full audit of current UI stack — what's installed and what's missing (7 of 40+ shadcn components, no candlestick charts, no data grid, no command palette, no skeleton loading); (§11.2) Head-to-head comparison of **shadcn/ui vs MUI vs DaisyUI** with verdict: keep and extend shadcn/ui (already in use, zero runtime cost, full customization) — MUI too heavy (+300KB, CSS-in-JS re-render cost), DaisyUI too generic for trading; (§11.3) Definitive recommended library stack: keep Tailwind+shadcn+Zustand+Framer Motion, **add TradingView Lightweight Charts** (candlestick/OHLCV, ~45KB), **TanStack Table v8** (professional data grid, ~15KB), **Sonner** (toasts, ~5KB), **cmdk** (command palette, ~4KB), react-resizable-panels, Vaul; explicit NOT-recommended list with reasons (MUI, DaisyUI, Ant Design, AG Grid, D3, Chart.js, react-hot-toast); (§11.4) Complete shadcn/ui component installation plan across 3 phases (12 critical: dialog, dropdown, select, tabs, tooltip, table, skeleton, alert, collapsible, scroll-area, toast, command; 8 enhanced; 7 polish); (§11.5) TradingView Lightweight Charts integration plan with component structure, data flow for live updates, and feature list (candlestick, volume, SuperTrend overlay, signal markers, crosshair); (§11.6) TanStack Table plan for positions/trades/logs/orders with sorting, filtering, column resize/pin, row expand, pagination, virtual scrolling, custom cell renderers; (§11.7) Professional trading terminal design system: trading-specific CSS color tokens (bid/ask, signal CALL/PUT, Greeks colors), typography enhancement (Geist/Satoshi for brand, IBM Plex Mono for logs), 10 micro-interaction specifications (P&L flash, trade fill toast, SL hit alert, TWS disconnect border, signal glow, position near-TP/SL pulse), full command palette (cmdk) design with 20+ commands across 5 groups; (§11.8) Dashboard layout redesign from vertical config stack → chart-first 3-panel trading terminal with resizable areas (chart 50%, positions 25%, signals 25%), move config panels to Settings; (§11.9) 4-phase implementation plan with specific tasks and timeline estimates. Added **Part XII – Updated Priorities** consolidating all UI modernization items with existing performance and backend priorities. Updated Part VI cross-references.
- **Performance deep-dive & professional UI features (v3):** Added **Part VIII – Performance Deep-Dive** with code-level analysis of 6 major bottlenecks: (1) SuperTrend/BOTSingal using 5 iterrows loops (50–100× slower than vectorized numpy); (2) init_data_feed has 15+ seconds of hard time.sleep(); (3) get_strikes/get_contract_detail use blocking poll loops; (4) event_processor runs full SuperTrend on every tick instead of bar-close only, block=False bug; (5) Indicators.py functions use Yahoo Finance HTTP calls instead of TWS data; (6) PnL emitted 20×/s, no log batching, heavy data_status computation under lock. Added **Part IX – Professional Trading UI** with 30+ new feature proposals across 4 categories: Dashboard (Greeks, intraday P&L curve, signal timeline, market overview, position cards, risk gauges, strategy breakdown, heat map, order flow), Logs (trade lifecycle groups, structured categories, search/regex, export, persistence, audio alerts, terminal viewer, severity badges, trade-linked navigation), Analytics (drawdown chart, risk metrics, trade distribution, symbol breakdown, multi-day view, strategy comparison, execution quality, session summary), Positions (live P&L, TP/SL gauge, Greeks, time held, sizing info, quick adjust, alerts). Added **Part X – Engine & Backend Improvements** covering class-based BOT refactor, consolidated DB, new sidecar events (greeks_update, signal_history, order_lifecycle, bar_close, tick_stream, session_summary), and TWS data enhancements (option Greeks, reqPnLSingle, VIX, execution details, multi-day history, market depth). **Part VI priorities completely restructured** with P0 security fix, P1 performance items, and P1/P2 new features integrated.
- **Optimization techniques (deep analysis):** Added **§4.6 Optimization techniques** with code-level analysis: (1) Summary of already-implemented optimizations. (2) Frontend: store selectors for LiveStats, DataFeedStatus, AccountSummary, RiskManagement, charts; useMemo for PnLChart/EquityCurve; usePositions stale-closure fix (getState in callback); batch addLog for high log volume. (3) Backend: throttle _emit_pnl_update to 1s in engine; optional log batching in sidecar. (4) Rust: optional event batching. (5) Summary table with file locations and priorities. Part VI updated with P2 optimization backlog.
- **Start Trading timing, update intervals, UI lightness, roadmap:** Start Trading flow documented (config from store, sidecar spawn = main delay, 0.2s TWS pause). UI shows "Loading config & engine…" while starting, "Started in X.Xs" after start; Dashboard shows "Updates: PnL ~1s · Account summary ~5s · Data status ~10s". Cards made lighter (border/70, shadow-sm; CSS border variables lightened). §4.5 marked implemented; Performance issue marked partially fixed; Part VI P1 Performance marked Done.
- **Performance / tab switch:** Added Known Issue (Part II) for UI hang when switching tabs. Added **§4.5 Performance & optimizations** (lazy routes, throttle PnL re-renders, memo Header/Sidebar, virtualize Logs/ActivityLog, list keys, optional page memo). Implemented: throttle 1s, lazy routes, memo layout, virtualized lists. P1 Frontend priority marked Done.
- **IBKR verification & roadmap update:** Deep-checked full flow: reqPnL → pnl_cache → pnl_update (every loop) and reqAccountSummary (12 tags) → account_summary_cache → account_metrics (every 5s). Documented in Part I "IBKR data shown in the UI"; added trading:account_metrics and get_account_metrics to commands/events; §3.1 and §4.1 marked done; Part VI P0/P2 items marked done where applicable.
- **Complete roadmap (v2):** Added **Part I – What the app currently has** (backend commands, state, events; frontend pages, components, stores, hooks, UI stack; sidecar protocol and engine; config, license, build). Added **Part II – Known issues**. Expanded **Part III–IV** (backend/frontend features). Added **Part V – Modern & unique UI** (critique, typography, color options, layout, motion, identity). Priorities in **Part VI**.
- **Earlier:** PnL emit fix; initial roadmap with vision, §3.1 IBKR metrics, planned features, improvements.
