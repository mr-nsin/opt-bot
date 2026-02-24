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

# PART XII – Updated Priorities (Including UI Modernization)

| Priority | Area | Item | Section |
|----------|------|------|---------|
| ~~P0~~ | Backend | ~~Continuous PnL + IBKR account metrics~~ **Done** | §3.1 |
| **P0** | **Security** | **Fix SQL injection in data_access.py** | §10.1 |
| ~~P0~~ | Frontend | ~~Install shadcn/ui Phase 1 components (skeleton, tabs, alert, tooltip)~~ **Done** (no external deps, pure Tailwind) | §11.4 |
| **P0** | **Frontend** | **Install Lightweight Charts + TanStack Table + Sonner + cmdk** (requires npm install) | §11.3 |
| **P0** | **Frontend** | **Add TradingView candlestick chart to Dashboard** (biggest UX impact) | §11.5, §11.8 |
| **P1** | **Performance** | **Vectorize SuperTrend/BOTSingal** | §8.1 |
| **P1** | **Performance** | **Bar-close triggered signals** | §8.4 |
| **P1** | **Performance** | **Remove hard sleeps in init_data_feed** | §8.2 |
| **P1** | **Performance** | **Throttle PnL emit to 1s in engine** | §8.6 |
| **P1** | **Performance** | **Fix event_queue.get() block=True** | §8.4 |
| ~~P1~~ | Frontend | ~~Skeleton loading states for StatCard, LiveStats, AccountSummary, PositionsPage~~ **Done** | §11.9 Phase 1 |
| ~~P1~~ | Frontend | ~~P&L flash animations (Header, StatCard, PnLValue component)~~ **Done** | §11.9 Phase 1 |
| **P1** | **Frontend** | **Sonner toasts** (requires npm install) | §11.9 Phase 1 |
| **P1** | **Frontend** | **Upgrade position/trade tables with TanStack Table** (requires npm install) | §11.6 |
| **P1** | **Frontend** | **Command palette (cmdk)** (requires npm install) | §11.7 |
| ~~P1~~ | Frontend | ~~Signal history timeline panel (SignalActivity component)~~ **Done** | §9.1, §11.9 Phase 2 |
| **P1** | **Frontend** | **Intraday P&L Curve** | §9.1 |
| ~~P1~~ | Frontend | ~~Position P&L gauge bar (PositionRow)~~ **Done** | §9.4 |
| ~~P1~~ | Frontend | ~~Log search + severity badges (LogsPage, ActivityLog, Sidebar)~~ **Done** | §9.2 |
| **P1** | **Frontend** | **Drawdown chart + risk metrics** | §9.3 |
| **P1** | Backend | Options Greeks from TWS + greeks_update event | §10.3 |
| **P1** | Backend | reqPnLSingle for per-position P&L | §10.3 |
| **P1** | Backend | export_trades, health commands | §3.2 |
| ~~P1~~ | UI | ~~Trading color tokens (CSS variables) + thematic Tailwind colors~~ **Done** | §11.7, §5.2 |
| ~~P2~~ | Frontend | ~~Dashboard layout redesign (tabbed: Overview, Signals & Market, Config, Activity)~~ **Done** | §11.8 |
| ~~P2~~ | Frontend | ~~Market overview panel (live tick data grid)~~ **Done** | §9.1 |
| **P2** | **Frontend** | **Greeks per position display** | §9.4 |
| **P2** | **Frontend** | **Trade lifecycle log groups** | §9.2 |
| **P2** | **Frontend** | **Audio alerts + log persistence/export** | §9.2 |
| **P2** | **Frontend** | **Order flow panel** | §9.1 |
| **P2** | **Frontend** | **Quick adjust TP/SL from positions** | §9.4 |
| P2 | Performance | Event-based contract resolution, separate queues, batch logs | §8.3, §8.4, §8.6 |
| P2 | Backend | Config validation, class-based BOT, consolidated DB + loggers | §10.1 |
| ~~P2~~ | Frontend | ~~Store selectors (LiveStats, Header, Sidebar use individual selectors)~~ **Done** | §4.6 |
| ~~P2~~ | UI | ~~Micro-interactions (P&L flash, signal glow, TWS disconnect border, hover effects)~~ **Done** | §11.7 |
| **P2** | UI | Compact mode, resizable panels (react-resizable-panels) | §11.9 |
| **P3** | **Frontend** | **P&L heatmap, trade distribution, execution quality** | §9.1, §9.3 |
| **P3** | **Frontend** | **Strategy comparison, calendar trade history** | §9.3, §11.9 |
| P3 | Performance | msgpack IPC, numba SuperTrend | §8.6, §8.1 |
| P3 | Backend | Market depth, multi-day history | §10.3 |
| P3 | All | BOT.py TODO cleanup, tests, code signing | — |

---

