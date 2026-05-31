# Progress: QuantDrift Options Trading Bot

## What is Implemented
- [x] **React + TypeScript Frontend:** Dashboard, Analytics, Positions, System Logs, Settings tabs.
- [x] **Tauri Native Wrapper:** Compiled Rust app handling window, files, and licensing validation.
- [x] **JSON-RPC Communication Bridge:** Stdio JSON-RPC event routing between Rust and Python sidecar.
- [x] **Real-time Price & P&L Streaming:** Bid/Ask, Last/Current Price, and Position P&L calculated in the Python trading engine, piped through Rust, and merged in the React stores.
- [x] **Trade Blotter Live Cross-Reference:** Trade Blotter connects to the active position map via a normalized option key to dynamically show active contract ticks.
- [x] **Fixed-Percent stop loss and take profit:** Added UI switches for SL/TP mode to configure either dynamic ATR or fixed premium percentages. Built helper functions (`sl_tp_helpers.py`) with complete unit test coverage.
- [x] **Config persistence fixes:** Ensured Tauri config state updates write back to the correct path loaded at runtime (e.g. `./config.json`).

## What is Partially Done / In Progress
- [ ] Running regression tests on the full Tauri app workspace.
- [ ] Validating runtime UI state binding when switching between Demo and Live accounts.

## Known Issues & Debt
- **TWS Disconnection Recovery:** Real-time updates depend on active TWS API socket connections. TWS Gateway restarts daily; the bot must reliably re-initialize data subscriptions post-reconnect.
- **Pytest Dependencies:** Venv python lacks pytest packages locally. Test runner execution must fall back to direct import scripts or inline script execution.
