# Data Models & Database Schema — OPT_BOT

## Python Dataclasses (common.py)

### OptionOrder

The central order tracking object. Used throughout the system for both entry and exit orders.

```python
@dataclass
class OptionOrder:
    id: int = None                  # IB order ID
    conId: int = None               # IB contract ID
    symbol: str = None              # e.g., "TSLA"
    expiration: str = None          # e.g., "20250815"
    strike: float = None            # e.g., 250.0
    right: str = None               # "CALL" or "PUT"
    order_type: str = None          # "LMT", "MKT"
    order_side: str = None          # "BUY" or "SELL"
    order_qty: int = None           # Number of contracts
    order_price: float = None       # Limit price
    order_status: str = None        # "Pending", "submitted", "filled", "cancelled", etc.
    executed_qty: int = 0           # Filled quantity
    average_price: float = 0        # Average fill price
    profit_price: float = None      # Initial take profit target
    stoploss_price: float = None    # Stop loss price
    profit_trigger: bool = False    # Whether trailing profit is activated
    current_profit_price: float = 0.0  # Current trailing profit target
    profit_increment: float = 0.0   # Step size for trailing profit
    contract: Contract = None       # IB Contract object
    exit_placed: bool = False       # Whether exit order has been sent
    exit_order: bool = False        # True if this IS an exit order
    active: bool = False            # Active until position closed or rejected
    ref_order_id: int = None        # For exit orders: points to entry order ID

    @property
    def option_symbol(self) -> str:
        return f"{self.symbol}{self.expiration}{self.right}{self.strike}"
```

### Tick

Real-time market data container. One per subscribed contract.

```python
@dataclass
class Tick:
    symbol: str = None              # Ticker string (e.g., "TSLA" or "TSLA20250815C250.0")
    contract: Contract = None       # IB Contract object
    ask: float = -1                 # Ask price
    bid: float = -1                 # Bid price
    close: float = -1               # Previous close
    last: float = -1                # Last traded price
    delta: float = -1               # Options delta
    volume: int = -1                # Volume
    open_interest_call: float = -1  # Call open interest
    open_interest_put: float = -1   # Put open interest
    active_order: OptionOrder = None # Currently active order on this tick
    locked: bool = False            # Prevents concurrent order placement
    last_trade_time: datetime = None # Time of last trade closure (for cooldown)
    busy: bool = False              # Prevents concurrent TP/SL checks
    option_symbol: str = None       # Human-readable option symbol

    @property
    def open_interest(self) -> float:
        # Returns call or put OI based on contract right
```

### Position

IB account position snapshot.

```python
@dataclass
class Position:
    account: str = None             # IB account ID
    symbol: str = None              # e.g., "TSLA"
    position: int = None            # Number of contracts (0 = closed)
    strike: float = None
    right: str = None               # "C" or "P"
    expiry: str = None              # "20250815"
```

### PNL

Account P&L data.

```python
@dataclass
class PNL:
    account: str = None
    dailyPnL: float = None
    unrealizedPnL: float = None
    realizedPnL: float = None
```

### Trade

Order execution/status tracking (from IB callbacks).

```python
@dataclass
class Trade:
    orderId: int = 0
    contract: Contract = None
    order: Order = None
    orderStatus: OrderState = None
    executed_qty: float = None
    remaining_qty: float = None
    average_price: float = None
    last_fill_price: float = None
    order_status: str = None        # Lowercase status string
```

---

## Database Schema 1: db/orders.db (data_access.py)

Used by the core trading engine for order persistence.

### Table: option_orders

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER | PK | IB order ID |
| `conId` | INTEGER | Yes | IB contract ID |
| `symbol` | TEXT | Yes | Stock symbol |
| `expiration` | TEXT | Yes | Expiry date (YYYYMMDD) |
| `strike` | REAL | Yes | Strike price |
| `right` | TEXT | Yes | CALL/PUT |
| `order_type` | TEXT | Yes | LMT/MKT |
| `order_side` | TEXT | Yes | BUY/SELL |
| `order_qty` | INTEGER | Yes | Quantity |
| `order_price` | REAL | Yes | Limit price |
| `order_status` | TEXT | Yes | Current status |
| `executed_qty` | INTEGER | Yes | Filled quantity |
| `average_price` | REAL | Yes | Avg fill price |
| `profit_price` | REAL | Yes | Initial profit target |
| `stoploss_price` | REAL | Yes | Stop loss price |
| `profit_trigger` | INTEGER | Yes | Boolean (0/1) |
| `current_profit_price` | REAL | Yes | Trailing profit target |
| `profit_increment` | REAL | Yes | Trailing step |
| `contract` | TEXT | Yes | Serialized contract (unused) |
| `exit_placed` | INTEGER | Yes | Boolean (0/1) |
| `exit_order` | INTEGER | Yes | Boolean (0/1) |
| `active` | INTEGER | Yes | Boolean (0/1) |
| `ref_order_id` | INTEGER | Yes | Links exit → entry |

**Access pattern:** Queue-based async writes via DAL thread. Read at startup to recover state.

---

## Database Schema 2: database/trades.db (utils/database_manager.py)

Used by the newer strategy/client layer for enhanced tracking.

