"""
Abstract base class for trading strategies.
All strategies must implement the `check_signal` method.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.enabled = True

    @abstractmethod
    def check_signal(self, symbol: str, candle_data: Any, tick_data: Any) -> Optional[Dict]:
        """
        Check for trading signals.

        Returns:
            None if no signal, or a dict with signal details:
            {
                "signal_type": "CALL" | "PUT",
                "symbol": "SPY",
                "strike": 585.0,
                "reason": "Bullish engulfing + ATR confirmation",
                "confidence": 0.85,
            }
        """
        pass

    @abstractmethod
    def get_take_profit(self, entry_price: float, signal_type: str) -> float:
        """Calculate take-profit price based on entry."""
        pass

    @abstractmethod
    def get_stop_loss(self, entry_price: float, signal_type: str) -> float:
        """Calculate stop-loss price based on entry."""
        pass
