# Deep Analysis: Live Updates and Metrics Across the App

## Executive Summary

This document traces data flows for positions, trades, P&L, and dashboard metrics. It identifies gaps where data may not update continuously or display correctly.

---

## Tabs Overview and Data Sources

| Tab / Page | Components | Data Source | Hydration / Update |
|------------|------------|-------------|-------------------|
| **Dashboard** | PnLSparkline, LiveStats, AccountSummary, DataFeedStatus, StockPricesGrid, MarketOverview, SignalActivity | tradingStore (dailyPnl, accountMetrics, dataStatus, todayTrades, signalsInSession) | Events; App init calls refreshStatus |
| **Analytics** | PerformanceMetrics, WinLossChart, PnLChart, EquityCurve | tradingStore (todayTrades, winningTrades, losingTrades, dailyPnl) | Events; refreshStatus on mount |
| **Positions** | Positions table, TradeBlotter, PositionHistory | positionStore + tradingStore | position_update events, refreshPositions poll (2s) |
| **Logs** | LogFilter, virtual list | logStore ← logsApi.get() | One-time fetch on mount; real-time via trading:log_message |
| **Settings** | Forms | configStore | config.get on load |

---

## 1. Position P&L (Positions Page)

### Data Flow
```
TWS positions → engine.get_positions() → position_update event (every 2s)
                ↓
         current_price from: (1) order_id_tick_lookup[entry_order.id]
                             (2) fallback: client.get_options_data(symbol, expiry, right, strike)
                ↓
         Rust app.trading.positions ← event
         React positionStore ← position_update event OR refreshPositions (poll every 2s)
                ↓
         PositionRow displays position.pnl, position.current_price
```

### Issues
| Issue | Cause | Severity |
|-------|-------|----------|
| P&L stays 0 | No tick in order_id_tick_lookup AND get_options_data returns None (option not subscribed, illiquid) | Medium |
| Stale prices | position_update every 2s — may feel laggy for fast markets | Low |
| updatePosition match | Uses symbol+strike+right; multiple positions same symbol different expiry could theoretically collide (rare) | Low |

### Current Fixes (already applied)
- Position emit interval: 5s → 2s
- Fallback to client tick_cache when order lookup fails
- Frontend poll: 5s → 2s

### Future Improvement
- **reqPnLSingle**: TWS provides per-position unrealized PnL; use instead of manual (current - avg) × qty × 100

---

## 2. Open Trade → Closed Trade Conversion (Trade Blotter, Analytics)

### Data Flow
```
Exit order FILLED → order_manager.process_fill() → _emit_trade_closed({symbol, right, strike, expiry, pnl, exit_price, ...})
                ↓
         useTradingEvents: trading:trade_closed
                ↓
         updateTradePnl(match, pnl, exitPrice) — finds open trade, sets status:"closed", pnl, exit_price
         usePositions: removePosition + addClosedPosition
```

### Matching Logic (updateTradePnl)
- Matches on: symbol, right (normalized C/CALL, P/PUT), strike, **expiry** (when provided)

### Issues
| Issue | Cause | Severity |
|-------|-------|----------|
| Wrong trade marked closed | Same symbol+strike+right, different expiry — matches first open trade | Medium |
| Trade stays "OPEN" | Right mismatch (e.g. "C" vs "CALL" — we have nr() so should be ok); or symbol/strike float tolerance | Low |
| Analytics empty | EquityCurve, PnLChart filter `t.pnl !== undefined` — if no trade_closed fires or match fails, no completed trades | High |

### Fix
- Add **expiry** to updateTradePnl match when provided in trade_closed

---

## 3. PnL Sparkline (Dashboard)

### Data Flow
```
TWS pnl() callback → pnl_cache {daily, unrealized, realized}
                ↓
         Engine _emit_pnl_update() every loop (~50ms when connected)
                ↓
         trading:pnl_update (throttled 1s in useTradingEvents)
                ↓
         tradingStore.dailyPnl
                ↓
         PnLSparkline: records point every 5s when isRunning, from dailyPnl.total
```

### Issues
| Issue | Cause | Severity |
|-------|-------|----------|
| Chart flat / no new points | Only adds when dailyPnl.total in deps triggers useEffect AND 5s elapsed; if total unchanged for long period, points still added (5s timer) | Low |
| "Collecting data…" forever | Needs ≥2 points; first point at 5s, second at 10s — 10s to see chart | Low |
| Stale if pnl_cache empty | reqPnL in init_order_requests; if TWS never sends pnl(), cache empty, _emit_pnl_update returns early | Medium |

