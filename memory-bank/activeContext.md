# Active Context: QuantDrift Options Trading Bot

## Current Focus of Work
* We are currently on the branch **`fix-pricing`**.
* The core goal of the active workspace session is verifying that:
  1. Real-time pricing fields (Current Price, Bid/Ask, P&L) populate correctly in Active Positions and Trade Blotter UI components.
  2. The newly implemented Fixed-Percent Stop-Loss and Take-Profit premium settings calculate, serialize, save, and apply correctly across both UI controls, Tauri config states, and the Python trading engine logic.

## Recent Decisions
* **Fixed % Option Premium Logic:** Integrated a new configuration key `sl_tp_mode` supporting `dynamic_atr` and `fixed_percent`. Under `fixed_percent` mode, the stop loss and take profit are calculated strictly as a percentage of the entry premium rather than using ATR references.
* **Config Path Persistence:** Enhanced Tauri `config_state` to mirror JSON writes back to the exact path from which it loaded the file (e.g. legacy `./config.json` vs app data directory), resolving discrepancies where settings saved on the UI did not take effect in the Python engine.
* **Committed Active Tasks:** The implementation files (`sl_tp_helpers.py`, UI component changes in `RiskManagement.tsx`, state changes in `config_state.rs`, logic additions in `BOT.py`, and unit tests `test_fixed_sl_tp_premium_math.py`) have been verified and committed on the `fix-pricing` branch.

## Next Steps
* Run the Tauri application in dev mode (`npm run tauri:dev` or `run-with-registry.bat`) to verify that the frontend launches, successfully reads configurations, and streams mock or live pricing ticks.
* Monitor logs for any IPC RPC message serialization warnings or Rust warnings in the sidecar manager.
