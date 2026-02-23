# IBKR / TWS API – PnL & Account Metrics

This document lists which **Interactive Brokers TWS API** calls and callbacks are used (or planned) for **PnL and account metrics** in QuantDrift. See **docs/ROADMAP.md** §3.1 for the full feature plan.

---

## Current Implementation

| API | Purpose | Where |
|-----|---------|--------|
| **reqPnL** (reqId, account, modelCode) | Request account-level PnL. TWS responds with **pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)**. Subscription is kept open for continuous updates. | `tws_api_client.py`: called in `managedAccounts()`; callback `pnl()` updates `pnl_cache` with keys `daily`, `unrealized`, `realized`. |
| **pnl_cache** | In-memory cache read by the trading engine and emitted to the UI every engine loop (~50ms) when connected. | `tws_api_client.pnl_cache`; `trading_engine._emit_pnl_update()` → `emit_pnl()` → `pnl_update` event → Rust → `trading:pnl_update` → Header, LiveStats, RiskManagement, Analytics. |
| **reqAccountSummary** (reqId, groupName, tags) | Request account summary with 12 tags (see below). TWS responds with **accountSummary(reqId, account, tag, value, currency)** and **accountSummaryEnd(reqId)**. | `tws_api_client.py`: called in `managedAccounts()` with reqId=2, groupName="All"; callbacks update `account_summary_cache[tag] = value`. |
| **account_summary_cache** | In-memory cache read by the engine every 5s and emitted as `account_metrics`. | `trading_engine._emit_account_metrics()` → `emit_account_metrics(metrics)` → Rust stores snapshot and emits `trading:account_metrics`; frontend **Account Summary (IBKR)** card shows all tags; `get_account_metrics` returns last snapshot. |

**PnL flow:** TWS connects → `managedAccounts` → `reqPnL(1, managed_account, "")` → TWS pushes `pnl(1, daily, unrealized, realized)` → cache updated → engine emits every loop → frontend.

**Account summary flow:** Same `managedAccounts` → `reqAccountSummary(2, "All", tags)` → `accountSummary` callbacks populate cache → engine emits every 5s → frontend.

---

## Account summary tags (implemented)

All 12 tags below are requested and shown in the Dashboard **Account Summary (IBKR)** card:

- **NetLiquidation** – Net liquidation value  
- **TotalCashValue** – Total cash  
- **GrossPositionValue** – Value of positions  
- **BuyingPower** – Buying power  
- **AvailableFunds** – Available funds  
- **ExcessLiquidity** – Excess liquidity  
- **MaintMarginReq** – Maintenance margin requirement  
- **InitialMarginReq** – Initial margin requirement  
- **RealizedPnL** – Realized P&L  
- **UnrealizedPnL** – Unrealized P&L  
- **SettledCash** – Settled cash  
- **EquityWithLoanValue** – Equity with loan value  

(Exact tag names and availability depend on IBKR API version and account type.)

---

## Optional / future

| API | Purpose | Notes |
|-----|---------|--------|
| **reqAccountUpdatesMulti** (reqId, account, modelCode, ledgerAndNLV) | Streaming account updates. | If needed for real-time margin/NLV beyond summary. |
| **reqPnLSingle** (reqId, account, modelCode, conId) | Per-position unrealized PnL. | For Positions table and per-leg risk display. |

---

## References

- **Roadmap:** docs/ROADMAP.md §3.1 (Continuous IBKR PnL & Account Metrics — Done)
- **TWS client:** `tws_api_client.py` (pnl_cache, account_summary_cache, reqPnL, reqAccountSummary, pnl, accountSummary)
- **Engine:** `trading-engine/engine/trading_engine.py` (_emit_pnl_update, _emit_account_metrics)
- **Frontend:** `trading:pnl_update` / `trading:account_metrics`, `dailyPnl` / `accountMetrics` stores, Header, LiveStats, AccountSummary card, `get_account_metrics` command
