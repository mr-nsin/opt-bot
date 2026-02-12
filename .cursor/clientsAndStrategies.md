# Clients & Strategies Reference — OPT_BOT

## Strategies

### 1. strategies/engulfing_atr.py — Basic Engulfing + ATR Strategy

**Class:** `EngulfingATRStrategy`
**Config source:** `config/settings.json` → `strategy` section

This is a class-based, config-driven strategy designed for the newer architecture layer.

#### Parameters (from config)

| Parameter | Default | Description |
|---|---|---|
| `atr_period` | 14 | ATR calculation period |
| `ema_length` | 9 | EMA period for trend confirmation |
| `sl_multiplier` | 1.9 | Stop loss = entry ± (ATR × 1.9) |
| `tp_multiplier` | 1.0 | Take profit = entry ± (ATR × 1.0) |
| `sl_move_profit` | 0.8 | Move SL when 80% of target reached |
| `sl_move_to` | 0.5 | Move SL to 50% of target distance |
| `high_atr_threshold` | 26 | ATR > 26 triggers tighter TP/SL |
| `buy_volume_mult` | 0.65 | Min volume ratio for bullish confirmation |
| `sell_volume_mult` | 0.85 | Min volume ratio for bearish confirmation |

#### Key Methods

| Method | Purpose |
|---|---|
| `is_trading_hours()` | Check if within configured trading hours |
| `calculate_atr(df, period)` | Calculate ATR from DataFrame |
| `calculate_ema(df, period)` | Calculate EMA from DataFrame |
| `detect_engulfing_pattern(df)` | Detect engulfing candlestick pattern (7-candle analysis) |
| `_check_bullish_engulfing(...)` | 3-candle bullish engulfing with volume |
| `_check_bearish_engulfing(...)` | Bearish engulfing with high-low-volume checks |
| `_calculate_bullish_strength(...)` | Score 0-1 based on EMA, volume, body size, momentum |
| `_calculate_bearish_strength(...)` | Score 0-1 (same factors, opposite direction) |
| `should_move_stop_loss(...)` | Check if SL should move to breakeven (at 80% of target) |
| `get_position_size(balance, risk, entry, sl)` | Risk-based position sizing |
| `generate_signal(df)` | Main entry point — returns signal dict with action, SL, TP |

#### Signal Strength Scoring

Base strength 0.5, then:
- +0.2 if price is on correct side of EMA
- +0.15 if volume ratio > 1.5x (or +0.1 if > 1.2x)
- +0.1 if candle body > 1.2x previous body
- +0.05 if 3-candle momentum alignment
- Minimum 0.6 required to generate signal

---

### 2. strategies/enhanced_engulfing_atr.py — Enhanced Strategy

**Class:** `EngulfingATRStrategy` (same name, different implementation)
**Additional dependency:** `pandas_ta`, `utils/database_manager.py`

Enhanced version with:
- **EMA filter**: Previous candle close must be on correct side of 9-period EMA
- **Database integration**: Saves trades/signals via `DatabaseManager`
- **Position management**: Tracks positions array, max 2 concurrent
- **Dynamic ATR adjustment**: High ATR (>26) → tighter TP (0.9×) and SL (1.8×)
- **UUID-based trade IDs**

#### Additional Methods

| Method | Purpose |
|---|---|
| `detect_engulfing_signal(df)` | Returns "BUY"/"SELL"/None with 7-candle unpacking |
| `check_ema_filter(df, signal)` | EMA trend confirmation using `pandas_ta` |
| `calculate_position_size(balance, risk%, entry, sl)` | Min 1, max 5 contracts |
| `calculate_stop_loss_take_profit(entry, signal)` | ATR-based SL/TP with fallback (20/15 ticks) |
| `should_move_stop_loss(position, current_price)` | Returns new SL if profit threshold met |
| `analyze_market_data(df)` | Full analysis pipeline → dict with signal, SL, TP, ATR |
| `create_trade_order(analysis, symbol, balance)` | Creates trade order dict with UUID |
| `get_strategy_status()` | Returns current strategy state |

---

## Clients

### 1. clients/databento_client.py — Databento Market Data Client

**Purpose:** Alternative to IB for market data streaming.
**Config:** `config/settings.json` → `databento` section
**Status:** Placeholder/early integration

Designed to stream real-time trade data from Databento's `GLBX.MDP3` dataset for futures symbols (NQ.FUT, MNQ.FUT).

### 2. clients/databento_enhanced.py — Enhanced Databento Client

Extended version with additional data processing capabilities.

### 3. clients/databento_streamer.py — Real-time Streamer

Dedicated streaming client for continuous market data feed from Databento.

### 4. clients/tradovate_client.py — Tradovate Futures Client

**Purpose:** Alternative broker for futures trading (MNQ, NQ).
**Config:** `config/settings.json` → `tradovate` section
**Status:** Placeholder/early integration

Supports:
- Demo and live API endpoints
- Authentication with username/password/client_id/secret
- REST API v1 interface

### 5. clients/__init__.py

Empty init file — makes `clients/` a Python package.

---

## Integration Status

### Currently Active (BOT.py core flow)

The main trading engine uses:
- **IB API** via `tws_api_client.py` for all market data and order execution
- **SuperTrend** (`Indicators.BOTSingal`) or **engulfing patterns** (inline in `BOT.py`) for signals
- **Manual ATR/VWAP/EMA** calculations in `BOT.py` functions

### Newer Architecture Layer (partially integrated)

The `strategies/`, `clients/`, and `utils/` directories use:
- Config-driven parameters from `config/settings.json`
- Class-based strategy patterns
- Enhanced database schema
- Categorized logging

These are **available but not fully wired** into the main `BOT.py` event loop. The `GUI.py` references some of these (e.g., `from utils.ui_animations import ThemeTransitionManager`, `from utils.logger import trading_logger`).

---

## Utils

### utils/database_manager.py — DatabaseManager

Enhanced SQLite database manager for the newer architecture. See `dataModels.md` for full schema.

Key features:
- Context manager for connections (`get_connection()`)
- Trade CRUD with UUID-based IDs
- Signal storage with execution tracking
- Performance metrics aggregation
- Session management (start/end with P&L)
- Candle data storage with retention cleanup
- Proper indexing for performance

### utils/logger.py — TradingLogger

Categorized logging system with multiple rotating file loggers.

| Logger | File | Level | Purpose |
|---|---|---|---|
| `trading` | `trading.log` | INFO | All trading activity |
| `trades` | `trades.log` | INFO | Trade entries/exits only |
| `errors` | `errors.log` | ERROR | Errors and exceptions |
| `system` | `system.log` | DEBUG | System events, connections |

**Global instance:** `trading_logger = TradingLogger()` — imported and used throughout strategies and utilities.

Convenience methods: `log_trade_entry()`, `log_trade_exit()`, `log_signal()`, `log_system_event()`, `log_connection_event()`, `log_error()`, `log_performance()`, `get_recent_logs()`.

### utils/ui_animations.py — UI Animations

See `guiReference.md` for full details. Provides theme transitions, button animations, status pulsing, loading spinners, and slide transitions for PyQt5 widgets.
