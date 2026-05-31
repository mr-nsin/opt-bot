# Active Context: QuantDrift Options Trading Bot

## Current Focus of Work
* We are currently on the branch **`fix-pricing`**.
* The user initiated a deep-dive knowledge extraction loop to exhaustively map out the project architecture and store it in the Memory Bank.
* **The Loop is Complete:** We successfully traversed the Python Engine, the Rust Backend, and the React Frontend.

## Recent Decisions
* **Frontend Analysis:** Documented how Zustand (`tradingStore.ts`) manages live ticks. Confirmed the rigid normalization required for option matching `(symbol, strike, right, expiry)`.
* **Project Brain Created:** Generated `antigravity-rules.md` in the `memory-bank/` directory. This encapsulates the architectural strictness (IPC chains, config pathing, options matching, and process lifecycle).
* **Memory Bank Overhaul Loop Status:** DONE. All core files and the intelligence rules file are up to date and comprehensive.

## Next Steps
* Run `git add` and `git commit` to permanently save the `antigravity-rules.md` and context changes to the active branch.
* Await user confirmation to run the app or proceed to the next feature implementation.