---

## 4. Daily P&L (LiveStats, Header, Sidebar, RiskManagement)

### Data Flow
- Same as PnL Sparkline: pnl_update → dailyPnl
- Throttled to 1s in useTradingEvents

### Issues
- If pnl_cache empty (reqPnL not responded yet, or TWS disconnects), values stay at 0 or last

---

## 5. Account Metrics (AccountSummary, Header NetLiq)

### Data Flow
```
TWS accountSummary() → account_summary_cache
                ↓
         Engine _emit_account_metrics() — first time when cache has data, then every 5s
                ↓
         trading:account_metrics
                ↓
         tradingStore.accountMetrics
```

### Issues
- Emitted every 5s — may feel slow
- If cache never populated (reqAccountSummary not called or no response), stays null

---

## 6. Stock Prices / Market Overview (StockPricesGrid, MarketOverview, DataFeedStatus)

### Data Flow
```
TWS tick_cache (STK/FUT ticks)
                ↓
         _emit_data_status() every 10s
                ↓
         data_status event {stock_ticks_sample: [{symbol, last, bid, ask, ...}], ...}
                ↓
         tradingStore.dataStatus
                ↓
         StockPricesGrid, MarketOverview use dataStatus.stock_ticks_sample
```

### Issues
| Issue | Cause | Severity |
|-------|-------|----------|
| "Awaiting market data" | data_status every 10s; stock_ticks_sample from tick_cache. If only OPT subscribed (no STK), stk_snapshot empty | Medium |
| Placeholders with 0 | When symbols configured but no ticks yet | Expected |
| 10s update interval | Feels sluggish for "live" prices | Low |

---

## 7. Analytics Tab (EquityCurve, PnLChart, WinLossChart, PerformanceMetrics)

### Data Source
- todayTrades from tradingStore
- EquityCurve, PnLChart: filter `t.pnl !== undefined` (closed trades with PnL)
- WinLossChart: winningTrades, losingTrades (from trade_closed events)
- PerformanceMetrics: todayTrades, dailyPnl, etc.

### Issues (and fixes)
| Issue | Cause | Severity | Fix |
|-------|-------|----------|-----|
| "No completed trades yet" | updateTradePnl match fails (expiry missing, etc.) → trades stay open → no pnl | High | Added expiry to match ✓ |
| todayTrades empty on load | Store only populated by events; no sync from backend on mount | High | get_trading_status now returns trades_today; refreshStatus hydrates on App init + Analytics mount ✓ |
| **Hydration returns trades without pnl** | Rust trades_today was never updated when trade_closed arrived; get_trading_status returned trades with pnl=None | High | Rust trade_closed handler now updates matching open trade with pnl, exit_price, status="closed" ✓ |
| Stale win/loss counts | winningTrades/losingTrades only updated on trade_closed | Expected | — |

---

## 8. Trade Blotter (Positions Page)

### Data Source
- todayTrades — open and closed
- status "open" vs "closed" from updateTradePnl
- PnL shown when status closed and pnl defined

### Issues
- Same as Analytics: if updateTradePnl doesn't match, trade stays OPEN in blotter

---

## Summary of Fixes Applied

1. **updateTradePnl**: Added expiry to match when trade_closed includes it (disambiguate multiple positions)
2. **usePositions trade_closed**: Added expiry to position match and removePosition
3. **positionStore updatePosition**: Added expiry to matcher when multiple positions same symbol+strike+right
4. **PnL Sparkline**: Reduced record interval from 5s to 2s for smoother curve
5. **data_status**: Reduced interval 10s → 5s for StockPricesGrid / MarketOverview freshness
6. **Position P&L**: Document reqPnLSingle as future enhancement for accurate per-position PnL
7. **Analytics hydration**: get_trading_status now returns trades_today; refreshStatus hydrates tradingStore; called on App init and Analytics page mount
8. **Rust trade_closed**: When trade_closed event arrives, Rust now updates the matching open trade in trades_today with pnl, exit_price, status="closed" — so hydration returns complete data for Analytics charts

---

## Event/Update Intervals Reference

| Event / Poll | Interval | Consumers |
|--------------|----------|-----------|
| pnl_update | ~50ms (engine) → throttled 1s (frontend) | dailyPnl, PnL Sparkline, LiveStats, etc. |
| position_update | 2s | Positions page, positionStore |
| account_metrics | 5s | AccountSummary, Header |
| data_status | 5s | StockPricesGrid, MarketOverview, DataFeedStatus |
| Positions refreshPositions | 2s | positionStore (poll) |
