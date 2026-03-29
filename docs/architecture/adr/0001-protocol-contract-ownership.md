# ADR 0001: Sidecar protocol contract ownership

## Status

Accepted

## Context

The app communicates between **Rust** and **Python** via **JSON lines** on stdio. Event and method names are stringly-typed; drift between Python emitters and Rust listeners causes silent UI bugs (events never forwarded) or duplicate handling.

## Decision

1. **Canonical spellings** for RPC **methods** and **event** names live in:
   - `trading-engine/protocol/messages.py`
   - `src-tauri/src/sidecar/protocol.rs` (`methods::`, `event_types::`)

2. **Python emitters** must use `messages.*` constants in `protocol/emitter.py` (not ad-hoc literals) so grep and review stay aligned.

3. **Rust** may match on string literals in `manager.rs` today; when touching that code, prefer `protocol::event_types::*` for the same names.

4. **Documentation** for humans: `docs/ARCHITECTURE.md` §4; update it when adding methods or events.

## Consequences

- Any new method or event requires **two file edits** minimum (Python + Rust constants) plus `handler` / `main` registration and optional `manager.rs` match arm.
- Frontend listens to `trading:{event}`; event name is the Python `event` field without prefix.

## Compliance

- [x] `emitter.py` imports `messages` for event type strings
- [x] `event_types` in Rust includes `account_metrics`, `data_status`, `signal_data`
