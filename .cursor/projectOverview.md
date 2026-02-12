# Project Overview — OPT_BOT

## What Is This Project?

OPT_BOT is an **automated options trading bot** targeting US equity markets (SPY, QQQ, TSLA, AAPL, AMD, NVDA, MSFT, AMZN, BABA). It connects to **Interactive Brokers (TWS)** via the official `ibapi` Python library, streams real-time market data, detects trading signals using technical indicators, places and manages options orders, and enforces daily risk limits.

The project also includes early-stage integrations for **Tradovate** (futures) and **Databento** (alternative market data), indicating planned expansion beyond IB options.

## Product Names / Branding

The product is marketed under two brand names (togglable in code):
- **LevelUP** — current active brand (logos in `logo/levelup*.png`)
- **QuantDrift** — alternate brand (logos in `logo/quantDrift*.png`)

Support contact: `quantdrift@gmail.com` / WhatsApp: `+91-9461651867`

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Broker API | Interactive Brokers `ibapi` |
| GUI | PyQt5 (primary), Tkinter (legacy `TK_GUI.py`) |
| Charts | Matplotlib (Qt5Agg backend) |
| Data | pandas, numpy, yfinance |
| Database | SQLite3 (two schemas — see `data_access.py` and `utils/database_manager.py`) |
| Logging | Python `logging` with `RotatingFileHandler` (three logger implementations) |
| Alternative data | Databento (`clients/databento_*.py`) |
| Alternative broker | Tradovate (`clients/tradovate_client.py`) |

## Key Directories

```
OPT_BOT/
├── BOT.py                  # Main trading engine (~2400 lines)
├── GUI.py                  # PyQt5 GUI (~2067 lines)
├── TK_GUI.py               # Legacy Tkinter GUI
├── common.py               # Shared data structures, logger setup
├── tws_api_client.py       # IB API wrapper (EWrapper + EClient)
├── order_manager.py        # Order lifecycle management
├── data_access.py          # SQLite DAL for option_orders
├── Indicators.py           # Technical indicators library
├── logger.py               # Loggers class (secondary logging)
├── loadFile.py             # Entry point with license check
├── new_change.py           # Legacy entry point
├── image_load.py           # Image loading utility
├── config.json             # Main trading config (IB connection, deltas, limits)
├── expiryStrike.json       # Pre-fetched strike prices per symbol
├── license.json            # License key storage
├── RUN_GUI.bat             # Windows launcher
├── strategies/
│   ├── engulfing_atr.py        # Engulfing + ATR strategy
│   └── enhanced_engulfing_atr.py # Enhanced version with volume + EMA
├── clients/
│   ├── databento_client.py     # Databento market data client
│   ├── databento_enhanced.py   # Enhanced Databento client
│   ├── databento_streamer.py   # Real-time Databento streamer
│   └── tradovate_client.py     # Tradovate futures API client
├── utils/
│   ├── database_manager.py     # Enhanced SQLite manager (trades, signals, sessions, candles)
│   ├── logger.py               # TradingLogger with categorized log files
│   └── ui_animations.py        # PyQt5 animation helpers
├── config/
│   └── settings.json           # UI/strategy/broker settings
├── db/
│   └── orders.db               # SQLite database (runtime)
├── logo/                       # Brand images
└── logs/                       # Rotating log files (runtime)
```

## Entry Points

1. **`RUN_GUI.bat`** → runs `GUI.py` (Windows users)
2. **`python GUI.py`** → launches PyQt5 GUI directly
3. **`loadFile.py`** → license validation → GUI launch
4. **`BOT.py`** → can be started directly via `start_trading()` / `main_call()`

## Current State

- The core IB options trading flow is **functional** — connects to TWS, subscribes to market data, detects SuperTrend/engulfing signals, places options trades with TP/SL, and monitors positions.
- The PyQt5 GUI provides trading controls, analytics, position management, and logging.
- The `strategies/`, `clients/`, and `utils/` directories represent a **newer architecture layer** (config-driven, class-based) that is partially integrated with the main `BOT.py` flow.
- License validation is implemented with SHA-256 hash-based key generation.

## Active Branch

`opt-bot` (tracking `origin/opt-bot`)
