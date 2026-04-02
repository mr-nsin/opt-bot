# Latency Architecture: Current State & Future Roadmap

## Current Pipeline (After Option A Optimizations)

```
IBKR TWS Socket
    |
    v
EClient.run() reader thread (ibapi)
    |  tickPrice() / tickSize() callbacks fire on this thread
    |  Lock acquired on tick_cache (~1ms)
    v
queue.Queue.put(tick)              ← ~0.1ms
    |
    v  (4 event_processor threads consume, block=True timeout=50ms)
event_processor thread
    |  OPT tick → check_and_close_position() [per-order Lock, ~1-5ms]
    |  STK tick → getCallPutEngulfCheck() [signal scan, ~10-50ms]
    v
(TP/SL hit?) → order_manager.close_position() → placeOrder() to TWS
    |
    v  (every 100ms)
_emit_positions() → builds position list [cached 50ms] → emit_positions_snapshot()
    |  1 JSON line to stdout (all positions batched)
    v
Rust sidecar reader (tokio async, ~0.5ms)
    |  parse JSON → update AppState → emit to React
    v
Tauri IPC emit("trading:positions_snapshot")   ← ~1ms
    |
    v
React useTradingEvents handler → setPositions() → re-render
    |  PnL throttled to 100ms
    v
UI updated                         TOTAL: ~50-150ms tick-to-UI
```

### Current Latency Budget

| Stage | Latency | Notes |
|-------|---------|-------|
| IBKR socket → tickPrice callback | ~0ms | Handled by ibapi EReader |
| Lock + queue.put | ~0.1ms | threading.Lock on tick_cache |
| queue.get (event_processor) | 0-50ms | block=True, timeout=0.05 |
| TP/SL check | 1-5ms | Per-order Lock, no dropped ticks |
| Position emission interval | 0-100ms | _positions_interval_sec = 0.1 |
| get_positions() rebuild | 0ms (cached) or 5-10ms | 50ms cache TTL |
| JSON serialize + stdout | ~0.1ms | Batched, all positions in 1 call |
| Rust parse + AppState update | ~0.5ms | tokio async |
| Tauri emit IPC | ~1ms | WebView bridge |
| React state + render | ~5ms | Zustand setPositions |
| **Total tick-to-UI** | **~50-150ms** | |
| **Total tick-to-TP/SL** | **~0.1-50ms** | Primary path via event_processor |

---

## Future Optimization Tiers

### Tier 1: deque + Condition Variable (Est: 3-4 hours, Medium risk)

**Problem:** `queue.Queue` uses mutex internally. Under high tick rates (50+ ticks/sec), GIL + mutex contention adds ~0.05ms per put/get.

**Solution:** Replace `queue.Queue` with `collections.deque` + `threading.Condition`:

```python
# Current
from queue import Queue
event_queue = Queue()
# Producer: event_queue.put(tick)
# Consumer: event_queue.get(block=True, timeout=0.05)

# Proposed
from collections import deque
import threading

class FastTickQueue:
    def __init__(self):
        self._deque = deque()
        self._cond = threading.Condition()

    def put(self, item):
        with self._cond:
            self._deque.append(item)
            self._cond.notify()  # Wake ONE waiting consumer

    def get(self, timeout=0.05):
        with self._cond:
            while not self._deque:
                if not self._cond.wait(timeout):
                    raise Empty()
            return self._deque.popleft()

    def qsize(self):
        return len(self._deque)
```

**Why faster:** `deque.append()` and `deque.popleft()` are O(1) C-implemented atomic operations. The Condition variable only wakes consumers when data arrives (no busy-loop, no spurious wakeups).

**Expected improvement:** ~0.02-0.05ms per tick (marginal at current volumes, meaningful at 100+ ticks/sec).

**Files:** `BOT.py` (replace Queue import + event_queue creation), `trading_engine.py` (update _event_queue usage)

---

### Tier 2: asyncio Bridge (Est: 8-12 hours, High risk)

**Problem:** ibapi is strictly threading-based. 4 event_processor threads + EClient reader thread contend for GIL. Python's GIL means only 1 thread runs Python bytecode at a time.

**Solution:** Keep ibapi on its own thread, but bridge callbacks into an asyncio event loop:

