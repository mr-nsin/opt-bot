# Developer Guide — OPT_BOT

## Quick Start

### Prerequisites

- Python 3.12+
- Interactive Brokers TWS or IB Gateway (running on port 7497 for paper, 7496 for live)
- pip packages (not in a requirements.txt — install manually):

```bash
pip install ibapi PyQt5 pandas numpy yfinance matplotlib pytz qtawesome pandas_ta
```

### Running the Application

**Option 1: GUI (recommended)**
```bash
cd /path/to/OPT_BOT
python GUI.py
```

**Option 2: Windows launcher**
```
Double-click RUN_GUI.bat
```

**Option 3: Direct BOT (headless)**
```python
import BOT
BOT.start_trading(config_dict)  # Pass config dict
```

### First Run Checklist

1. Ensure TWS/IB Gateway is running and accepting API connections
2. Configure `config.json` with correct IP, PORT, CLIENTID
3. Update `expiryStrike.json` with current strike prices for your symbols
4. Enter license key in GUI when prompted
5. Verify connection status shows "CONNECTED" in header
6. Set risk parameters (profit limit, loss limit, max contract amount)
7. Start in DEMO mode first

---

## Project File Map

### Files You'll Edit Most Often

| File | When |
|---|---|
| `config.json` | Changing trading parameters, adding/removing symbols |
| `BOT.py` | Modifying signal logic, trade execution, P&L management |
| `order_manager.py` | Changing TP/SL logic, trailing profit behavior |
| `GUI.py` | UI changes, adding controls, modifying tabs |
| `Indicators.py` | Adding new indicators or modifying SuperTrend params |
| `config/settings.json` | Strategy parameters, UI settings, broker config |
| `strategies/enhanced_engulfing_atr.py` | Strategy improvements |

### Files You Rarely Need to Touch

| File | Why |
|---|---|
| `tws_api_client.py` | Stable IB API wrapper — rarely needs changes |
| `data_access.py` | DAL is stable — only change for schema updates |
| `common.py` | Data structures — only change when adding new fields |
| `utils/ui_animations.py` | Animation utilities — stable |
| `utils/logger.py` | Logging — stable |

---

## Key Code Patterns

### Adding a New Stock

1. Add to `config.json` → `stockListToTrade`:
   ```json
   "META": "NASDAQ"
   ```
2. Add to `config.json` → `stockData`:
   ```json
   "META": {"amount": 350}
   ```
3. Add strike data to `expiryStrike.json`:
   ```json
   "META": {"Strike": [480.0, 485.0, 490.0, ...]}
   ```

### Adding a New Indicator

1. Add function to `Indicators.py`:
   ```python
   def MyIndicator(df, period=14):
       # Calculate and return indicator values
       return result_df
   ```
2. Call from `BOT.py` in `getCallPutEngulfCheck()` or `checkAlgoAndTrade()`

### Modifying TP/SL Logic

Edit `order_manager.py`:
- `check_take_profit()` — trailing profit logic
- `check_stop_loss()` — stop loss trigger
- `PROFIT_INCREMENT` in `config.json` controls trailing step size

### Adding a New GUI Tab

In `GUI.py` → `init_ui()`:
```python
self.new_tab = self.create_new_tab()
self.tab_widget.addTab(self.new_tab, "New Tab")
```

---

## Data Flow Diagram

```
User clicks "Start Trading"
       │
       ▼
GUI.get_ui_config() ──→ Read widget values
       │
       ▼
BOT.start_trading(config) ──→ Set globals from config
       │
       ▼
BOT.main_call()
       │
       ├── DAL() ──→ db/orders.db (restore state)
       ├── OrderManager(db) ──→ Manages orders
       ├── init_api_client() ──→ TwsApiClient connects to TWS
       │       │
       │       ├── reqPositions() ──→ Sync existing positions
       │       ├── reqAllOpenOrders() ──→ Sync open orders
       │       └── reqPnL() ──→ Subscribe to P&L updates
       │
       ├── Subscribe stock contracts (STK)
       │       │
       │       └── Subscribe historical bars (5 min candles)
       │
       ├── Subscribe option contracts (OPT) for nearest strikes
       │
       ├── Start event_processor() ──→ Processes tick events
       │       │
       │       ├── Stock tick ──→ getCallPutEngulfCheck()
       │       │       │
       │       │       ├── SuperTrend signal detected
       │       │       │       │
       │       │       │       └── checkConditionsAndTrade()
       │       │       │               │
       │       │       │               └── takeTrade() ──→ placeOrder()
       │       │       │
       │       │       └── No signal ──→ continue
       │       │
       │       └── Option tick ──→ check_and_close_position()
       │               │
       │               ├── check_take_profit() ──→ trailing close
       │               └── check_stop_loss() ──→ stop loss close
       │
       ├── Start pnl_watchdog_thread()
       │       │
       │       └── Check daily P&L vs limits every 60s
       │
       └── Start monitor_positions_loop()
               │
               └── Iterate active orders, check TP/SL every 2s
```

---

## Debugging Tips

### View Real-Time Logs
Logs are written to `logs/bot_YYYY-MM-DD.log` with rotating backup.

### Check Order Status
Look for log lines with these patterns:
- `"ENTRY Order"` — new order placed
- `"EXIT Order"` — position closed
- `"HIT TakeProfit"` — trailing profit triggered close
- `"HIT Stoploss"` — stop loss triggered close
- `"Cooldown active"` — trade blocked by cooldown
- `"DAY LOCK active"` — all trading blocked (P&L limit)

### Debug Signal Detection
Look for:
- `"stock = X, signal is ="` — SuperTrend raw signal
- `"Signal Match for stock"` — signal flip detected
- `"Bullish Engulf Condition"` / `"Bearish Engulf Condition"` — pattern match
- `"TAKE PROFIT CHECK"` — TP monitoring with prices
- `"STOPLOSS CHECK"` — SL monitoring with prices

### Debug Order Issues
The `log_order_status()` method in `OrderManager` prints a comprehensive block:
```
═══════════════════════════════════════════
ORDER STATUS: TSLA20250815C250.0
═══════════════════════════════════════════
Order ID: 123
Status: filled
Entry Price: $1.50
...
```

### Common Issues

| Symptom | Likely Cause |
|---|---|
| "TWS not connected" | TWS/Gateway not running, wrong port, or API not enabled |
| "Contract details timeout" | Symbol not found, market closed, or IB rate limit |
| "Cooldown active" | Trade attempted within 610s of last close for same symbol+right |
| "DAY LOCK active" | Daily P&L limit exceeded — restart required |
| "Order already present" | Duplicate order for same symbol — check `entry_orders_cache` |
| No signals generated | Check `candleTime`, insufficient candle data, or market closed |
| Charts not updating | Check if `timer` QTimer is running (100ms interval) |

---

## Port Numbers

| Port | Purpose |
|---|---|
| 7497 | TWS Paper Trading |
| 7496 | TWS Live Trading |
| 4002 | IB Gateway Paper Trading |
| 4001 | IB Gateway Live Trading |

---

## Environment Notes

- The bot operates in **New York timezone** (`America/New_York`) for all market time checks
- Default trading window: **9:35 AM - 3:45 PM ET**
- All prices are in **USD**
- Options multiplier is **100** (standard US equity options)
- The bot places **limit orders** for entry and **market orders** for exit
