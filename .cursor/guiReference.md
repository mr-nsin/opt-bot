# GUI Reference — OPT_BOT

## Overview

The primary GUI is built with **PyQt5** (`GUI.py`, ~2067 lines). A legacy Tkinter GUI exists in `TK_GUI.py` but is not actively used.

## Main Classes

### MainApp (QWidget)

The main application window. Contains all UI state and trading controls.

**Window Title:** `"LevelUP-PROFESSIONAL OPIONS TRADING SOFTWARE"`
**Default Size:** 1200x800

### TradingThread (QThread)

Background thread that runs the trading engine.

**Signals:**
- `log_signal(str)` — log messages to GUI
- `stats_signal(dict)` — stats updates (P&L, trades, win rate)
- `error_signal(str)` — error messages
- `price_signal(str, float)` — real-time price updates

**Note:** Currently, `start_trading()` bypasses `TradingThread` and calls `BOT.start_trading(config)` directly.

## Tab Structure

### Tab 1: Trading

**Layout:** 4-column horizontal layout

| Panel | Contents |
|---|---|
| **Trade Parameters** (left) | Expiry selectors (stock/ETF), max contract amount, gap between trades, call/put delta, start/end time, candle timeframe |
| **Stock Parameters** (center-left) | Stock list text editor, TWS IP/Port/ClientID |
| **Risk Management** (center-right) | Daily profit target, daily loss limit, risk per trade % |
| **Trading Controls** (center-right) | Start Trading, Stop Trading, Emergency Stop buttons |
| **Real-time Statistics** (center-right) | Daily P&L, trade count, win rate |
| **Trading Activity** (right) | Scrolling log text area |

### Tab 2: Analytics

**Layout:** Metrics grid + 3-section chart area

- **Performance Metrics** grid: Total trades, win rate, avg win, avg loss, net P&L
- **ALL TRADES** stats panel: Gross P&L, # of trades, # of contracts, avg/longest trade time, % profitable
- **Performance** pie chart: Win vs Loss ratio (animated, updates every 100ms)
- **Trade Chart** bar chart: Individual trade P&L distribution (animated)

Charts use `matplotlib` with `Qt5Agg` backend and theme-aware colors.

### Tab 3: Positions

- **Active Positions** table (8 columns): Trade ID, Side, Entry Price, Current P&L, Stop Loss, Take Profit, Entry Time, Actions (Close button)
- **Controls:** Close All Positions, Refresh buttons
- Auto-refreshes every 5 seconds via `position_timer`

### Tab 4: Logs

- **Log Filters:** Type filter (text input), Refresh button
- **System Logs:** Scrolling text area (Consolas 8pt font)
- Reads from `utils/logger.py`'s `trading_logger.get_recent_logs()`

## Header Section

| Element | Description |
|---|---|
| **Logo** | Brand image (LevelUP or QuantDrift), fixed 1700x300px |
| **Welcome label** | "Welcome User!" |
| **Clock** | Live time (updates every 1s), with optional `qtawesome` icon |
| **Date** | Current date |
| **Connection status** | "CONNECTED" (green) or "DISCONNECTED" (red) |
| **DEMO/LIVE toggle** | Switches trading mode with confirmation dialog |
| **Theme toggle** | Dark/Light theme switch with smooth transition |

## Theming

### Dark Theme (default)
- Background: `#17191B`
- Text: `#ffffff`
- Start button: `#1e5f1e` (green)
- Stop button: `#5f1e1e` (red)
- Emergency button: `#8b0000` (dark red)
- Tab selected: `#0078d4` (blue) bottom border

### Light Theme
- Background: `#ffffff`
- Text: `#17191B`
- Start button: `#d4edda` (light green)
- Stop button: `#f8d7da` (light red)
- Emergency button: `#dc3545` (red)

### Theme Transition
Uses `ThemeTransitionManager` from `utils/ui_animations.py` for smooth transitions. Falls back to direct stylesheet application on error.

