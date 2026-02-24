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

# PART VI – Priorities Summary

| Priority | Area | Item |
|----------|------|------|
| ~~P0~~ | Backend | ~~Continuous PnL + full IBKR account metrics (§3.1)~~ **Done** |
| P1 | Backend | Remaining commands: export_trades, health (§3.2); get_account_metrics done |
| P1 | Frontend | Account/Summary view (§4.1) **Done** (Dashboard card); Alerts & notifications (§4.2) |
| ~~P1~~ | Frontend | ~~**Performance:** Fix UI hang on tab switch (§4.5)~~ **Done** (throttle PnL, lazy routes, memo layout, virtualize lists) |
| P1 | UI | Unique typography + thematic color (§5.2, §5.3) |
| P2 | Backend | Sidecar account_metrics event **Done**; config validation (§3.3, §3.4); throttle PnL emit in engine to 1s (§4.6) |
| P2 | Frontend | Export & reporting (§4.3); UX (shortcuts, confirmations, stale indicator) (§4.4); **Optimizations:** store selectors (LiveStats, DataFeedStatus, AccountSummary, RiskManagement), useMemo chart data (PnLChart, EquityCurve), usePositions getState fix, batch addLog (§4.6) |
| P2 | UI | Motion and feedback; compact mode (§5.3) |
| P3 | All | BOT.py TODO cleanup; tests; code signing; docs (§II, §4.6); optional log/event batching in sidecar and Rust (§4.6) |

---

# PART VII – Changelog (Roadmap)

- **Optimization techniques (deep analysis):** Added **§4.6 Optimization techniques** with code-level analysis: (1) Summary of already-implemented optimizations. (2) Frontend: store selectors for LiveStats, DataFeedStatus, AccountSummary, RiskManagement, charts; useMemo for PnLChart/EquityCurve; usePositions stale-closure fix (getState in callback); batch addLog for high log volume. (3) Backend: throttle _emit_pnl_update to 1s in engine; optional log batching in sidecar. (4) Rust: optional event batching. (5) Summary table with file locations and priorities. Part VI updated with P2 optimization backlog.
- **Start Trading timing, update intervals, UI lightness, roadmap:** Start Trading flow documented (config from store, sidecar spawn = main delay, 0.2s TWS pause). UI shows "Loading config & engine…" while starting, "Started in X.Xs" after start; Dashboard shows "Updates: PnL ~1s · Account summary ~5s · Data status ~10s". Cards made lighter (border/70, shadow-sm; CSS border variables lightened). §4.5 marked implemented; Performance issue marked partially fixed; Part VI P1 Performance marked Done.
- **Performance / tab switch:** Added Known Issue (Part II) for UI hang when switching tabs. Added **§4.5 Performance & optimizations** (lazy routes, throttle PnL re-renders, memo Header/Sidebar, virtualize Logs/ActivityLog, list keys, optional page memo). Implemented: throttle 1s, lazy routes, memo layout, virtualized lists. P1 Frontend priority marked Done.
- **IBKR verification & roadmap update:** Deep-checked full flow: reqPnL → pnl_cache → pnl_update (every loop) and reqAccountSummary (12 tags) → account_summary_cache → account_metrics (every 5s). Documented in Part I "IBKR data shown in the UI"; added trading:account_metrics and get_account_metrics to commands/events; §3.1 and §4.1 marked done; Part VI P0/P2 items marked done where applicable.
- **Complete roadmap (v2):** Added **Part I – What the app currently has** (backend commands, state, events; frontend pages, components, stores, hooks, UI stack; sidecar protocol and engine; config, license, build). Added **Part II – Known issues**. Expanded **Part III–IV** (backend/frontend features). Added **Part V – Modern & unique UI** (critique, typography, color options, layout, motion, identity). Priorities in **Part VI**.
- **Earlier:** PnL emit fix; initial roadmap with vision, §3.1 IBKR metrics, planned features, improvements.
