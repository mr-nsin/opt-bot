# Configuration Reference — OPT_BOT

## 1. config.json — Main Trading Configuration

**Location:** `/config.json`
**Read by:** `BOT.py` at module level (import time)

```json
{
  "profit_increment": 0.03,          // Trailing profit step size ($)
  "expiryToTrade": "next",           // Stock expiry: "current" or "next" weekly
  "SPY_QQQ_EXPIRY": "0DTE",          // ETF/Index expiry: "0DTE" or "1DTE"
  "USE_DIFF_EXPIRY_INDEX": "yes",    // Use different expiry for SPY/QQQ
  
  // TWS Connection
  "IP": "127.0.0.1",
  "PORT": 7497,                      // 7497=paper, 7496=live
  "CLIENTID": 0,
  "ACCOUNT_ID": "U6987141",
  
  // Market Hours
  "marketStartTime": "19:00:00",     // UTC market start (for reference)
  "scriptStartTime": "0935",         // NY time to start trading (HHMM)
  "scriptEndTime": "1545",           // NY time to stop trading (HHMM)
  
  // Order Settings
  "ORDER_TRANSMIT": true,            // Actually send orders to IB
  "USE_TIMER_IN_ORDER": "ON",        // Enable GTD time-in-force
  "ORDER_EXPIRY_TIMER": 15,          // Seconds until order expires (GTD)
  "VWAP_ON_OFF": "ON",               // Enable VWAP confirmation
  
  // Delta Thresholds
  "CALL_DELTA_CHECK": 0.35,          // Min delta for call selection
  "PUT_DELTA_CHECK": -0.35,          // Min (abs) delta for put selection
  
  // Volume/ATR Thresholds
  "VOLUME_CHECK": 100,               // Min options volume for strike
  "ATR_CHECKS": 0.047,               // Min ATR ratio to qualify
  "ATR_CHECK": 0.047,                // Duplicate key (same value)
  "ACTIVE_VOLUME": 5,                // Min active volume threshold
  "ATR_VALUE": 0.99,                 // ATR value threshold
  "AVG_VOLUMNS_CANDLES": 30,         // Avg volume calculation period
  
  // Position Sizing
  "MAX_CONTRACT_AMOUNT": 350,        // Max $ per trade ($350)
  "SHARE_VOLUME": 1,                 // Share volume multiplier
  "BODY": 2.0,                       // Candle body size multiplier
  "MIDPOINT_OFFSET": 0.01,           // Midpoint offset for pricing
  "QUANTITY": 2,                     // Default quantity
  
  // Data Settings
  "fetchValue": "1 D",               // Historical data duration ("1 D" = 1 day)
  "candleTime": "5 mins",            // Candle timeframe
  
  // Trade Management
  "distance_between_trade": 610,     // Cooldown seconds between same symbol+right
  "perDayTrades": 3,                 // Max trades per day (per stock)
  "profit_amount_day": 200,          // Daily profit target ($)
  "loss_amount_day": 200,            // Daily loss limit ($)
  
  // Stock Configuration
  "stockListToTrade": {
    "SPY": "NASDAQ",
    "QQQ": "NASDAQ",
    "TSLA": "NASDAQ",
    "AMZN": "NASDAQ",
    "AAPL": "NASDAQ",
    "AMD": "NASDAQ",
    "NVDA": "NASDAQ",
    "MSFT": "NASDAQ",
    "BABA": "NASDAQ"
  },
  "stockData": {                     // Per-stock amount limits
    "SPY": {"amount": 350},
    "QQQ": {"amount": 350},
    // ... same for all stocks
  }
}
```

### Key Config Mappings in BOT.py

| Config Key | Global Variable | Default |
|---|---|---|
| `IP` | `IP` | `127.0.0.1` |
| `PORT` | `PORT` | `7497` |
| `CLIENTID` | `CLIENTID` | `0` |
| `ACCOUNT_ID` | `SUB_ACCOUNT_ID` | `U6987141` |
| `expiryToTrade` | `EXPIRY` → `tradeExpiry_val` | `next` |
| `SPY_QQQ_EXPIRY` | `spy_qqq_tradeExpiry` | `0DTE` |
| `candleTime` | `candleTime` | `5 mins` |
| `fetchValue` | `fetchValue` | `1 D` |
| `CALL_DELTA_CHECK` | `CALL_DELTA_CHECK` | `0.35` |
| `PUT_DELTA_CHECK` | `PUT_DELTA_CHECK` | `-0.35` |
| `MAX_CONTRACT_AMOUNT` | `MAX_CONTRACT_AMOUNT` | `350` |
| `profit_amount_day` | `profit_amount_day` | `200` |
| `loss_amount_day` | `loss_amount_day` | `200` |
| `distance_between_trade` | `TRADE_COOLDOWN_SECONDS` | `610` |
| `profit_increment` | `PROFIT_INCREMENT` | `0.03` |
| `ORDER_EXPIRY_TIMER` | `ORDER_EXPIRY_TIMER` | `15` |
| `USE_TIMER_IN_ORDER` | `USE_TIMER_IN_ORDER` | `ON` |
| `VWAP_ON_OFF` | `VWAP_ON_OFF` | `ON` |
| `VOLUME_CHECK` | `VOLUME_CHECK` | `100` |
| `ATR_CHECKS` | `ATR_CHECKS` | `0.047` |

