# QuantDrift — Feature Gap Analysis & UI Improvement Plan

## 1. Critical Bug: Bot Positions/Trades Not Showing on UI

### Root Cause

The Python trading engine (`BOT.py` / `trading_engine.py`) **imports** the emitter functions (`emit_position`, `emit_trade_executed`, `emit_trade_closed`, `emit_signal`) but **never calls them**. The entire data pipeline exists:

```
BOT.py → emit_position() → stdout JSON → Rust sidecar manager → Tauri event → React store → UI
```

But the first link is broken — `BOT.py` never calls `emit_position()` or `emit_trade_executed()`.

### What Needs to Happen

In `BOT.py`, these emitter calls must be added at the correct points:

| When | Call | Data |
|------|------|------|
| After `placeOrder()` succeeds | `emit_trade_executed({symbol, strike, right, expiry, quantity, entry_price, side, timestamp})` | Order fill data |
| When position is monitored (TP/SL loop) | `emit_position({symbol, strike, right, qty, avg_price, current_price, pnl, pnl_percent, delta})` | Current position state |
| When `squareOffAll()` or TP/SL closes | `emit_trade_closed({symbol, pnl, exit_price, reason})` | Close data |
| When signal detected in `checkConditionsAndTrade()` | `emit_signal({symbol, signal_type, strike, price, reason})` | Signal info |

### Files to Modify

- `BOT.py` — Add emit calls in `takeTrade()`, `placeAndVerifyOrder()`, `monitor_positions_loop()`, `squareOffAll()`, `checkConditionsAndTrade()`
- `trading-engine/engine/trading_engine.py` — Bridge calls from BOT into the emitter

---

## 2. Trades vs Positions — What's the Difference?

| Concept | Meaning | Current UI |
|---------|---------|------------|
| **Trade** | A single order execution (entry or exit). Has: symbol, side (BUY/SELL), price, quantity, timestamp, fees | Only shown as count in LiveStats. No trade list anywhere. |
| **Position** | An open holding. Has: symbol, qty, avg_price, current_price, P&L, TP/SL levels | Positions page shows active + closed positions |
| **Closed Position** | A position that was fully exited. Has: entry/exit prices, P&L, duration | Shown in PositionHistory (bottom of Positions page) |

### What's Missing

1. **No Trade Blotter** — There is no page/component that shows individual order executions (entries AND exits). A trading bot absolutely needs this.
2. **No Order Status** — Pending/working orders are invisible. If an order is placed but not yet filled, the user can't see it.
3. **No Trade Journal** — Closed trades lack context (why was the trade taken, what signal triggered it, entry/exit reasons).

---

## 3. Frontend Features — Implemented vs Not Implemented

### Fully Implemented (UI + Backend)

| Feature | Page | Backend Support |
|---------|------|-----------------|
| Start/Stop/Emergency Stop | Dashboard > Controls | ✅ Tauri commands → Python engine |
| Live P&L display | Header + Dashboard | ✅ `pnl_update` events from engine |
| Account metrics (IBKR) | Dashboard > AccountSummary | ✅ `account_metrics` events |
| TWS connection status | Header + StatusBar | ✅ `connection_status` events |
| Log viewer with filtering | Logs page | ✅ `log_message` events + `get_logs` command |
| Config editing | Dashboard > Configuration tab | ✅ `get_config`/`save_config` commands |
| License validation | LicenseGate | ✅ Full license system |
| Market ticker strip | MarketTicker | ✅ Data from `data_status.stock_ticks_sample` |
| Data feed status | Dashboard > DataFeedStatus | ✅ `emit_data_status()` periodic |

### Partially Implemented (UI exists, backend incomplete)

| Feature | Page | Issue |
|---------|------|-------|
| **Active Positions** | Positions page | UI listens for `position_update` events but BOT.py never calls `emit_position()` |
| **Closed Positions** | Positions page | UI listens for `trade_closed` but BOT.py never calls `emit_trade_closed()` |
| **Signal Activity** | Dashboard > Signals tab | UI listens for `signal_detected` but BOT.py never calls `emit_signal()` |
| **Trade count/stats** | Analytics + LiveStats | UI listens for `trade_executed` but BOT.py never calls `emit_trade_executed()` |
| **Close Position from UI** | Positions page | `close_position` Tauri command exists, sends to sidecar, but BOT.py handler may not respond |
| **Close All from UI** | Positions page | Same issue — message sent but BOT.py handling unclear |
| **P&L Sparkline chart** | Dashboard > Overview | Accumulates data only while running. Resets on restart. No persistence. |
| **Analytics charts** | Analytics page | All charts depend on `todayTrades` store which is only populated by `trade_executed` events (never fired) |

