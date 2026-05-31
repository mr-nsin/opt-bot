"""SL/TP settings parsing and fixed-% premium targets for long option entries (BOT.takeTrade)."""
from __future__ import annotations

from typing import Any, Dict, Tuple


def parse_sl_tp_settings(fd: Dict[str, Any]) -> Tuple[str, float, float, bool]:
    """
    Returns (sl_tp_mode, fixed_take_profit_percent, fixed_stop_loss_percent, trailing_take_profit).
    mode is 'dynamic_atr' or 'fixed_percent'.
    """
    if not isinstance(fd, dict):
        fd = {}
    mode = str(fd.get("sl_tp_mode", fd.get("SL_TP_MODE", "dynamic_atr"))).strip().lower()
    if mode in ("fixed", "fixed_premium", "percent", "fixed_percent"):
        mode = "fixed_percent"
    tp_pct = float(fd.get("fixed_take_profit_percent", fd.get("FIXED_TP_PERCENT", 30)) or 30)
    sl_pct = float(fd.get("fixed_stop_loss_percent", fd.get("FIXED_SL_PERCENT", 30)) or 30)
    raw_tr = fd.get("trailing_take_profit", fd.get("TRAILING_TP", True))
    if isinstance(raw_tr, str):
        trailing = raw_tr.strip().lower() in ("true", "1", "yes", "on")
    else:
        trailing = bool(raw_tr)
    return mode, max(0.01, tp_pct), max(0.01, sl_pct), trailing


def compute_fixed_percent_sl_tp(
    entry: float, tp_pct: float, sl_pct: float, is_long: bool
) -> Tuple[float, float]:
    """Long BUY option: TP above entry, SL below. Percent is of option premium."""
    if is_long:
        tp = round(entry * (1.0 + tp_pct / 100.0), 2)
        sl = round(entry * (1.0 - sl_pct / 100.0), 2)
    else:
        tp = round(entry * (1.0 - tp_pct / 100.0), 2)
        sl = round(entry * (1.0 + sl_pct / 100.0), 2)
    sl = max(0.01, sl)
    return tp, sl
