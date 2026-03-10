# Sideways Market Detection & Strategy Ideas

For momentum-based scalping, sideways/ranging markets cause whipsaws and false signals. Below are practical ways to detect sideways conditions and skip trades.

---

## 1. ADX (Average Directional Index) — Strong Trend Filter

**Idea:** ADX < 25–30 = weak/no trend = sideways. Only trade when ADX > threshold.

**Implementation:**
- Add ADX(14) to `Indicators.py` using +DI, -DI, DX, and smoothed DX
- In `checkAlgoAndTrade` or before `checkConditionsAndTrade`: if ADX < 25, return `toTrade = False`
- Config: `adx_min_trend = 25` (tunable)

**Pros:** Standard, widely used  
**Cons:** ADX lags; needs extra bars

---

## 2. ATR as % of Price — Low Volatility Filter (You Already Have This)

**Current:** `ATR_CHECKS` (e.g. 0.047) — if ATR < threshold, skip trade.

**Improvement:**
- Use ATR as % of close: `atr_pct = ATR / close * 100`
- Sideways: ATR% often < 0.5–1% for indices
- Add config: `atr_pct_min` — skip when `atr_pct < atr_pct_min`
- Or tighten existing `ATR_CHECKS` for more conservative entries

---

## 3. Bollinger Band Width — Range Contraction

**Idea:** Narrow bands = low volatility = sideways.

**Implementation:**
- BB width = (upper - lower) / middle
- If width < threshold (e.g. 2–3% of price), skip trade
- Config: `bb_width_min` — only trade when width > this

---

## 4. Price vs. Recent Range — Choppy Price Action

**Idea:** Price oscillating inside a narrow range = sideways.

**Implementation:**
- Last N bars: `range_high = max(high)`, `range_low = min(low)`, `range_size = range_high - range_low`
- If `range_size / close < X%` (e.g. 1%), skip
- Or: count how many bars close near the middle of the range — many = choppy

---

## 5. SuperTrend Flip Frequency — Whipsaw Detection

**Idea:** Many SuperTrend flips in few bars = whipsaw = sideways.

**Implementation:**
- Track last 5–10 bars’ SuperTrend values
- If flips in last N bars > 2, skip (e.g. BUY→SELL→BUY in 3 bars)
- Store flip count in `signal_dict[stock]['recent_flips']`

---

## 6. EMA Slope — Weak Trend

**Idea:** Flat EMA = no trend = sideways.

**Implementation:**
- EMA(20) slope = (EMA_now - EMA_5_bars_ago) / 5
- If |slope| < X% of price per bar, skip
- You already have `EMA_8_13_21` in `checkAlgoAndTrade` — add slope check

---

## 7. Combined Filter (Recommended)

Use 2–3 filters together:

1. **ADX > 25** — require some trend
2. **ATR% > threshold** — require enough volatility (you have ATR_CHECKS)
3. **SuperTrend flip count** — avoid recent whipsaws

**Suggested order:**
1. Implement ADX in `Indicators.py`
2. Add `is_sideways(stock, bars)` returning True when ADX < 25 (or similar)
3. In `getCallPutEngulfCheck` or `checkConditionsAndTrade`: if `is_sideways()`, return `False` before trading

---

## Config Additions (for later)

```json
{
  "adx_period": 14,
  "adx_min_trend": 25,
  "skip_sideways": true,
  "atr_pct_min": 0.5
}
```

---

## Files to Modify (when implementing)

- `Indicators.py` — add ADX, BB width, or EMA slope
- `BOT.py` — `checkAlgoAndTrade` or new `is_sideways()` helper
- `config.json` / `config_state.rs` — new params
- `trading_engine.py` — pass new config to BOT