### Not Implemented (UI exists with no backend)

| Feature | Where | What's Missing |
|---------|-------|----------------|
| **Runtime config update** | Dashboard > Configuration | UI updates local state but `update_config` protocol message isn't sent to running engine |
| **Stock list add/remove** | Dashboard > StockList | Can edit list but no hot-reload to running engine |
| **Settings persistence** | Settings page | Some settings (font_size, update_interval, show_charts) exist in UI but aren't used anywhere |
| **Export data** | Nowhere | No CSV/JSON export for trades, positions, or logs |
| **Order status tracking** | Nowhere | `order_update` event type exists in protocol but no UI component displays orders |

### Not Implemented (No UI, no backend)

| Feature | Priority | Description |
|---------|----------|-------------|
| **Trade Blotter** | 🔴 Critical | List of all individual order executions with timestamps, fill prices, fees |
| **Order Book** | 🔴 Critical | Pending/working orders with ability to cancel |
| **Trade Journal** | 🟡 High | Closed trades with entry reason, exit reason, signal type, duration, screenshots |
| **Historical Performance** | 🟡 High | Multi-day P&L tracking, equity curve across days |
| **Strategy Stats** | 🟡 High | Per-strategy win rate, avg P&L, best/worst times |
| **Risk Dashboard** | 🟡 High | Max drawdown, Sharpe ratio, risk/reward, exposure heat map |
| **Alerts/Notifications** | 🟠 Medium | Configurable alerts (price levels, P&L limits, connection loss) |
| **Position Sizing Calculator** | 🟠 Medium | Calculate optimal position size based on account, risk % |
| **Backtesting Results** | 🟠 Medium | View backtesting results alongside live performance |
| **Multi-Account** | 🟠 Medium | Trade across multiple IBKR accounts |
| **Data Export** | 🟠 Medium | Export trades/positions/logs to CSV/JSON |
| **Config Presets** | 🟢 Low | Save/load trading config profiles |
| **Audit Trail** | 🟢 Low | Immutable log of all trading actions |

---

## 4. UI Improvement Recommendations

### A. Missing Pages/Views to Add

#### 4.1 Trade Blotter (New Component)
Display every order execution in a sortable, filterable table:

| Column | Source |
|--------|--------|
| Time | Order fill timestamp |
| Symbol | Stock symbol |
| Side | BUY / SELL |
| Type | CALL / PUT |
| Strike | Option strike price |
| Expiry | Option expiration |
| Qty | Number of contracts |
| Fill Price | Execution price |
| Status | Filled / Cancelled / Pending |
| Signal | What triggered this trade |

This requires `emit_trade_executed()` to be called in BOT.py.

#### 4.2 Order Book (New Component)
Show pending/working orders:

| Column | Source |
|--------|--------|
| Order ID | TWS order ID |
| Symbol | Stock symbol |
| Side | BUY / SELL |
| Type | LMT / MKT |
| Price | Limit price |
| Qty | Quantity |
| Status | Pending / Working / Partial |
| Action | Cancel button |

This requires `emit_order_update()` to be called in BOT.py.

#### 4.3 Enhanced Position View
Current positions page is basic. Add:

- **Greeks display** (delta, gamma, theta, vega) — data exists in BOT.py
- **P&L chart per position** — mini sparkline showing P&L over time
- **TP/SL levels** — visual indicator of take profit and stop loss
- **Time in trade** — how long position has been held
- **Entry signal** — what triggered the trade

### B. Dashboard Improvements

#### 4.4 Quick Stats Bar
Add a prominent stats row showing:
- Today's P&L (large, color-coded)
- Win/Loss ratio (visual bar)
- Open positions count
- Pending orders count
- Time until market close

