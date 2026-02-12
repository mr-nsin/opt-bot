# Known Issues & Technical Debt — OPT_BOT

## Critical Issues

### 1. Heavy Global Variable Usage (BOT.py)

`BOT.py` declares ~30+ global variables at module level and modifies them from multiple threads. This creates:
- **Race conditions**: `STOP_TRADING`, `DAY_LOCKED`, `CLOSE_ALL_ORDERS`, `DAILY_LIMIT_HIT` are read/written from multiple threads without synchronization
- **Testability issues**: Cannot test functions in isolation
- **Initialization order dependency**: Config is read at import time, making module-level testing fragile

**Affected globals:** `client`, `event_queue`, `order_mgr`, `db`, `trade_time_dict`, `signal_dict`, `STOP_TRADING`, `DAILY_LIMIT_HIT`, `DAY_LOCKED`, `CLOSE_ALL_ORDERS`, `START_DAY_PNL`, plus all config-derived globals.

### 2. SQL Injection Vulnerability (data_access.py)

`update_option_order()` uses f-string interpolation for SQL queries:
```python
query = f"UPDATE option_orders SET order_status = '{option_order.order_status}', ..."
```
This is vulnerable to SQL injection if any order field contains malicious content. Should use parameterized queries like the other methods.

### 3. Dual Database Systems

Two separate SQLite databases exist with overlapping concerns:
- `db/orders.db` (DAL in `data_access.py`) — used by core engine
- `database/trades.db` (DatabaseManager in `utils/database_manager.py`) — used by newer layers

No synchronization or migration path between them. Trades in one system are invisible to the other.

### 4. Three Logger Implementations

Three separate logging systems that may conflict:
1. `common.py` → `setup_logger('bot')` — primary, used throughout core
2. `logger.py` → `Loggers` class — secondary, imported by BOT.py  
3. `utils/logger.py` → `TradingLogger` — used by strategies/utils

All write to `logs/` directory with different naming conventions and formats.

---

## Moderate Issues

### 5. Hardcoded License Credentials (GUI.py)

License validation parameters are hardcoded in source:
```python
IP_Validate = "192.168.0.100"
email_validate = "longnguyen347@yahoo.com"
key_to_validate = "quant-drift-$987$-&x1$(-*0#!("
```
Anyone with source access can generate valid license keys.

### 6. Two License Systems

- `GUI.py`: SHA-256 hash-based with `{ip, email, key, start_date, days}`
- `BOT.py`: Base64 encoded issue date, 90-day validity

These are independent — validating in GUI doesn't validate in BOT and vice versa.

### 7. Broad Exception Handling

Many try/except blocks catch `Exception` or bare `except:` without logging or re-raising:
```python
except Exception as e:
    pass  # Silently swallows errors
```

This makes debugging extremely difficult in production. Found in:
- `GUI.py`: theme transitions, icon loading, timer updates
- `tws_api_client.py`: reconnection attempts
- `BOT.py`: various trade execution paths
- `utils/ui_animations.py`: all animation methods

### 8. Commented-Out Code

Extensive commented-out code blocks throughout:
- `BOT.py`: Old function implementations, alternative logic paths (~200+ lines)
- `GUI.py`: Commented-out validation logic, alternative theme code
- `tws_api_client.py`: Old contract detail methods, PnL handling

### 9. Incomplete Strike Data (expiryStrike.json)

Some symbols have very few strikes stored:
- `SPY`: only 3 strikes (616.0, 10.01, 10010.0) — clearly incomplete
- `QQQ`: only 1 strike (561.0)
- `AAPL`: only 1 strike (249.0)
- `MSFT`: only 1 strike (500.0)

The bot may need to fetch strikes dynamically at runtime if this data is stale.

### 10. Duplicate TwsApiClient `connectionClosed` Method

`tws_api_client.py` defines `connectionClosed()` twice (lines ~63 and ~736). The second definition overrides the first, which means the reconnection logic in the first definition is dead code.

### 11. Mixed Naming Conventions

- Snake_case: `check_take_profit`, `order_manager`
- CamelCase: `getCallPutEngulfCheck`, `checkConditionsAndTrade`
- Mixed: `checkAlgoAndTrade`, `placeAndVerifyOrder`
- Debug markers: `"99999999999999999"`, `"11111111111111"`, `"00000000000000"` in log messages

---

## Minor Issues

### 12. Windows-Specific Path Separators

`logger.py` uses `\\` (Windows backslash):
```python
logPath = os.getcwd()+'\\Logs\\'+self.logFileName
```
This will fail on macOS/Linux.

### 13. Unused Imports

Several files import modules that aren't used:
- `BOT.py`: `Pool` from multiprocessing, `base64`, `random`
- `GUI.py`: `QSplitter`, `QScrollArea` (imported but unused)

### 14. TK_GUI.py (Legacy)

The Tkinter GUI still exists but is not maintained. It may confuse developers or be accidentally used.

### 15. Missing Error Recovery in DAL

The `handle_orders_queue()` thread runs an infinite while loop. If any unhandled exception occurs (e.g., database corruption), the entire order processing pipeline stops silently.

### 16. Event Queue Processing

`event_processor` uses `Queue.get()` which blocks forever. If the main trading loop needs to stop, it relies on checking `STOP_TRADING` flag, but this check may not occur if the queue is empty and `get()` is blocking.

### 17. Config Writes Not Atomic

GUI writes to `config.json` and `config/settings.json` using `json.dump()` without:
- File locking
- Atomic write (write to temp file → rename)
- Backup of previous config

A crash during write could corrupt the config files.

### 18. No Test Suite

There are zero test files in the project. No unit tests, integration tests, or strategy backtests.

---

## Improvement Opportunities

1. **Refactor BOT.py** into a class-based `TradingEngine` — eliminate globals, improve testability
2. **Consolidate databases** — single SQLite schema with migration support
3. **Consolidate loggers** — single logging configuration used everywhere
4. **Fix SQL injection** — use parameterized queries in `update_option_order()`
5. **Add proper threading** — use `threading.Event` for stop signals, proper `Queue.get(timeout=)` 
6. **Remove dead code** — clean up commented blocks and unused imports
7. **Add tests** — at minimum for signal detection, order management, and TP/SL logic
8. **Externalize secrets** — move license params to environment variables
9. **Use pathlib** — replace string path concatenation with `pathlib.Path`
10. **Add type hints** — many functions lack return type and parameter type annotations
