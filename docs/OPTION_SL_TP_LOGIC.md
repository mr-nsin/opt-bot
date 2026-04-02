# Option stop-loss and take-profit logic

This document describes the **previous** SL/TP behavior in `takeTrade` (removed April 2026), the **current** rule set, and how exits are enforced in `order_manager.py`.

## Where the numbers are used

- **`takeTrade`** in `BOT.py` sets `profitPrice` (take-profit anchor) and `auxPrice` (stop-loss) from the option **entry premium** (`tradePrice`) and an **ATR** value.
- **`placeOrder` / `placeAndVerifyOrder`** store these on `OptionOrder` as `profit_price`, `stoploss_price`, and initialise trailing state (`current_profit_price`, `profit_increment`).
- **`OrderManager.check_take_profit`** and **`check_stop_loss`** compare live option bid/ask/last to those levels (long BUY: TP above entry, SL below; short SELL: reversed).

## Previous logic (historical reference)

The old implementation (replaced in `takeTrade`) had these characteristics:

1. **ATR source**  
   Only the **underlying stock** ATR from `checkAlgoAndTrade` → `getATRValue` (21-bar WWMA-style ATR on the stock) was passed in as `atrVale`. It was then multiplied by global **`ATR_VALUE`** from `config.json` (typically ~0.99). There was **no** use of option-specific historical ATR.

2. **Scale mismatch**  
   Stock ATR is in **underlying dollars per share**; `tradePrice` is the **option premium**. Comparing and adding them directly mixed two different scales (e.g. a $2 stock ATR vs a $0.80 option).

3. **Complex branching**  
   After scaling, TP used a first guess `tradePrice + atrVale`, then many overrides by:
   - buckets of `atrVale` (e.g. `< 0.235`, `0.235–0.485`, `≥ 1.05`),
   - **time of day** (`marketTimeInt` vs 1201, 1301, etc.),
   - **days to expiry** (`TimeDecayDiffVal` from `timeDecayDiff`),
   - **0DTE** special cases (different % of premium by time window and premium level),
   - **cheap option** windows (`tradePrice ≤ 0.2`, etc.).

4. **Stop-loss**  
   SL was derived from the same scaled ATR with a parallel ladder of multipliers and DTE/time branches, not a single symmetric rule tied to “30% of premium vs ATR”.

5. **Duplication**  
   A large block of similar logic appeared twice (once inside a commented triple-quoted string and once live), which made behaviour hard to reason about and risked drift.

6. **Long-only entries**  
   `takeTrade` always called `placeAndVerifyOrder` with `action="BUY"`. TP/SL were always “long option” shaped (TP up, SL down).

## Current logic (implemented in `BOT.py`)

### Price

- **`PRICE`** = option premium used as entry reference: **`tradePrice`** (ask if tight spread, else bid per existing spread rules).

### ATR used for SL/TP

1. **Strike (option) ATR**  
   `try_get_option_atr_from_bars` looks up IBKR historical bars for the option contract key  
   `symbol + expiry + right + strike` (same string shape as `TwsApiClient.subscribe` for OPT).  
   If at least ~22 bars exist, ATR is computed with the same `getATR` helper used for stocks.

2. **Fallback: stock ATR**  
   If option bars are missing (normal today, because `init_data_feed` only subscribes historical data for **underlyings**, not each option), the algo’s **underlying ATR** (`atrVale` from `checkAlgoAndTrade`) is used.  
   **`ATR_VALUE` is not applied** to SL/TP anymore; the new rules compare ATR to **30% of the option premium**, which ties the threshold to the correct scale for the premium.

### Rules (long option premium)

Let `threshold = PRICE * 0.30`.

- If **`ATR > threshold`**:  
  - `TP = PRICE + PRICE * 0.30`  
  - `SL = PRICE - PRICE * 0.30`

- If **`ATR <= threshold`**:  
  - `TP = PRICE + ATR`  
  - `SL = PRICE - ATR`

### Short (reversed)

For a **short** premium position (`is_long=False` in `compute_sl_tp_from_price_and_atr`):

- Same **offset** as above, but  
  - `TP = PRICE - offset`  
  - `SL = PRICE + offset`  

`takeTrade` currently sets `is_long_entry = True` because entries are BUY-only; the helper is ready if short entries are added later.

### Low ATR / bad data

If resolved ATR for SL/TP is **`<= 0.01`**, a small floor is used: `TP = tradePrice + 0.02`, `SL = tradePrice - 0.01` (same idea as the old “low ATR” branch).

### 0DTE gates (unchanged intent)

Hard **no-trade** returns are still applied **before** SL/TP sizing when `timeDecayDiff(tradeExpiry_val) == 0`:

- Premium `≤ $0.10` in certain morning windows → `"0dtepricebelow10cent"`.
- After **14:45** ET → `"0dte2ndhalfnotrade"`.

SPY/QQQ still force `time_decay_dte = -1` so those 0DTE blocks do not apply in the same way as single-name 0DTE.

### Floor

- `SL` is never below **`0.01`** after calculation.

## Exit engine (`order_manager.py`) — unchanged contract

- **Long:** TP trail uses bid/last; SL uses bid vs `stoploss_price`.
- **Short:** TP trail uses ask/last; SL uses ask vs `stoploss_price`.
- A separate **10% of notional** profit rule can still close early regardless of ATR-based targets.

## Optional future improvement

To make **OPT** ATR the common path, either subscribe historical bars for traded option contracts or add a one-off historical request per contract before sizing SL/TP.