```python
# In tws_api_client.py tickPrice callback:
def tickPrice(self, reqId, tickType, price, attrib):
    with self._lock:
        tick = self.tick_cache.get(reqId)
        if tick is None: return
        if tickType == 1: tick.bid = price
        elif tickType == 4: tick.last = price
        # Bridge to asyncio instead of queue.put()
        if self._async_loop and self._async_queue:
            self._async_loop.call_soon_threadsafe(
                self._async_queue.put_nowait, {"tick": tick}
            )

# In event processor (now async coroutine):
async def event_processor(async_queue, count):
    while not STOP_TRADING:
        try:
            event_data = await asyncio.wait_for(async_queue.get(), timeout=0.05)
            tick = event_data["tick"]
            if tick.contract.secType == "OPT" and tick.active_order:
                order_mgr.check_and_close_position(tick=tick)
            elif tick.contract.secType == "STK":
                # Run CPU-bound signal scan in executor to not block event loop
                await loop.run_in_executor(None, process_stk_tick, tick)
        except asyncio.TimeoutError:
            pass
```

**Benefits:**
- Single event loop replaces 4 competing threads
- `asyncio.Queue.get()` is zero-overhead wait (no GIL contention)
- CPU-bound work (signal scans) offloaded to thread pool via `run_in_executor`
- Better backpressure: if queue grows, we know immediately

