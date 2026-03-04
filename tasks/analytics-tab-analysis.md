# Deep Analysis: Analytics Tab Charts — What May Not Update

## Scope

This document analyzes the four Analytics components and their data flows to identify why charts might not update or display data.

---

## 1. Component → Data Mapping

| Component | Store Fields Used | Critical Filter / Logic |
|-----------|-------------------|-------------------------|
| **PerformanceMetrics** | totalTrades, openTrades, closedTrades, winningTrades, losingTrades, dailyPnl, todayTrades | Stats derived from todayTrades with `(t.pnl ?? 0) > 0` / `< 0`; Net P&L from dailyPnl.total |
| **WinLossChart** | winningTrades, losingTrades | Pie chart: Wins vs Losses counts |
| **PnLChart** | todayTrades | `todayTrades.filter(t => t.pnl !== undefined)` — only closed trades with PnL |
| **EquityCurve** | todayTrades | Same filter; cumulative equity built from closed trades |

---

## 2. Data Flow (Event Path)

```
order_manager.process_fill() [entry filled]
    → emit_trade_executed({id, symbol, right, strike, expiry, ...})
    → Rust: trade_executed → app.trading.trades_today.push(trade)
    → Tauri emit: trading:trade_executed
    → useTradingEvents: addTrade(), setTradeStats(), setOpenClosedTrades()

order_manager.process_fill() [exit filled]
    → emit_trade_closed({symbol, right, strike, expiry, pnl, exit_price, ...})
    → Rust: trade_closed → update matching trade in trades_today (pnl, status)
    → Tauri emit: trading:trade_closed
    → useTradingEvents: updateTradePnl(), setTradeStats(), setOpenClosedTrades()
```

---

## 3. Why Charts Stay Empty / Don't Update

### 3.1 No completed trades in PnLChart / EquityCurve

**Cause:** `t.pnl !== undefined` filters out all trades.

| Root Cause | Scenario | Fix Status |
|------------|----------|------------|
| **trade_closed never fires** | Exit fill not processed (TWS callback not wired, order_manager not called) | Architecture: callback is set in TradingEngine._init_tws_client |
| **updateTradePnl match fails** | symbol/right/strike/expiry mismatch between trade_executed and trade_closed | expiry added to match ✓; right normalized (C/CALL, P/PUT) ✓ |
| **Strike float mismatch** | e.g. 450.0 vs 450 | Match uses `Number(t.strike) === match.strike` — may fail for 449.9999999 |
| **Expiry format mismatch** | "20250117" vs "2025-01-17" | Frontend normExp removes dashes; Rust trade_closed normalizes ✓ |

### 3.2 WinLossChart shows 0/0

**Cause:** winningTrades and losingTrades both 0.

| Root Cause | Scenario | Fix Status |
|------------|----------|------------|
| **trade_closed not received** | Same as 3.1 | — |
| **pnl === 0** | trade_closed has pnl=0; neither winning nor losing incremented | By design: 0 is neutral |
| **Hydration overwrote with stale data** | refreshStatus returns old winning_trades/losing_trades | Rust now updates trades_today on trade_closed; get_trading_status returns correct counts ✓ |

### 3.3 PerformanceMetrics show zeros or stale values

**Cause:** totalTrades=0, or todayTrades empty, or dailyPnl stale.

| Root Cause | Scenario | Fix Status |
|------------|----------|------------|
| **trade_executed not received** | Entry fill not processed | Architecture: order_manager.process_trade is callback |
| **dailyPnl not updating** | pnl_update event not firing or TWS pnl_cache empty | Event-driven; throttle 1s |
| **Stats from todayTrades** | Same filters as PnLChart; if no closed trades, avgWin/avgLoss/profitFactor = 0 or N/A | Expected |

### 3.4 Hydration (page load / navigate to Analytics)

**Cause:** When user opens Analytics after a refresh or cold start, store is empty until refreshStatus runs.

| Root Cause | Scenario | Fix Status |
|------------|----------|------------|
| **get_trading_status didn't return trades_today** | Rust used to omit or return incomplete | Now returns trades_today ✓ |
| **trades_today had pnl=null for closed trades** | Rust never updated trades on trade_closed | Rust now updates matching trade with pnl, status ✓ |
| **refreshStatus not called on Analytics mount** | Page relied only on events | AnalyticsPage calls refreshStatus() in useEffect on mount ✓ |
| **setTodayTrades replaces entire array** | Correct for hydration — backend is source of truth | Working as intended |

---

## 4. Edge Cases

### 4.1 Untracked exit orders

When an exit order fills but the entry was **not** in orders_cache (e.g. square-off, manual close outside app):

- `order_manager.process_trade` emits `trade_closed` with pnl=0, symbol/right/strike/expiry from contract
- No matching open trade in todayTrades → updateTradePnl finds nothing
- Win/loss not incremented (pnl=0)
- Chart does not show this close (no trade to update)
- **Result:** Position disappears from Positions, but Analytics does not show the close

### 4.2 Equity curve order

- todayTrades is stored **newest-first** (addTrade prepends)
- EquityCurve maps in array order: `Trade 1` = first in filtered array = most recent close
- Cumulative runs from newest → oldest
- **UX:** X-axis "Trade 1" is most recent; users may expect chronological. Data is correct; order is reversed.

### 4.3 Multiple positions same symbol+strike+right, different expiry

- updateTradePnl matches on expiry (when provided)
- Rust trade_closed matches on expiry
- If trade_closed omits expiry for some code path, wrong trade could be updated

### 4.4 Strike float precision

- Frontend: `Number(t.strike) === match.strike`
- TWS/IB often uses floats (e.g. 450.0)
- If engine sends 449.99999999999, strict equality fails
- **Mitigation:** Consider `Math.abs(Number(t.strike) - match.strike) < 0.01` for tolerance

---

## 5. React / Recharts Reactivity

- All chart components use `useTradingStore((s) => s.todayTrades)` or similar selectors
- When todayTrades, winningTrades, or losingTrades change, Zustand triggers re-render
- `addTrade` and `updateTradePnl` produce new array references → Recharts receives new data
- **No useMemo** on chart data in PnLChart and EquityCurve — new array each render, but that’s fine for correctness
- PerformanceMetrics uses useMemo for stats; dependencies include todayTrades

---

## 6. Verification Checklist

To confirm charts update correctly:

1. **Live events:** Start trading → place entry → fill → place exit → fill. Verify:
   - trade_executed fires → PerformanceMetrics totalTrades increases, Trade Blotter shows open trade
   - trade_closed fires → PnLChart/EquityCurve show bar/point, WinLossChart updates, PerformanceMetrics stats update

2. **Hydration:** With engine running and closed trades, refresh the page or navigate away and back to Analytics. Verify:
   - refreshStatus runs (check network or logs)
   - All four components show the same data as before refresh

3. **Demo mode:** Run SIMULATE_DEMO; all components should populate within ~30 seconds.

---

## 7. Summary: Remaining Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Strike float mismatch in updateTradePnl | Low | Add tolerance (e.g. 0.01) if reports persist |
| Untracked exits not in Analytics | Low | Document; consider adding synthetic closed trade when position disappears without match |
| Equity curve X-axis order (newest first) | Low | Consider `.slice().reverse()` for chronological display if desired |
| TWS not sending fills to callback | Medium | Verify orderStatus/execDetails wiring in tws_api_client |