---

## 2. config/settings.json — UI & Strategy Configuration

**Location:** `/config/settings.json`
**Read by:** `GUI.py`, `strategies/*.py`, `clients/*.py`

### Sections

#### trading
```json
{
  "mode": "demo",                    // "demo" or "live"
  "symbol": "MNQ",                   // Primary futures symbol
  "symbols": ["MNQU5", "NQU5"],      // Futures contracts list
  "contract_month": "202506",
  "max_positions": 2,
  "position_size": 1,
  "risk_per_trade": 2.0,             // 2% risk per trade
  "max_daily_trades": 10,
  "time_windows": ["06:50", ...],    // Specific trade entry times
  "trade_end_time": "16:55",
  "trading_hours": {"start": "06:00", "end": "17:00"},
  "daily_profit_limit": 500.0,
  "daily_loss_limit": -300.0
}
```

#### strategy
```json
{
  "name": "engulfing_atr",
  "atr_period": 14,
  "atr_lookback": 100,
  "ema_length": 9,
  "sl_multiplier": 1.9,              // SL = entry - (ATR * 1.9)
  "tp_multiplier": 1.0,              // TP = entry + (ATR * 1.0)
  "sl_move_profit": 0.8,             // Move SL when 80% of target reached
  "sl_move_to": 0.5,                 // Move SL to 50% of target
  "high_atr_threshold": 26,          // ATR > 26 → tighter TP/SL
  "volume_confirmation": {
    "buy_volume_mult": 0.65,
    "sell_volume_mult": 0.85
  },
  "trail_update": 12
}
```

#### databento
```json
{
  "api_key": "your_databento_api_key_here",
  "dataset": "GLBX.MDP3",
  "schema": "trades",
  "symbols": ["NQ.FUT", "MNQ.FUT"]
}
```

#### tradovate
```json
{
  "demo_base_url": "https://demo.tradovateapi.com/v1",
  "live_base_url": "https://live.tradovateapi.com/v1",
  "credentials": {
    "username": "",
    "password": "",
    "client_id": "",
    "client_secret": "",
    "app_id": "",
    "demo_account_id": "",
    "live_account_id": ""
  }
}
```

#### ui
```json
{
  "theme": "dark",                   // "dark" or "light"
  "update_interval": 1000,           // ms between UI updates
  "show_charts": true,
  "font_size": 9,
  "animation_duration": 300,         // ms for theme transitions
  "smooth_transitions": true
}
```

#### logging & database
```json
{
  "logging": {"level": "INFO", "max_file_size": "10MB", "backup_count": 5},
  "database": {"path": "database/trades.db", "backup_enabled": true, "candle_retention_days": 30},
  "broker": {"host": "127.0.0.1", "port": 7497, "client_id": 22}
}
```

---

## 3. expiryStrike.json — Pre-Fetched Strike Prices

**Location:** `/expiryStrike.json`
**Read by:** `BOT.py` in `main_call()`

Structure: `{symbol: {Strike: [list of float strike prices]}}`

Example:
```json
{
  "SPY": {"Strike": [616.0, 10.01, 10010.0]},
  "QQQ": {"Strike": [561.0]},
  "TSLA": {"Strike": [512.5, 515.0, 517.5, ...]},
  "AMZN": {"Strike": [75.0, 80.0, 85.0, ...]},
  "NVDA": {"Strike": [0.5, 1.0, 2.0, ...]},
  "BABA": {"Strike": [22.5, 25.0, 30.0, ...]}
}
```

**Note:** Some symbols (SPY, QQQ, AAPL, MSFT) have very few strikes stored, which may indicate incomplete data or that strikes are fetched dynamically via `client.get_strikes()` at runtime.

---

## 4. license.json — License Key Storage

**Location:** `/license.json`
**Read by:** `BOT.py` (is_license_valid), `GUI.py` (validate_license)

```json
{"key": "<sha256_hash_string>"}
```

The GUI also checks `config/license.txt` for a stored license key.

---

## 5. GUI Config Override Flow

When the user clicks "Start Trading" in the GUI:

1. GUI reads current widget values (`get_ui_config()`)
2. Reads `config.json`, updates values from widgets
3. Passes the merged config dict to `BOT.start_trading(config_dict)`
4. BOT.py uses the passed config to override its globals

This means **GUI settings take precedence** over `config.json` when trading is started from the GUI.