Chart backgrounds, text colors, grid colors, and spine colors all update on theme change via `update_chart_theme()`.

## License Validation Flow

1. **Startup:** `check_license_on_startup()` checks `config/license.txt`
   - If valid → hide license section, enable controls
   - If invalid/missing → show license input section

2. **Manual validation:** User enters key → `validate_license()`
   - Generates expected key: `SHA-256(json.dumps({ip, email, key, start_date, days}))`
   - Compares against input
   - On match: saves to `license.json`, hides license section, enables controls
   - On mismatch: shows error dialog with support contact

3. **Hardcoded validation params** (in GUI.py):
   ```
   IP_Validate = "192.168.0.100"
   email_validate = "longnguyen347@yahoo.com"
   key_to_validate = "quant-drift-$987$-&x1$(-*0#!("
   starting_date = "2025-08-17"
   days_to_validate = 10
   ```

## GUI → BOT Communication

### Start Trading
```python
def start_trading(self):
    self.get_ui_config()          # Read all widget values
    # Updates self.data (config dict) from widgets
    BOT.start_trading(self.data)  # Pass config to BOT
    self.log_message("Trading Started")
```

### Stop Trading
```python
def stop_trading(self):
    BOT.stop_trading()            # Signal BOT to stop
    self.log_message("Trading Stopped")
```

### Config Widget Mapping

| Widget | Config Key | Default |
|---|---|---|
| `trade_expiry` (ComboBox) | `expiryToTrade` | "Current" |
| `index_trade_expiry` (ComboBox) | `SPY_QQQ_EXPIRY` | "0 DTE" |
| `max_contract_amount` (SpinBox) | `MAX_CONTRACT_AMOUNT` | 350 |
| `gap_between_trades` (SpinBox) | `distance_between_trade` | 300 |
| `call_delta` (DoubleSpinBox) | `CALL_DELTA_CHECK` | 0.35 |
| `put_delta` (DoubleSpinBox) | `PUT_DELTA_CHECK` | 0.35 |
| `start_time` (TimeEdit) | `scriptStartTime` | 09:35 |
| `end_time` (TimeEdit) | `scriptEndTime` | 15:45 |
| `candle_time` (ComboBox) | `candleTime` | "5 mins" |
| `stock_list` (TextEdit) | `stockListToTrade` | AAPL, MSFT, TSLA, AMZN, GOOGL |
| `tws_ip` (LineEdit) | `IP` | "127.0.0.1" |
| `tws_port` (LineEdit) | `PORT` | "7497" |
| `tws_clientid` (LineEdit) | `CLIENTID` | "25" |
| `profit_input` (SpinBox) | `profit_amount_day` | 500 |
| `loss_input` (SpinBox) | `loss_amount_day` | -300 |
| `risk_input` (DoubleSpinBox) | risk_per_trade | 2.0% |

## Timers

| Timer | Interval | Purpose |
|---|---|---|
| `time_timer` | 1000ms | Updates clock display |
| `position_timer` | 5000ms | Refreshes positions table |
| `timer` (charts) | 100ms | Animates analytics charts |

## UI Animation Utilities (utils/ui_animations.py)

| Class | Purpose |
|---|---|
| `ThemeTransitionManager` | Smooth theme switching (applies stylesheet + emits signal) |
| `ButtonPressAnimation` | Scale effect on button press |
| `StatusIndicatorAnimation` | Pulsing opacity for status indicators |
| `LoadingSpinner` | Rotating spinner animation |
| `SlideTransition` | Slide-in/slide-out widget transitions |
| `ColorTransition` | Smooth color interpolation |
| `SafeAnimationManager` | Manages and cleans up active animations |

## Dependencies

- `PyQt5` — Core GUI framework
- `matplotlib` — Charts (Qt5Agg backend)
- `qtawesome` (optional) — Material Design icons for buttons