**Risks:**
- BOT.py has 2400+ lines of deeply threaded code — many globals, thread-local state
- ibapi callbacks still fire on EClient thread (can't change)
- `call_soon_threadsafe` adds ~0.01ms overhead per tick
- Regression risk in TP/SL timing if async scheduling delays checks

**Files:** `tws_api_client.py`, `BOT.py`, `trading_engine.py`

---

### Tier 3: ib-insync / ib_async (Est: 2-3 days, High risk)

**What:** `ib-insync` (by Ewald de Wit) is a popular wrapper around ibapi that provides:
- Asyncio-native event loop
- Automatic reconnection
- Clean position/order/trade objects
- Built-in throttling for API rate limits

`ib_async` is its successor (same author, Python 3.12+ only).

**How it works:**
```python
from ib_insync import IB, util
ib = IB()
await ib.connectAsync('127.0.0.1', 7497, clientId=1)

# Positions are live-updated objects
positions = ib.positions()

# Subscribe to tick updates
ticker = ib.reqMktData(contract)
ticker.updateEvent += on_tick  # Event-driven, no polling

# Order placement
order = MarketOrder('SELL', 1)
trade = ib.placeOrder(contract, order)
trade.filledEvent += on_filled  # Callback when filled
```

**Benefits:**
- Eliminates all threading complexity (single asyncio loop)
- Built-in position reconciliation
- Trade objects with event callbacks (no manual order status tracking)
- Production-proven (used by many prop trading firms)

**Risks:**
- **Major rewrite**: Would replace tws_api_client.py, large parts of BOT.py, order_manager.py
- ib-insync is in maintenance mode (author recommends ib_async)
- ib_async requires Python 3.12+ (already using 3.12, so OK)
- Different API surface — all existing order/position logic needs porting

**Expected improvement:** Eliminates GIL contention entirely. Tick-to-TP/SL would be ~0.1-1ms (just the callback + check).

**Files:** `tws_api_client.py` (full rewrite), `BOT.py` (major refactor), `order_manager.py` (adapt to ib-insync Trade objects)

---

### Tier 4: Rust-Native IBKR Client (Est: 2-4 weeks, Very high risk)

**What:** Eliminate the Python sidecar entirely. Write the trading engine in Rust, talking directly to TWS via the IBKR socket protocol.

**Available crates:**
- No mature Rust crate for IBKR TWS API exists as of 2025
- Would need to implement the TWS wire protocol in Rust (binary framing, message IDs, callback dispatch)
- Or use FFI to call the C++ TWS API library

**Benefits:**
- Zero GIL, zero Python overhead
- Tick-to-TP/SL in microseconds
- Direct Tauri integration (no IPC boundary)
- Single binary distribution

**Risks:**
- No existing Rust IBKR crate — must implement protocol from scratch
- TWS protocol is undocumented (reverse-engineered from Java/Python clients)
- All trading logic (signals, TP/SL, order management) must be ported to Rust
- Testing against live IBKR is complex

**Expected improvement:** Tick-to-UI in <1ms. Tick-to-TP/SL in <0.1ms.

---

### Tier 5: Shared Memory for IPC (Est: 1-2 days, Medium risk)

**What:** Replace JSON-over-stdio with `multiprocessing.shared_memory` for zero-copy data sharing between Python sidecar and Rust.

```python
# Python side
from multiprocessing import shared_memory
shm = shared_memory.SharedMemory(name='positions', create=True, size=4096)
# Write position data as packed struct directly to shared memory
struct.pack_into('!10s f f f f', shm.buf, offset, symbol, strike, price, pnl, ...)

# Rust side (via mmap)
let shm = SharedMemory::open("positions")?;
let positions: &[PositionData] = unsafe { shm.as_slice() };
```

**Benefits:**
- Zero serialization cost (binary struct, not JSON)
- Zero copy (both processes read/write same memory)
- ~0.001ms per position update vs ~0.1ms for JSON

**Risks:**
- Platform-specific (POSIX shm on macOS/Linux, named shared memory on Windows)
- Manual memory layout management (no schema evolution)
- Synchronization via atomic flags or mutexes
- Harder to debug than JSON lines

**Expected improvement:** IPC latency from ~0.1-0.5ms → ~0.001ms. Marginal overall impact since IPC is not the bottleneck.

---

### Tier 6: ZeroMQ / nanomsg (Est: 1 day, Low risk)

**What:** Replace stdio pipes with ZeroMQ (or nanomsg) for structured message passing.

```python
# Python
import zmq
ctx = zmq.Context()
pub = ctx.socket(zmq.PUB)
pub.bind("ipc:///tmp/trading-engine")
pub.send_json({"event": "positions_snapshot", "data": positions})

# Rust
let sub = zmq::Context::new().socket(zmq::SUB)?;
sub.connect("ipc:///tmp/trading-engine")?;
```

**Benefits:**
- Built-in framing (no line-delimiter parsing)
- PUB/SUB pattern for multiple subscribers
- IPC transport (Unix domain sockets) is faster than stdio pipes
- Backpressure via HWM (high-water mark)

**Risks:**
- Additional dependency (libzmq)
- Replaces Tauri's built-in shell plugin stdio mechanism
- Need to manage socket lifecycle

**Expected improvement:** ~0.05-0.1ms improvement on IPC. Marginal.

---

## Recommendation Priority

| Priority | Tier | Effort | Risk | Latency Gain | When |
|----------|------|--------|------|-------------|------|
| **Done** | Option A (Quick wins) | 2h | Low | 500-1200ms → 50-150ms | Now |
| **Next** | Tier 1 (deque+Condition) | 3-4h | Medium | ~5-10ms | Next sprint |
| **Later** | Tier 3 (ib-insync/ib_async) | 2-3 days | High | 50ms → 1-5ms | When ready for major refactor |
| **Maybe** | Tier 2 (asyncio bridge) | 8-12h | High | ~10-30ms | Only if skipping Tier 3 |
| **Skip** | Tier 4 (Rust native) | 2-4 weeks | Very high | <1ms | Only if Python becomes bottleneck |
| **Skip** | Tier 5 (SharedMemory) | 1-2 days | Medium | ~0.1ms | IPC is not the bottleneck |
| **Skip** | Tier 6 (ZeroMQ) | 1 day | Low | ~0.05ms | IPC is not the bottleneck |

## Key Insight

The **single biggest remaining bottleneck** is the polling model itself. Even at 100ms intervals, positions are polled, not pushed. The ideal architecture (Tier 3: ib-insync) would make everything event-driven:

```
# Current: tick → queue → processor → (wait 100ms) → emit positions
# Ideal:   tick → callback → update position → emit immediately
```

ib-insync/ib_async achieves this by wrapping every IBKR callback as an async event. When a tick arrives, the position P&L is recalculated and emitted in the same event loop iteration (~0.1ms).

## What Professional Platforms Do

| Platform | Architecture | Tick-to-UI |
|----------|-------------|-----------|
| IBKR TWS | Java Swing, event-driven callbacks | ~5ms |
| NinjaTrader | C#, event-driven, LMAX-style ring buffer | ~1ms |
| Sierra Chart | C++, single-threaded, lock-free circular buffer | <1ms |
| TradingView | WebSocket → React, delta updates only | ~50ms |
| NautilusTrader | Rust core + Python control, event-sourced | ~0.01ms |
| **Our app (after Option A)** | **Python threading → Rust → React, polling** | **~50-150ms** |

The gap between our 50-150ms and TWS's 5ms is primarily the polling model + Python GIL. Tier 3 (ib-insync) would close most of that gap.
