"""
Data models for the trading engine.
Refactored from common.py -- now JSON-serializable for IPC.
"""

import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any


@dataclass
class OptionOrder:
    id: int = 0
    con_id: int = 0
    symbol: str = ""
    expiration: str = ""
    strike: float = 0.0
    right: str = ""  # "C" or "P"
    order_type: str = ""
    order_side: str = ""  # "BUY" or "SELL"
    order_qty: int = 0
    order_price: float = 0.0
    order_status: str = ""
    executed_qty: int = 0
    average_price: float = 0.0
    profit_price: float = 0.0
    stoploss_price: float = 0.0
    profit_trigger: bool = False
    current_profit_price: float = 0.0
    profit_increment: float = 0.0
    exit_placed: bool = False
    exit_order: bool = False
    active: bool = False
    ref_order_id: Optional[int] = None

    @property
    def option_symbol(self) -> str:
        return f"{self.symbol}{self.expiration}{self.right}{self.strike}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Tick:
    symbol: str = ""
    ask: float = -1
    bid: float = -1
    close: float = -1
    last: float = -1
    delta: float = -1
    volume: int = -1
    open_interest_call: float = -1
    open_interest_put: float = -1
    locked: bool = False
    last_trade_time: Optional[str] = None
    busy: bool = False
    option_symbol: str = ""
    active_order: Optional[OptionOrder] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.active_order:
            d["active_order"] = self.active_order.to_dict()
        return d


@dataclass
class Position:
    account: str = ""
    symbol: str = ""
    position: int = 0
    strike: float = 0.0
    right: str = ""
    expiry: str = ""
    avg_price: float = 0.0
    current_price: float = 0.0
    pnl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PNL:
    account: str = ""
    daily_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _get_market_start(data: Dict) -> str:
    """Read market start from config: market_hours.start > scriptStartTime > default 0935."""
    mh = data.get("market_hours") or {}
    return (
        mh.get("start")
        or data.get("script_start_time")
        or data.get("scriptStartTime", "0935")
    )


def _get_market_end(data: Dict) -> str:
    """Read market end from config: market_hours.end > scriptEndTime > default 1545."""
    mh = data.get("market_hours") or {}
    return (
        mh.get("end")
        or data.get("script_end_time")
        or data.get("scriptEndTime", "1545")
    )


