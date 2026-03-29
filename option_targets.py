"""
Option premium TP/SL targets: pure helpers (unit-tested).

Underlying ATR is converted to a dollar distance, then capped to a fraction of option
premium so cheap options do not get stock-sized TP/SL widths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class OptionTpSlResult:
    """Initial TP/SL and trailing cap / SL floor for a long option entry."""

    profit_price: float
    aux_price: float
    max_tp_price: float
    min_sl_price: float
    atr_dist_raw: float
    dist_applied: float


def compute_option_tp_sl(
    trade_price: float,
    atr_vale: float,
    atr_value_mult: float,
    *,
    max_move_fraction: float = 0.15,
    min_dist_dollars: float = 0.02,
) -> OptionTpSlResult:
    """
    Compute symmetric TP/SL distance in premium dollars for a long option.

    - Start from underlying ATR (same construction as legacy takeTrade).
    - Cap distance to ``trade_price * max_move_fraction`` (default 15% of premium each way).
    - Apply a small minimum distance in dollars (clamped so it never exceeds the premium cap).

    Args:
        trade_price: Limit / working price used as entry reference (premium per share).
        atr_vale: Last underlying ATR (same units as stock price).
        atr_value_mult: Config ATR_VALUE (e.g. 0.99).
        max_move_fraction: Max |TP-entry| and |entry-SL| as a fraction of premium.
        min_dist_dollars: Floor on distance after capping (e.g. 0.02).

    Returns:
        OptionTpSlResult with rounded prices to 2 decimals.
    """
    if trade_price <= 0:
        raise ValueError("trade_price must be positive")
    if max_move_fraction <= 0:
        raise ValueError("max_move_fraction must be positive")

    if atr_vale <= 0.01:
        base_dist = 0.02
    else:
        base_dist = float(atr_vale) * float(atr_value_mult)
    atr_risk_cap = (atr_vale * 0.9) if atr_vale > 0.01 else 0.018
    atr_dist_raw = min(base_dist, float(atr_risk_cap))

    premium_cap_dist = float(trade_price) * float(max_move_fraction)
    dist = min(atr_dist_raw, premium_cap_dist)
    # Floor: at least min_dist, but never more than half the premium (sanity)
    floor_candidate = min(float(min_dist_dollars), float(trade_price) * 0.5)
    dist = max(dist, floor_candidate)
    dist = min(dist, premium_cap_dist)

    profit_price = round(trade_price + dist, 2)
    aux_price = round(trade_price - dist, 2)
    if aux_price < 0.01:
        aux_price = 0.01

    # Trailing TP ceiling must be *wider* than initial TP. When max_tp_price == profit_price,
    # OrderManager._cap_trailing_tp clamps every ratchet back to the initial target, so the
    # effective trail never moves up with price (late exits / confusing SL&TP behaviour).
    trail_ceiling_pct = min(float(max_move_fraction) * 2.5, 0.45)
    max_tp_price = round(float(trade_price) * (1.0 + trail_ceiling_pct), 2)
    if max_tp_price < profit_price:
        max_tp_price = profit_price

    min_sl_price = round(max(0.01, trade_price - dist), 2)
    if min_sl_price > aux_price:
        min_sl_price = aux_price

    return OptionTpSlResult(
        profit_price=profit_price,
        aux_price=aux_price,
        max_tp_price=max_tp_price,
        min_sl_price=min_sl_price,
        atr_dist_raw=atr_dist_raw,
        dist_applied=dist,
    )


def targets_from_config(
    trade_price: float,
    atr_vale: float,
    config: Mapping[str, Any],
) -> OptionTpSlResult:
    """Build targets using BOT-style config keys (ATR_VALUE, option_tp_sl_*)."""
    atr_mult = float(config.get("ATR_VALUE", 0.99))
    max_frac = float(config.get("option_tp_sl_max_pct", 0.15))
    min_dist = float(config.get("option_tp_sl_min_dist", 0.02))
    return compute_option_tp_sl(
        trade_price,
        atr_vale,
        atr_mult,
        max_move_fraction=max_frac,
        min_dist_dollars=min_dist,
    )


def normalize_ibkr_option_avg_premium(
    avg_cost: float | None,
    order_avg_fill: float | None = None,
) -> float:
    """
    Average cost basis for an option position for PnL / UI.

    IBKR's position() avgCost for US equity options is normally the **average premium per
    contract share** (same units as the option quote), not ``premium * 100``.

    Prefer the order manager's fill price when present. A legacy bug divided avgCost by 100
    whenever it was > 1, which breaks essentially all premiums above $1.00.
    """
    eo = float(order_avg_fill or 0)
    if eo > 0:
        return round(eo, 6)
    ac = float(avg_cost or 0)
    if ac <= 0:
        return 0.0
    # If TWS ever reports total contract dollars (e.g. ~150 for a $1.50 quote), map down.
    if ac >= 50.0:
        scaled = ac / 100.0
        if 0.03 <= scaled <= 80.0:
            return round(scaled, 6)
    return round(ac, 6)


def backfill_order_tp_sl_caps(order: Any) -> None:
    """
    When max_tp_price / min_sl_price were not persisted (legacy DB), infer safe caps
    from fill/limit price and clamp runaway trailing targets.
    """
    if getattr(order, "exit_order", False):
        return
    ref = float(getattr(order, "average_price", 0) or 0) or float(getattr(order, "order_price", 0) or 0)
    if ref <= 0:
        return
    cap_tp = round(ref * 1.15, 2)
    floor_sl = round(max(0.01, ref * 0.85), 2)

    if getattr(order, "max_tp_price", None) is None:
        ipp = float(getattr(order, "profit_price", 0) or 0)
        order.max_tp_price = min(ipp, cap_tp) if ipp > 0 else cap_tp
    if getattr(order, "min_sl_price", None) is None:
        order.min_sl_price = floor_sl

    mtp = float(getattr(order, "max_tp_price", 0) or 0)
    cpp = float(getattr(order, "current_profit_price", 0) or 0)
    if mtp > 0 and cpp > mtp:
        order.current_profit_price = mtp