# PART VII – Changelog (Roadmap)

- **UI Modernization Implementation (v5):** Implemented core UI improvements without installing new npm packages — all using existing Tailwind + CVA + clsx + Lucide stack. **New UI primitives (4):** `skeleton.tsx` (shimmer animation, pre-built StatCard/Card/TableRow skeletons), `tabs.tsx` (pure React context-based tabs, no Radix dependency), `alert.tsx` (6 variants incl. signal/destructive, auto-icons), `tooltip.tsx` (pure CSS hover tooltip, 4 directions). **New trading components (3):** `PnLValue.tsx` (animated P&L display with green/red flash on value change, ±sign, percentage, size variants), `SignalActivity.tsx` (signal timeline panel showing detected signals + executed trades with direction icons, strength badges, timestamps, glow animation), `MarketOverview.tsx` (live tick data grid with bid/ask, priority symbol sorting, volume display). **CSS system:** Added 14 trading-specific CSS custom properties (profit/loss, bid/ask, signal-call/put, greeks-delta/gamma/theta/vega, chart-up/down/volume) in both light and dark themes; added `pnl-flash-green`/`pnl-flash-red` animations, `skeleton-shimmer` animation, `signal-glow` animation, `tws-disconnected-border`, P&L gauge utility classes, severity classes (critical/error/warn/info/debug/trade/signal/order), category icon classes. Added Tailwind `trading.*`, `signal.*`, `greeks.*` color tokens and `fade-up`/`slide-in-right` keyframe animations. **Component improvements (11 files):** `StatCard` — added skeleton loading, P&L flash, hover effects, info tooltip; `LiveStats` — memoized with individual store selectors, skeleton on Starting, flash on Running, engine status with TWS connection subtitle; `ActivityLog` — category-specific icons (Zap/ShoppingCart/Database/Settings2), level icons, error/warning count badges, empty state with CTA; `DashboardPage` — tabbed layout (Overview: account+controls+risk+data; Signals & Market: market overview+signals+data; Configuration: all config panels; Activity: full log); `Header` — P&L flash animation, realized/unrealized mini display, TWS disconnect top border, trend direction icon; `Sidebar` — error count badge on Logs nav item, session mini-stats (trades/wins/losses), license expiry warning styling, TWS reconnecting state; `AccountSummary` — skeleton loading, tiered layout (primary metrics prominent, P&L with color + trend icons, secondary compact), connected badge; `PositionRow` — P&L gauge bar, trend icon on hover, close button on hover only, bold symbol; `PositionsPage` — summary cards (active/totalPnL/calls/puts), skeleton loading, better empty state; `LogsPage` — level summary badges, inline search field, row numbers, category-specific icons + colors, left-border for errors; `AnalyticsPage` — tabbed charts (All Charts/P&L Analysis/Distribution), info alert when no trades, trade count display; `PerformanceMetrics` — 8 metrics (added best trade + expectancy), info tooltips. Updated `App.tsx` suspense fallback with branded loading spinner. Updated ROADMAP Part XII priorities (12 items marked Done) and Phase 1/2 tables.
- **UI Library Evaluation & Modernization Plan (v4):** Added **Part XI – UI Library Evaluation & Professional Trading System Modernization** with 9 sub-sections: (§11.1) Full audit of current UI stack — what's installed and what's missing (7 of 40+ shadcn components, no candlestick charts, no data grid, no command palette, no skeleton loading); (§11.2) Head-to-head comparison of **shadcn/ui vs MUI vs DaisyUI** with verdict: keep and extend shadcn/ui (already in use, zero runtime cost, full customization) — MUI too heavy (+300KB, CSS-in-JS re-render cost), DaisyUI too generic for trading; (§11.3) Definitive recommended library stack: keep Tailwind+shadcn+Zustand+Framer Motion, **add TradingView Lightweight Charts** (candlestick/OHLCV, ~45KB), **TanStack Table v8** (professional data grid, ~15KB), **Sonner** (toasts, ~5KB), **cmdk** (command palette, ~4KB), react-resizable-panels, Vaul; explicit NOT-recommended list with reasons (MUI, DaisyUI, Ant Design, AG Grid, D3, Chart.js, react-hot-toast); (§11.4) Complete shadcn/ui component installation plan across 3 phases (12 critical: dialog, dropdown, select, tabs, tooltip, table, skeleton, alert, collapsible, scroll-area, toast, command; 8 enhanced; 7 polish); (§11.5) TradingView Lightweight Charts integration plan with component structure, data flow for live updates, and feature list (candlestick, volume, SuperTrend overlay, signal markers, crosshair); (§11.6) TanStack Table plan for positions/trades/logs/orders with sorting, filtering, column resize/pin, row expand, pagination, virtual scrolling, custom cell renderers; (§11.7) Professional trading terminal design system: trading-specific CSS color tokens (bid/ask, signal CALL/PUT, Greeks colors), typography enhancement (Geist/Satoshi for brand, IBM Plex Mono for logs), 10 micro-interaction specifications (P&L flash, trade fill toast, SL hit alert, TWS disconnect border, signal glow, position near-TP/SL pulse), full command palette (cmdk) design with 20+ commands across 5 groups; (§11.8) Dashboard layout redesign from vertical config stack → chart-first 3-panel trading terminal with resizable areas (chart 50%, positions 25%, signals 25%), move config panels to Settings; (§11.9) 4-phase implementation plan with specific tasks and timeline estimates. Added **Part XII – Updated Priorities** consolidating all UI modernization items with existing performance and backend priorities. Updated Part VI cross-references.
- **Performance deep-dive & professional UI features (v3):** Added **Part VIII – Performance Deep-Dive** with code-level analysis of 6 major bottlenecks: (1) SuperTrend/BOTSingal using 5 iterrows loops (50–100× slower than vectorized numpy); (2) init_data_feed has 15+ seconds of hard time.sleep(); (3) get_strikes/get_contract_detail use blocking poll loops; (4) event_processor runs full SuperTrend on every tick instead of bar-close only, block=False bug; (5) Indicators.py functions use Yahoo Finance HTTP calls instead of TWS data; (6) PnL emitted 20×/s, no log batching, heavy data_status computation under lock. Added **Part IX – Professional Trading UI** with 30+ new feature proposals across 4 categories: Dashboard (Greeks, intraday P&L curve, signal timeline, market overview, position cards, risk gauges, strategy breakdown, heat map, order flow), Logs (trade lifecycle groups, structured categories, search/regex, export, persistence, audio alerts, terminal viewer, severity badges, trade-linked navigation), Analytics (drawdown chart, risk metrics, trade distribution, symbol breakdown, multi-day view, strategy comparison, execution quality, session summary), Positions (live P&L, TP/SL gauge, Greeks, time held, sizing info, quick adjust, alerts). Added **Part X – Engine & Backend Improvements** covering class-based BOT refactor, consolidated DB, new sidecar events (greeks_update, signal_history, order_lifecycle, bar_close, tick_stream, session_summary), and TWS data enhancements (option Greeks, reqPnLSingle, VIX, execution details, multi-day history, market depth). **Part VI priorities completely restructured** with P0 security fix, P1 performance items, and P1/P2 new features integrated.
- **Optimization techniques (deep analysis):** Added **§4.6 Optimization techniques** with code-level analysis: (1) Summary of already-implemented optimizations. (2) Frontend: store selectors for LiveStats, DataFeedStatus, AccountSummary, RiskManagement, charts; useMemo for PnLChart/EquityCurve; usePositions stale-closure fix (getState in callback); batch addLog for high log volume. (3) Backend: throttle _emit_pnl_update to 1s in engine; optional log batching in sidecar. (4) Rust: optional event batching. (5) Summary table with file locations and priorities. Part VI updated with P2 optimization backlog.
- **Start Trading timing, update intervals, UI lightness, roadmap:** Start Trading flow documented (config from store, sidecar spawn = main delay, 0.2s TWS pause). UI shows "Loading config & engine…" while starting, "Started in X.Xs" after start; Dashboard shows "Updates: PnL ~1s · Account summary ~5s · Data status ~10s". Cards made lighter (border/70, shadow-sm; CSS border variables lightened). §4.5 marked implemented; Performance issue marked partially fixed; Part VI P1 Performance marked Done.
- **Performance / tab switch:** Added Known Issue (Part II) for UI hang when switching tabs. Added **§4.5 Performance & optimizations** (lazy routes, throttle PnL re-renders, memo Header/Sidebar, virtualize Logs/ActivityLog, list keys, optional page memo). Implemented: throttle 1s, lazy routes, memo layout, virtualized lists. P1 Frontend priority marked Done.
- **IBKR verification & roadmap update:** Deep-checked full flow: reqPnL → pnl_cache → pnl_update (every loop) and reqAccountSummary (12 tags) → account_summary_cache → account_metrics (every 5s). Documented in Part I "IBKR data shown in the UI"; added trading:account_metrics and get_account_metrics to commands/events; §3.1 and §4.1 marked done; Part VI P0/P2 items marked done where applicable.
- **Complete roadmap (v2):** Added **Part I – What the app currently has** (backend commands, state, events; frontend pages, components, stores, hooks, UI stack; sidecar protocol and engine; config, license, build). Added **Part II – Known issues**. Expanded **Part III–IV** (backend/frontend features). Added **Part V – Modern & unique UI** (critique, typography, color options, layout, motion, identity). Priorities in **Part VI**.
- **Earlier:** PnL emit fix; initial roadmap with vision, §3.1 IBKR metrics, planned features, improvements.