### Table: trades

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK AUTO | Auto-increment ID |
| `trade_id` | TEXT UNIQUE | UUID trade identifier |
| `symbol` | TEXT | Trading symbol |
| `strategy` | TEXT | Strategy name |
| `side` | TEXT | BUY/SELL |
| `entry_time` | TIMESTAMP | Entry timestamp |
| `entry_price` | DECIMAL(10,4) | Entry price |
| `exit_time` | TIMESTAMP | Exit timestamp |
| `exit_price` | DECIMAL(10,4) | Exit price |
| `quantity` | INTEGER | Position size |
| `pnl` | DECIMAL(10,2) | Profit/loss |
| `status` | TEXT | OPEN/CLOSED |
| `stop_loss` | DECIMAL(10,4) | SL price |
| `take_profit` | DECIMAL(10,4) | TP price |
| `atr_value` | DECIMAL(10,4) | ATR at entry |
| `signal_strength` | DECIMAL(5,2) | Signal strength 0-1 |
| `signal_type` | TEXT | Signal type |
| `volume_ratio` | REAL | Volume ratio at signal |
| `created_at` | TIMESTAMP | Record creation time |

### Table: signals

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK AUTO | Auto-increment |
| `signal_id` | TEXT UNIQUE | UUID |
| `symbol` | TEXT | Symbol |
| `strategy` | TEXT | Strategy name |
| `signal_type` | TEXT | BUY/SELL |
| `signal_strength` | DECIMAL(5,2) | Strength 0-1 |
| `price` | DECIMAL(10,4) | Price at signal |
| `atr_value` | DECIMAL(10,4) | ATR value |
| `volume_confirmation` | BOOLEAN | Volume confirmed |
| `timestamp` | TIMESTAMP | Signal time |
| `executed` | BOOLEAN | Whether trade was taken |

### Table: performance_metrics

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK AUTO | Auto-increment |
| `date` | DATE | Trading date |
| `total_trades` | INTEGER | Count |
| `winning_trades` | INTEGER | Wins |
| `losing_trades` | INTEGER | Losses |
| `gross_profit` | DECIMAL(10,2) | Total profit |
| `gross_loss` | DECIMAL(10,2) | Total loss |
| `net_profit` | DECIMAL(10,2) | Net P&L |
| `win_rate` | DECIMAL(5,2) | Win % |
| `avg_win` | DECIMAL(10,2) | Avg winning trade |
| `avg_loss` | DECIMAL(10,2) | Avg losing trade |
| `max_drawdown` | DECIMAL(10,2) | Max drawdown |

### Table: sessions

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK AUTO | Auto-increment |
| `session_id` | TEXT UNIQUE | UUID |
| `start_time` | TIMESTAMP | Session start |
| `end_time` | TIMESTAMP | Session end |
| `status` | TEXT | ACTIVE/COMPLETED |
| `initial_balance` | DECIMAL(10,2) | Starting balance |
| `final_balance` | DECIMAL(10,2) | Ending balance |
| `trades_count` | INTEGER | Trades in session |
| `net_pnl` | DECIMAL(10,2) | Session P&L |

### Table: candle_data

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK AUTO | Auto-increment |
| `symbol` | TEXT | Symbol |
| `timestamp` | DATETIME | Candle time |
| `open_price` | REAL | Open |
| `high_price` | REAL | High |
| `low_price` | REAL | Low |
| `close_price` | REAL | Close |
| `volume` | INTEGER | Volume |
| `created_at` | DATETIME | Record time |

**Indexes:**
- `idx_candle_symbol_timestamp` on `candle_data(symbol, timestamp DESC)`
- `idx_trades_symbol_time` on `trades(symbol, entry_time DESC)`

---

## In-Memory Caches (TwsApiClient)

| Cache | Key | Value | Populated By |
|---|---|---|---|
| `tick_cache` | ticker_id (int) | `Tick` object | `tickPrice`, `tickSize`, `tickOptionComputation` |
| `ticker_id_contract_cache` | ticker string | ticker_id (int) | `subscribe()` |
| `ticker_contract_cache` | ticker string | `Contract` object | `get_stock_contract`, `get_options_contract` |
| `history_cache` | reqId (int) | `{date: BarData}` | `historicalData`, `historicalDataUpdate` |
| `positions` | ticker string | `Position` object | `position()` callback |
| `trades_cache` | orderId (int) | `Trade` object | `openOrder()`, `orderStatus()` |
| `pnl_cache` | string key | float | `pnl()` callback |

## In-Memory Caches (OrderManager)

| Cache | Key | Value | Purpose |
|---|---|---|---|
| `orders_cache` | order_id (int) | `OptionOrder` | All tracked orders |
| `entry_orders_cache` | symbol (str) | `OptionOrder` | Active entry orders by symbol |
| `exit_orders_cache` | symbol (str) | `OptionOrder` | Active exit orders by symbol |
| `order_id_tick_lookup` | order_id (int) | `Tick` | Links order to its price stream |
| `recent_trade_closures` | `"{symbol}_{right}"` | `datetime` | Cooldown tracking |

## In-Memory State (BOT.py)

| Variable | Key | Value | Purpose |
|---|---|---|---|
| `trade_time_dict` | `"{symbol}_{right}"` | `datetime` | Cooldown tracking (mirrors OrderManager) |
| `signal_dict` | symbol (str) | `{last_signal, current_signal}` | SuperTrend signal state |