#### 4.5 Trade Timeline
A chronological timeline of today's events:
- Signal detected → Order placed → Order filled → Position monitored → TP/SL hit → Trade closed

### C. Analytics Improvements

#### 4.6 Deeper Analytics (when trade data flows)
- **Hourly performance** — Heat map of P&L by hour
- **Symbol performance** — P&L breakdown by symbol
- **Direction analysis** — Calls vs Puts performance
- **Duration analysis** — Avg time in trade for wins vs losses
- **Streak tracking** — Current win/loss streak

---

## 5. Data Available in BOT.py (Not Sent to UI)

These data points exist in BOT.py but are never emitted to the UI:

| Data | Where in BOT.py | How to Surface |
|------|-----------------|----------------|
| All open positions with Greeks | `getAllPositions()` | Call `emit_position()` periodically |
| Individual trade executions | `placeAndVerifyOrder()` result | Call `emit_trade_executed()` on fill |
| Trade close events | `monitor_positions_loop()` TP/SL | Call `emit_trade_closed()` on close |
| SuperTrend signals | `checkConditionsAndTrade()` | Call `emit_signal()` on signal detect |
| ATR/VWAP calculations | `getATRValue()`, `checkVWAPValue()` | Include in signal data |
| Options chain data | `fetch_all_strike_expiries()` | New event: `emit_options_chain()` |
| Order status updates | `orderStatus()` TWS callback | Call `emit_order_update()` on status change |
| Historical candle data | `event_processor()` bars | Could emit for chart overlay |
| Position TP/SL levels | `monitor_positions_loop()` | Include in `emit_position()` data |
| Daily trade cooldowns | `check_TRADE_COOLDOWN_SECONDS()` | Include in data status |

---

## 6. Implementation Priority

### Phase 1: Fix the Data Pipeline (Critical)
1. Add `emit_trade_executed()` calls in BOT.py `takeTrade()` / `placeAndVerifyOrder()`
2. Add `emit_position()` calls in `monitor_positions_loop()` and `synchronize_positions()`
3. Add `emit_trade_closed()` calls when TP/SL hits or `squareOffAll()`
4. Add `emit_signal()` calls in `checkConditionsAndTrade()`
5. Add `emit_order_update()` calls in TWS order callbacks

This alone will make Positions page, Analytics page, and Signal Activity work.

### Phase 2: Trade Blotter & Order Book
1. Create `TradeBlotter` component — table of all executions
2. Create `OrderBook` component — pending orders with cancel
3. Add to Dashboard or as new tab in Positions page
4. Store trades persistently (today at minimum)

### Phase 3: Enhanced Position View
1. Add Greeks to position row
2. Add TP/SL visual indicators
3. Add entry signal info
4. Add time-in-trade display

### Phase 4: Advanced Analytics
1. Per-symbol breakdown
2. Hourly heat map
3. Direction analysis (Calls vs Puts)
4. Multi-day history (requires DB persistence)

### Phase 5: Quality of Life
1. Data export (CSV)
2. Config presets
3. Alerts configuration
4. Position sizing calculator

---

## 7. Architecture Notes

### Current Data Flow
```
BOT.py (trading logic)
  → emit_*() functions (protocol/emitter.py)
    → stdout JSON (one line per event)
      → Rust sidecar manager (src-tauri/src/sidecar/manager.rs)
        → AppState update + Tauri event emit
          → React hooks (useTradingEvents, usePositions)
            → Zustand stores (tradingStore, positionStore)
              → UI components (reactive updates)
```

### The Gap
Step 1 (BOT.py → emit) is broken. The functions exist but are never called.
Steps 2-6 are fully implemented and tested (P&L and log events work end-to-end).

### Key Stores and Their Data Caps
- `tradingStore.todayTrades`: Max 100 entries (in-memory only, lost on restart)
- `positionStore.positions`: No cap (active positions)
- `positionStore.closedPositions`: Max 200 entries
- `logStore.logs`: Max 100 entries (frontend), 1000 entries (Rust backend)

### What Bot Tracks but UI Can't See
- All TWS order callbacks (orderStatus, openOrder, execDetails)
- Real-time options chain data
- Historical OHLCV candle data
- ATR, VWAP, SuperTrend indicator values
- Trade cooldown timers
- Account PnL from TWS (separate from calculated P&L)
