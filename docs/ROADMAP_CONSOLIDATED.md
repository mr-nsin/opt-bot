# QuantDrift — Consolidated Product & Engineering Roadmap

**Purpose:** Single navigable roadmap across the whole app. Deep specs remain in linked docs; this file prioritizes themes, gaps, and phases.

**Last updated:** March 2026

---

## 1. Executive summary

QuantDrift is a **Tauri + React + Python** desktop options-trading app for IBKR (TWS). Strengths: live P&L/account metrics, sidecar architecture, licensing, dashboard/analytics/positions flows. **Highest-impact improvement areas:** (1) **engine performance & startup** (SuperTrend, sleeps, IPC), (2) **distribution trust** (code signing, notarization), (3) **parity & correctness** (BOT globals, open P1 bugs), (4) **professional UX** (alerts, export, order visibility, charts), (5) **security & data hygiene**.

---

## 2. Architecture snapshot

| Layer | Stack | Key paths |
|-------|--------|-----------|
| Shell | Tauri 2 / Rust | `src-tauri/` — commands, sidecar manager, license |
| UI | React 19, Vite, Tailwind, Zustand | `src/` |
| Engine | Python sidecar, BOT.py, PyInstaller | `trading-engine/`, root `BOT.py`, `tws_api_client.py`, `order_manager.py` |
| Config | `config.json`, app data merge | See `docs/CONFIG_HANDLING.md` |

**Canonical “what exists today” inventory:** `docs/ROADMAP.md` **Part I** (large but authoritative).

---

## 3. Improvement themes

### 3.1 Platform, build & distribution

| Item | Issue / goal | Notes |
|------|----------------|-------|
| **macOS Gatekeeper** | “Damaged / can’t be opened” on other Macs | Ad-hoc signing + quarantine; **proper fix:** Developer ID + notarization |
| **Execute bits** | `opt-bot` / `trading-engine` 644 after zip/cloud transfer | Recipients: `chmod +x`; ship DMG without zipping when possible — `INSTALL_MAC.md` |
| **Universal binary** | Intel + Apple Silicon | `build-mac-universal.sh`, `npm run build:mac:universal` |
| **Windows** | NSIS/MSI, PyInstaller exe | `BUILD_WINDOWS.md`, CI workflow |
| **CI/CD** | Repeatable signed builds | GitHub Actions + Apple secrets for notarization |

### 3.2 Security & compliance

| Item | Severity | Reference |
|------|----------|-----------|
| **SQL / data access** | Treat DB access as parameterized; audit `data_access.py` | `ROADMAP.md` Part VI (P0 security) |
| **License & registry** | HMAC, hardware binding, key rotation | `docs/LICENSE_SYSTEM.md`, `LICENSE_SETUP_STEPS.md` |
| **Secrets in logs** | Avoid logging full API keys / account ids | Ongoing hygiene |

### 3.3 Trading engine — correctness & parity

| Item | Status | Reference |
|------|--------|-----------|
| **BOT vs sidecar globals** | `main_call()` sets many globals; engine must mirror all used in trade path | `docs/TAURI_VS_BOT_COMPARISON.md` — audit `to_bot_config_dict()` / `trading_engine.py` after changes |
| **`timeCheckAndCloseProgram` in loop** | Open (P1) | `docs/ISSUES_ROADMAP.md` |
| **Expiry format in `check_exit_conditions`** | Open (P1) | `docs/ISSUES_ROADMAP.md` |
| **Emitters in BOT** | Ensure `emit_signal`, `emit_trade_*`, `emit_position` where UI expects them | `docs/FEATURE_GAP_ANALYSIS.md` (verify current code) |
| **Runtime config / hot reload** | `UPDATE_CONFIG`, stock list changes while running | FEATURE_GAP_ANALYSIS — partial |

### 3.4 Performance & scalability (engine)

These are the largest CPU/latency wins documented in depth:

| Priority | Item | Expected impact | Status |
|----------|------|-----------------|--------|
| **P1** | **Vectorize SuperTrend / BOTSingal** — NumPy row loops (no `iterrows`); shared core for `alphaTrend` | Large CPU reduction on STK tick path | **Done** (`Indicators.py` `_supertrend_numpy_on_df`) |
| **P1** | **Signal only on bar close** (not every tick) where safe | Cuts redundant work | Open (behavior change — plan separately) |
| **P1** | **Replace hard `sleep()` in `init_data_feed`** — poll until underlyings / option snapshots ready (timeouts 3s / 10s) | Often faster startup when TWS is quick | **Done** (`BOT.py` helpers) |
| **P1** | **Throttle `_emit_pnl_update` in Python** (~1s) to match UI | Less IPC | **Done** (`trading_engine.py` `_pnl_throttle_sec = 1.0`) |
| **P1** | **`event_queue.get(block=True, timeout=…)`** | Less busy-spin in processors | **Done** (`BOT.py` `event_processor`) |
| **P2** | **Event-based contract/strike resolution** — per-reqId Events, not shared flags | `tws_api_client.py` | Open |
| **P2** | **Reduce yfinance dependency** for indicators — prefer TWS data | `ROADMAP.md` §8.5 | Open |
| **P3** | msgpack IPC, numba SuperTrend, optional queue split OPT/STK | `ROADMAP.md` §8.6 | Open |

### 3.5 IBKR data & backend features

| Item | Priority | Reference |
|------|----------|-----------|
| **reqPnLSingle / per-position P&L** | P1 | `ROADMAP.md` Part X §10.3 |
| **Greeks (generic ticks)** | P1 | Same |
| **Multi-day history for analytics** | P2 | `reqHistoricalData` beyond 1D |
| **`export_trades` / health command** | P1–P2 | `ROADMAP.md` Part III |
| **Order lifecycle events** | P2 | Protocol + UI “working orders” |

