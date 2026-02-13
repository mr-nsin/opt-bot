# Trading Engine Status (Tauri App Sidecar)

## What the sidecar does today

- **TWS connection** – Connects at engine start. If TWS is not running, the engine stays "Running" but shows "TWS Disconnected". **Periodic reconnection** (every 10s) runs while disconnected, so if you start TWS later, the app will connect and show "TWS Connected" without restarting the engine.
- **Connection state sync** – The main loop checks `isConnected()`; if the client reconnects internally (e.g. after a drop) or disconnects, the app state and UI are updated.
- **PnL** – When connected, the engine periodically emits PnL from the TWS client’s PnL cache to the frontend.
- **Events** – Trade/order events from TWS are put on the event queue and processed (currently logged); they can be extended to drive UI updates.

## Data feed and strategies (integrated)

- Once TWS is connected, the engine starts the **BOT data feed and strategy loop**: sets BOT globals from config, runs `init_order_requests`, `init_data_feed` (TWS historical + options subscriptions, builds `expiryStrike.json`), loads strike data, `synchronize_orders`, then starts **4 event-processor threads** that consume the tick queue and run **strategy logic** (`getCallPutEngulfCheck` + `checkConditionsAndTrade` for stocks; `order_mgr.check_and_close_position` for options). So **data is fetched via TWS**, **signals are computed**, and **entry/exit orders** are placed from the sidecar.
- **Orders:** Close position / Close all from the UI use `OrderManager.close_position_by_symbol` and `close_all_positions`. Entry orders (and strategy-driven exits) are placed by BOT's `placeOrder` / `placeAndVerifyOrder` via the same TWS client and order manager.


## TWS: start trading without TWS, then start TWS

- If you click **Start trading** with TWS **off**, the engine starts and shows "TWS Disconnected".
- When you **start TWS** later, the engine **retries connection every 10 seconds**. When the connection succeeds, it emits `connection_status(True)` and the UI shows "TWS Connected" without restarting the engine or the app.

## Files

| Area            | Location |
|-----------------|----------|
| Engine loop     | `trading-engine/engine/trading_engine.py` |
| TWS client      | Root `tws_api_client.py` |
| Order manager   | Root `order_manager.py` (close_position_by_symbol, close_all_positions) |
| Data / strategy | Root `BOT.py`, `Indicators.py`, `strategies/*.py` – invoked by sidecar after TWS connect |
