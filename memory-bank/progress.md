# Progress: QuantDrift Options Trading Bot

## What is Implemented
- [x] **React + TypeScript Frontend:** Dashboard, Analytics, Positions, System Logs, Settings tabs.
- [x] **Tauri Native Wrapper:** Compiled Rust app handling window, files, and licensing validation.
- [x] **JSON-RPC Communication Bridge:** Stdio JSON-RPC event routing between Rust and Python sidecar.
- [x] **Real-time Price & P&L Streaming:** Bid/Ask, Last/Current Price, and Position P&L calculated in the Python trading engine, piped through Rust, and merged in the React stores.
- [x] **Trade Blotter Live Cross-Reference:** Trade Blotter connects to the active position map via a normalized option key to dynamically show active contract ticks.
- [x] **Fixed-Percent stop loss and take profit:** Added UI switches for SL/TP mode to configure either dynamic ATR or fixed premium percentages. Built helper functions (`sl_tp_helpers.py`) with complete unit test coverage.
- [x] **Config persistence fixes:** Ensured Tauri config state updates write back to the correct path loaded at runtime (e.g. `./config.json`).
- [x] **High-Scale Performance Throttling:** Engine scaled to handle 20 symbols and hundreds of trades by introducing a strict 2.0-second throttle on heavy Pandas DataFrame strategies (SuperTrend/Engulfing), 0.25-second micro-throttles on OPT ticks, and completely silencing raw stdout debug logs to prevent Tauri IPC bridge lockups.
- [x] **TWS API Stream Limits:** Added a 90-contract subscription limit for option ticks in `tws_api_client.py` to prevent IBKR API cutoffs, using periodic snapshots as a fallback.
- [x] **Virtualized UI Rendering:** Added TanStack Virtualizer to the `TradeBlotter` table to handle heavy lists smoothly.
- [x] **Ponytail Cleanup:** Removed obsolete PyQt/Tkinter files and unused Databento/Tradovate connectors to declutter the codebase.

## What is Partially Done / In Progress
- [ ] Running regression tests on the full Tauri app workspace.
- [ ] Validating runtime UI state binding when switching between Demo and Live accounts.

## Known Issues & Debt
- **TWS Disconnection Recovery:** Real-time updates depend on active TWS API socket connections. TWS Gateway restarts daily; the bot must reliably re-initialize data subscriptions post-reconnect.
- **Pytest Dependencies:** Venv python lacks pytest packages locally. Test runner execution must fall back to direct import scripts or inline script execution.

