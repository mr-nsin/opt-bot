# Positions vs trades — data flow & sync

## When a trade opens (entry fill)

1. **`order_manager.process_fill`** (entry order, `status == filled`):
   - Emits **`trade_executed`** → React `useTradingEvents` adds a row to **todayTrades** and **positionStore** (if not duplicate).
   - Emits **`position_update`** immediately with avg price, qty, TP/SL when available → Rust `AppState.trading.positions` updates without waiting for TWS portfolio lag.

2. **Engine loop** (`_emit_positions` ~every 1s): Re-reads IBKR positions + ticks, emits **`position_update`** per row → refreshes P&L, bid/ask, TP/SL.

3. **`get_positions` Tauri command**: Asks sidecar for live list; Rust replaces cached positions only when the response is **non-empty** (avoids wiping UI on empty TWS delay).

## When a trade closes

- **`trade_closed`** from `order_manager` → React removes open row / moves to closed; Rust removes matching position (now keyed by **symbol + strike + normalized right + normalized expiry**).

## Normalization (must stay aligned)

- **Expiry**: strip `-`, spaces → compare `20260313` == `2026-03-13`.
- **Right**: `CALL`/`C` and `PUT`/`P` treated as same.

Shared TS helpers: `normRight`, `normExpiry`, `positionRowKey` in `src/stores/positionStore.ts`.

## `refreshPositions` merge

Pulling from the API could return a **non-empty** list that still **omits** a brand-new fill (TWS lag). The UI merges: **API rows first**, then **local open rows** whose `positionRowKey` is missing from the API — so the row added by `trade_executed` is not wiped.

## Known gaps / improvements

- **Partial fills**: Only **`filled`** triggers `trade_executed` / `position_update`; partials update DB but do not emit until fully filled.
- **Batch `position_update`**: Engine still emits one JSON line per position each tick; could batch for lower IPC (larger protocol change).
