# Antigravity Rules & Intelligence: QuantDrift Options Trading Bot

This document acts as the project brain. It holds the living record of patterns that work, gotchas, naming conventions, and specific architecture rules for this repository. 

**I MUST apply these rules in all future work.**

## 1. State Management & IPC Chain (The Sacred Flow)
**Rule:** Never break the triple-tier event chain.
* **Flow:** Python Engine (`emit_position`) -> stdout -> Rust Tauri Sidecar Manager (`handle_sidecar_message`) -> Tauri AppHandle Event (`trading:position_update`) -> React Zustand Store (`positionStore.ts`).
* **Gotcha:** Do not bypass the Rust layer for state aggregation. Rust deduplicates redundant ticks and merges P&L state before forwarding to React, saving CPU cycles on the frontend.

## 2. Configuration Persistence
**Rule:** Always write configuration changes back to the exact physical path they were loaded from.
* **Reason:** The Python sidecar processes are spawned in the background. If Tauri writes UI changes to an AppData directory while the Python script reads from `./config.json`, the engine will execute trades using outdated logic. 
* **Implementation:** Always use `app_state.config_loaded_from` to direct the write operation.

## 3. Options Position Matching Key
**Rule:** When cross-referencing orders, positions, and trades, always use the 4-part normalized tuple: `(symbol, strike, right, expiry)`.
* **Normalization Requirements:** 
  1. `right`: Must be explicitly converted to `"C"` or `"P"` (not "CALL" or "PUT").
  2. `expiry`: Must have all hyphens and spaces removed (e.g., `"2026-04-18"` -> `"20260418"`).
  3. `strike`: Always handled as a float to prevent string parsing mismatches.

## 4. Sidecar Process Reliability
**Rule:** Always assume the Python sidecar can crash or disconnect from TWS independently.
* **TWS Connections:** Never let the TWS client reconnect automatically on its own daemon thread. Let the `trading_engine.py` orchestrate reconnects so the system state (`connected_to_tws`) remains globally consistent.
* **Process Cleanup:** On Windows, always map the child Python process to a **Windows Job Object** (`win32job`). This ensures that if the Tauri UI is killed from the Task Manager, the Python engine dies instantly instead of trading forever in the background as a zombie.

## 5. UI Preferences & Styling
* **Tech Stack:** React (TypeScript) + Vite + TailwindCSS.
* **Icons:** Lucide React.
* **Design Pattern:** Component-based UI with Zustand for global state. Complex components should subscribe to the smallest possible state slice to prevent unnecessary re-renders when live tick data streams in 40 times a second.