### 3.6 Frontend & UX

| Item | Priority | Reference |
|------|----------|-----------|
| **Toasts / alerts** (TWS up/down, limits, fills) | P1 | `ROADMAP.md` Part IV §4.2 |
| **Export CSV** (trades, P&L summary) | P2 | §4.3 |
| **Keyboard shortcuts, confirmations** | P2 | §4.4 |
| **Stale data indicator** (no P&L/data_status) | P2 | §4.4 |
| **Store selectors / useMemo charts / batch logs** | P2 | §4.6 backlog |
| **Trade blotter / order book** | High product value | `FEATURE_GAP_ANALYSIS.md` |
| **Intraday P&L curve, drawdown, professional panels** | P1–P2 | `ROADMAP.md` Part IX |
| **TanStack Table, Lightweight Charts, command palette** | P2–P3 | `ROADMAP.md` Part XI |

### 3.7 UI design system

| Item | Reference |
|------|-----------|
| Distinct typography + color direction (not generic “AI blue”) | `ROADMAP.md` Part V |
| Futuristic revamp phases | `docs/UI_REVAMP_MIGRATION.md` |
| Crypto-link style notes | `docs/UI_CRYPTO_LINK_MATCH_PLAN.md` |

### 3.8 Observability & ops

| Item | Notes |
|------|-------|
| **Logs** | In-memory only today; optional disk persistence (`ROADMAP.md` §3.4) |
| **Log analysis playbooks** | `docs/LOG_ANALYSIS_SIGNALS.md`, `LOG_ERRORS_CLIENTID_ACCOUNT.md` |
| **Position / exit flow** | `docs/POSITION_MONITORING_FLOW.md`, `CHECK_EXIT_CONDITIONS_ANALYSIS.md` |

### 3.9 Testing & quality

| Item | Notes |
|------|-------|
| Automated tests for engine protocol, order keys, reconnect | Thin today — expand |
| E2E: start/stop, emergency stop, license gate | Manual + future Playwright/driver |
| **Emergency stop → UI sync** | Plan in `tasks/todo.md` — verify checklist |

---

## 4. Phased plan

### Phase A — **Stability & trust** (weeks)

1. Fix or verify **P1 engine bugs** (`ISSUES_ROADMAP`: timeCheckAndCloseProgram, expiry in exits).
2. **macOS:** Developer ID sign + notarize release DMG; document recipient workarounds until then.
3. Security pass: **data_access / SQL**, log redaction.
4. Confirm **BOT global parity** for any new config keys (`TAURI_VS_BOT_COMPARISON`).

### Phase B — **Performance** (sprints)

1. ~~Vectorize **SuperTrend / BOTSingal** (`ROADMAP.md` §8.1).~~ **Done** — NumPy core + `init_data_feed` polling waits + PnL 1s throttle + blocking queue get.
2. **Event-based contract resolution** in `tws_api_client` (`§8.3`) — still open.
3. Optional: **log batching** in sidecar; **bar-close-only** signal gating — evaluate risk/benefit.

### Phase C — **Product depth**

1. **Alerts/toasts** + export trades.
2. **Working orders** + trade blotter (protocol + UI).
3. **Charts:** intraday P&L, drawdown; consider Lightweight Charts for OHLCV later.
4. **Config validation** in Rust before save.

### Phase D — **Polish & scale**

1. UI design direction (Part V / UI_REVAMP_MIGRATION).
2. TanStack Table for large grids; command palette.
3. Multi-day analytics, execution quality, optional market depth.

---

## 5. Priority matrix (quick scan)

| P0 | P1 | P2 | P3 |
|----|----|----|-----|
| Security audit (SQL/data) | Engine perf (SuperTrend, sleeps, PnL throttle) | Export, validation, table/chart libs | Market depth, msgpack, extras |
| Signed + notarized macOS releases | IBKR: PnL single, Greeks, health/export | UX: shortcuts, stale indicator, batch logs | Nice-to-have analytics |
| | Alerts/toasts | Runtime config / order lifecycle | BOT.py TODO cleanup, tests |

---

## 6. Documentation map

| Document | Use for |
|----------|---------|
| **ROADMAP.md** | Full inventory, UI spec depth, performance §8–14, changelog |
| **ROADMAP_CONSOLIDATED.md** (this file) | Priorities & cross-cutting plan |
| **ISSUES_ROADMAP.md** | Sidecar parity checklist, P0–P3 issue list |
| **FEATURE_GAP_ANALYSIS.md** | UI vs backend gaps, blotter/journal ideas |
| **TRADING_ENGINE_STATUS.md** | What the sidecar does today |
| **TAURI_VS_BOT_COMPARISON.md** | Global/config parity debugging |
| **SIGNAL_FLOW_BOT_VS_ENGINE.md** | Signal pipeline & queue behavior |
| **IBKR_METRICS.md** | PnL / account API usage |
| **LICENSE_*.md** | Licensing |
| **CONFIG_HANDLING.md** | Config load/save |
| **UI_REVAMP_MIGRATION.md** | Visual refresh phases |
| **plans/** | Focused analyses (e.g. PnL/TP) |

---

## 7. Changelog of this roadmap file

| Date | Change |
|------|--------|
| 2026-03 | Initial consolidated roadmap from full codebase + `docs/` review |

---

*For exhaustive UI component specs and NinjaTrader-style gap lists, continue to use **docs/ROADMAP.md**; treat this document as the executive engineering backlog and phase guide.*