@dataclass
class TradingConfig:
    """Mirrors the config.json structure"""
    profit_increment: float = 0.03
    expiry_to_trade: str = "next"
    spy_qqq_expiry: str = "0DTE"
    use_diff_expiry_index: str = "yes"
    ip: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 0
    account_id: str = ""
    market_start_time: str = "19:00:00"
    script_start_time: str = "0935"
    script_end_time: str = "1545"
    vwap_on_off: str = "ON"
    order_transmit: bool = True
    use_timer_in_order: str = "ON"
    order_expiry_timer: int = 15
    call_delta_check: float = 0.35
    put_delta_check: float = -0.35
    volume_check: int = 100
    atr_checks: float = 0.047
    active_volume: int = 5
    max_contract_amount: float = 350.0
    atr_value: float = 0.99
    share_volume: int = 1
    body: float = 2.0
    midpoint_offset: float = 0.01
    quantity: int = 2
    fetch_value: str = "1 D"
    candle_time: str = "5 mins"
    distance_between_trade: int = 610
    avg_volumes_candles: int = 30
    stock_data: Dict[str, Dict] = field(default_factory=dict)
    stock_list_to_trade: Dict[str, str] = field(default_factory=dict)
    per_day_trades: int = 3
    loss_amount_day: float = 200.0
    profit_amount_day: float = 200.0
    emergency_close_buffer_seconds: int = 5
    adx_on_off: str = "ON"
    adx_threshold: float = 25.0
    rsi_divergence_on_off: str = "ON"
    volume_divergence_on_off: str = "ON"
    liquidity_swap_on_off: str = "ON"
    liquidity_check_on_off: str = "ON"
    liquidity_min_volume: int = 20
    liquidity_max_spread_pct: float = 15.0

    @classmethod
    def from_dict(cls, data: Dict) -> "TradingConfig":
        """Create from the config JSON received via IPC"""
        return cls(
            profit_increment=data.get("profit_increment", 0.03),
            expiry_to_trade=data.get("expiry_to_trade", data.get("expiryToTrade", "next")),
            spy_qqq_expiry=data.get("spy_qqq_expiry", data.get("SPY_QQQ_EXPIRY", "0DTE")),
            use_diff_expiry_index=data.get("use_diff_expiry_index", data.get("USE_DIFF_EXPIRY_INDEX", "yes")),
            ip=data.get("ip", data.get("IP", "127.0.0.1")),
            port=data.get("port", data.get("PORT", 7497)),
            client_id=data.get("client_id", data.get("CLIENTID", 0)),
            account_id=data.get("account_id", data.get("ACCOUNT_ID", "")),
            market_start_time=data.get("market_start_time", data.get("marketStartTime", "09:30:00")),
            script_start_time=_get_market_start(data),
            script_end_time=_get_market_end(data),
            vwap_on_off=data.get("vwap_on_off", data.get("VWAP_ON_OFF", "ON")),
            order_transmit=data.get("order_transmit", data.get("ORDER_TRANSMIT", True)),
            use_timer_in_order=data.get("use_timer_in_order", data.get("USE_TIMER_IN_ORDER", "ON")),
            order_expiry_timer=data.get("order_expiry_timer", data.get("ORDER_EXPIRY_TIMER", 15)),
            call_delta_check=data.get("call_delta_check", data.get("CALL_DELTA_CHECK", 0.35)),
            put_delta_check=data.get("put_delta_check", data.get("PUT_DELTA_CHECK", -0.35)),
            volume_check=data.get("volume_check", data.get("VOLUME_CHECK", 100)),
            atr_checks=data.get("atr_checks", data.get("ATR_CHECKS", 0.047)),
            active_volume=data.get("active_volume", data.get("ACTIVE_VOLUME", 5)),
            max_contract_amount=data.get("max_contract_amount", data.get("MAX_CONTRACT_AMOUNT", 350)),
            atr_value=data.get("atr_value", data.get("ATR_VALUE", 0.99)),
            share_volume=data.get("share_volume", data.get("SHARE_VOLUME", 1)),
            body=data.get("body", data.get("BODY", 2.0)),
            midpoint_offset=data.get("midpoint_offset", data.get("MIDPOINT_OFFSET", 0.01)),
            quantity=data.get("quantity", data.get("QUANTITY", 2)),
            fetch_value=data.get("fetch_value", data.get("fetchValue", "1 D")),
            candle_time=data.get("candle_time", data.get("candleTime", "5 mins")),
            distance_between_trade=data.get("distance_between_trade", 610),
            avg_volumes_candles=data.get("avg_volumes_candles", data.get("AVG_VOLUMNS_CANDLES", 30)),
            stock_data=data.get("stock_data", data.get("stockData", {})),
            stock_list_to_trade=data.get("stock_list_to_trade", data.get("stockListToTrade", {})),
            per_day_trades=data.get("per_day_trades", data.get("perDayTrades", 3)),
            loss_amount_day=data.get("loss_amount_day", 200),
            profit_amount_day=data.get("profit_amount_day", 200),
            emergency_close_buffer_seconds=data.get("emergency_close_buffer_seconds", 5),
            adx_on_off=data.get("adx_on_off", data.get("ADX_ON_OFF", "ON")),
            adx_threshold=float(data.get("adx_threshold", data.get("ADX_THRESHOLD", 25))),
            rsi_divergence_on_off=data.get("rsi_divergence_on_off", data.get("RSI_DIVERGENCE_ON_OFF", "ON")),
            volume_divergence_on_off=data.get("volume_divergence_on_off", data.get("VOLUME_DIVERGENCE_ON_OFF", "ON")),
            liquidity_swap_on_off=data.get("liquidity_swap_on_off", data.get("LIQUIDITY_SWAP_ON_OFF", "ON")),
            liquidity_check_on_off=data.get("liquidity_check_on_off", data.get("LIQUIDITY_CHECK_ON_OFF", "ON")),
            liquidity_min_volume=int(data.get("liquidity_min_volume", data.get("LIQUIDITY_MIN_VOLUME", 20))),
            liquidity_max_spread_pct=float(data.get("liquidity_max_spread_pct", data.get("LIQUIDITY_MAX_SPREAD_PCT", 15))),
        )

    def to_bot_config_dict(self) -> Dict[str, Any]:
        """Return a dict with BOT.py key names (IP, PORT, stockListToTrade, etc.) for writing config.json.
        Used by the sidecar so BOT.py can find config at import time when running frozen (e.g. on Windows)."""
        stock_data_map = {k: {"amount": v.get("amount", 350)} for k, v in self.stock_data.items()}
        if not stock_data_map and self.stock_list_to_trade:
            stock_data_map = {k: {"amount": self.max_contract_amount} for k in self.stock_list_to_trade}
        return {
            "profit_increment": self.profit_increment,
            "expiryToTrade": self.expiry_to_trade,
            "SPY_QQQ_EXPIRY": self.spy_qqq_expiry,
            "USE_DIFF_EXPIRY_INDEX": self.use_diff_expiry_index,
            "IP": self.ip,
            "PORT": self.port,
            "CLIENTID": self.client_id,
            "ACCOUNT_ID": self.account_id,
            "marketStartTime": self.market_start_time,
            "scriptStartTime": self.script_start_time,
            "scriptEndTime": self.script_end_time,
            "market_hours": {"start": self.script_start_time, "end": self.script_end_time},
            "VWAP_ON_OFF": self.vwap_on_off,
            "ORDER_TRANSMIT": self.order_transmit,
            "USE_TIMER_IN_ORDER": self.use_timer_in_order,
            "ORDER_EXPIRY_TIMER": self.order_expiry_timer,
            "CALL_DELTA_CHECK": self.call_delta_check,
            "PUT_DELTA_CHECK": self.put_delta_check,
            "VOLUME_CHECK": self.volume_check,
            "ATR_CHECKS": self.atr_checks,
            "ACTIVE_VOLUME": self.active_volume,
            "MAX_CONTRACT_AMOUNT": self.max_contract_amount,
            "ATR_VALUE": self.atr_value,
            "SHARE_VOLUME": self.share_volume,
            "BODY": self.body,
            "MIDPOINT_OFFSET": self.midpoint_offset,
            "QUANTITY": self.quantity,
            "fetchValue": self.fetch_value,
            "candleTime": self.candle_time,
            "distance_between_trade": self.distance_between_trade,
            "AVG_VOLUMNS_CANDLES": self.avg_volumes_candles,
            "stockData": stock_data_map,
            "stockListToTrade": dict(self.stock_list_to_trade),
            "perDayTrades": self.per_day_trades,
            "loss_amount_day": self.loss_amount_day,
            "profit_amount_day": self.profit_amount_day,
            "emergency_close_buffer_seconds": self.emergency_close_buffer_seconds,
            "ADX_ON_OFF": self.adx_on_off,
            "ADX_THRESHOLD": self.adx_threshold,
            "RSI_DIVERGENCE_ON_OFF": self.rsi_divergence_on_off,
            "VOLUME_DIVERGENCE_ON_OFF": self.volume_divergence_on_off,
            "LIQUIDITY_SWAP_ON_OFF": self.liquidity_swap_on_off,
            "LIQUIDITY_CHECK_ON_OFF": self.liquidity_check_on_off,
            "LIQUIDITY_MIN_VOLUME": self.liquidity_min_volume,
            "LIQUIDITY_MAX_SPREAD_PCT": self.liquidity_max_spread_pct,
        }
