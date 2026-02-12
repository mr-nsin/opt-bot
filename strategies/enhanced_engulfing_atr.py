"""
Enhanced Engulfing ATR Trading Strategy
Implements advanced engulfing pattern detection with ATR-based position sizing,
volume confirmation, and dynamic stop-loss management
"""

import uuid
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils.logger import trading_logger
from utils.database_manager import DatabaseManager


class EngulfingATRStrategy:
    def __init__(self, config: Dict):
        self.config = config
        self.db_manager = DatabaseManager()
        
        # Strategy parameters from config
        strategy_config = config.get('strategy', {})
        self.atr_period = strategy_config.get('atr_period', 14)
        self.atr_lookback = strategy_config.get('atr_lookback', 100)
        self.ema_length = strategy_config.get('ema_length', 9)
        self.sl_multiplier = strategy_config.get('sl_multiplier', 1.9)
        self.tp_multiplier = strategy_config.get('tp_multiplier', 1.0)
        self.sl_move_profit = strategy_config.get('sl_move_profit', 0.8)
        self.sl_move_to = strategy_config.get('sl_move_to', 0.5)
        self.high_atr_threshold = strategy_config.get('high_atr_threshold', 26)
        
        # Volume confirmation parameters
        volume_config = strategy_config.get('volume_confirmation', {})
        self.buy_volume_mult = volume_config.get('buy_volume_mult', 0.65)
        self.sell_volume_mult = volume_config.get('sell_volume_mult', 0.85)
        
        # Position management
        self.positions = []
        self.max_positions = config.get('trading', {}).get('max_positions', 2)
        self.current_atr = None
        self.current_sl_mult = self.sl_multiplier
        self.current_tp_mult = self.tp_multiplier
        
        # Signal state
        self.last_signal = None
        self.last_signal_time = None
        
        trading_logger.info(f"EngulfingATR strategy initialized with ATR period: {self.atr_period}")

    def calculate_atr(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate Average True Range with dynamic parameter adjustment"""
        if len(df) < self.atr_period + 10:
            return None
        
        # Use specified lookback period for ATR calculation
        df_atr = df.tail(self.atr_lookback).copy()
        
        # Calculate True Range
        df_atr['prev_close'] = df_atr['close'].shift(1)
        df_atr['tr1'] = df_atr['high'] - df_atr['low']
        df_atr['tr2'] = abs(df_atr['high'] - df_atr['prev_close'])
        df_atr['tr3'] = abs(df_atr['low'] - df_atr['prev_close'])
        df_atr['tr'] = df_atr[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Calculate ATR
        df_atr['atr'] = df_atr['tr'].rolling(window=self.atr_period).mean()
        
        current_atr = df_atr['atr'].iloc[-1]
        self.current_atr = current_atr
        
        # Adjust parameters based on ATR level (high volatility adjustment)
        if current_atr > self.high_atr_threshold:
            self.current_tp_mult = 0.9  # Tighter take profit in high volatility
            self.current_sl_mult = 1.8  # Tighter stop loss in high volatility
        else:
            self.current_tp_mult = self.tp_multiplier
            self.current_sl_mult = self.sl_multiplier
            
        trading_logger.debug(f"ATR: {current_atr:.2f}, TP mult: {self.current_tp_mult}, SL mult: {self.current_sl_mult}")
        return current_atr

    def detect_engulfing_signal(self, df: pd.DataFrame) -> Optional[str]:
        """
        Detect engulfing signals with volume confirmation
        Returns 'BUY', 'SELL', or None
        """
        if len(df) < 7:
            return None
            
        # Get last 7 candles for pattern analysis
        candles = df.iloc[-7:].copy()
        opens = candles['open'].tolist()
        highs = candles['high'].tolist()
        lows = candles['low'].tolist()
        closes = candles['close'].tolist()
        volumes = candles['volume'].tolist()

        # Unpack OHLCV data (c0 is oldest, c6 is most recent)
        (c0o, c1o, c2o, c3o, c4o, c5o, c6o) = opens
        (c0h, c1h, c2h, c3h, c4h, c5h, c6h) = highs
        (c0l, c1l, c2l, c3l, c4l, c5l, c6l) = lows
        (c0c, c1c, c2c, c3c, c4c, c5c, c6c) = closes
        (c0v, c1v, c2v, c3v, c4v, c5v, c6v) = volumes

        # Bullish engulfing pattern with volume confirmation
        bullish_pattern = (
            c6c >= c5c and  # Current close >= previous close
            (c5c >= c4o or c5c >= c4h or c5c >= c4c) and  # Previous engulfs earlier candle
            c4c <= c3c and  # Earlier bearish candle
            c6v >= c5v * self.buy_volume_mult and  # Volume confirmation
            c5v >= c4v * self.buy_volume_mult
        )
        
        if bullish_pattern:
            return "BUY"

        # Bearish engulfing pattern with volume confirmation  
        bearish_pattern = (
            c6c <= c4o and  # Current close below earlier open
            c6c <= c5o and  # Current close below previous open
            c5h >= c4h and  # Previous high >= earlier high
            c6c <= c5l and  # Current close <= previous low
            c6v >= c5v * self.sell_volume_mult and  # Volume confirmation
            c6v >= c4v * (self.sell_volume_mult - 0.05)  # Slightly relaxed for earlier candle
        )
        
        if bearish_pattern:
            return "SELL"
            
        return None

    def check_ema_filter(self, df: pd.DataFrame, signal: str) -> bool:
        """Apply EMA filter to confirm trend direction"""
        if len(df) < self.ema_length + 1:
            return False
            
        # Calculate EMA
        df_copy = df.copy()
        df_copy['ema'] = ta.ema(close=df_copy['close'], length=self.ema_length)
        
        # Get previous candle's EMA and close
        prev_candle_ema = df_copy['ema'].iloc[-2]
        prev_candle_close = df_copy['close'].iloc[-2]
        
        # Apply trend filter
        if signal == "BUY":
            return prev_candle_close > prev_candle_ema  # Uptrend required for buy
        elif signal == "SELL":
            return prev_candle_close < prev_candle_ema  # Downtrend required for sell
            
        return False

    def calculate_position_size(self, account_balance: float, risk_percent: float, 
                              entry_price: float, stop_loss: float) -> int:
        """Calculate position size based on risk management"""
        if not self.current_atr or account_balance <= 0:
            return 1  # Default size
            
        # Calculate risk per trade in dollars
        risk_amount = account_balance * (risk_percent / 100)
        
        # Calculate risk per share/contract
        risk_per_contract = abs(entry_price - stop_loss)
        
        # Calculate position size
        if risk_per_contract > 0:
            position_size = int(risk_amount / risk_per_contract)
            return max(1, min(position_size, 5))  # Min 1, max 5 contracts
        
        return 1

    def calculate_stop_loss_take_profit(self, entry_price: float, signal: str) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels based on ATR"""
        if not self.current_atr:
            # Fallback values if ATR not available
            if signal == "BUY":
                stop_loss = entry_price - 20  # 20 ticks default
                take_profit = entry_price + 15  # 15 ticks default
            else:
                stop_loss = entry_price + 20
                take_profit = entry_price - 15
            return stop_loss, take_profit
        
        # ATR-based calculation
        atr_value = self.current_atr
        
        if signal == "BUY":
            stop_loss = entry_price - (atr_value * self.current_sl_mult)
            take_profit = entry_price + (atr_value * self.current_tp_mult)
        else:  # SELL
            stop_loss = entry_price + (atr_value * self.current_sl_mult)
            take_profit = entry_price - (atr_value * self.current_tp_mult)
            
        return stop_loss, take_profit

    def should_move_stop_loss(self, position: Dict, current_price: float) -> Optional[float]:
        """Check if stop loss should be moved based on profit level"""
        entry_price = position['entry_price']
        side = position['side']
        stop_loss = position['stop_loss']
        take_profit = position['take_profit']
        
        # Calculate current P&L percentage
        if side == "BUY":
            pnl_pct = (current_price - entry_price) / entry_price
            target_profit = take_profit - entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price
            target_profit = entry_price - take_profit
            
        # Check if we've achieved the profit threshold for SL movement
        if pnl_pct >= self.sl_move_profit:
            # Move stop loss to the specified profit level
            if side == "BUY":
                new_stop_loss = entry_price + (target_profit * self.sl_move_to)
                return max(new_stop_loss, stop_loss)  # Only move up for long positions
            else:
                new_stop_loss = entry_price - (target_profit * self.sl_move_to)
                return min(new_stop_loss, stop_loss)  # Only move down for short positions
                
        return None

    def analyze_market_data(self, df: pd.DataFrame) -> Dict:
        """
        Main analysis function that processes market data and generates signals
        """
        result = {
            'signal': None,
            'signal_strength': 0.0,
            'atr': None,
            'ema_trend': None,
            'volume_confirmation': False,
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'position_size': 1
        }
        
        if len(df) < max(self.atr_period, self.ema_length) + 10:
            return result
        
        # Calculate ATR
        atr = self.calculate_atr(df)
        result['atr'] = atr
        
        # Detect engulfing signal
        signal = self.detect_engulfing_signal(df)
        if not signal:
            return result
            
        # Apply EMA filter
        ema_confirmed = self.check_ema_filter(df, signal)
        if not ema_confirmed:
            return result
            
        # Calculate signal strength (simplified)
        volume_ratio = df['volume'].iloc[-1] / df['volume'].iloc[-7:-1].mean() if len(df) > 7 else 1.0
        signal_strength = min(volume_ratio / 2.0, 1.0)  # Normalize to 0-1
        
        # Use current price as entry price
        entry_price = df['close'].iloc[-1]
        
        # Calculate stop loss and take profit
        stop_loss, take_profit = self.calculate_stop_loss_take_profit(entry_price, signal)
        
        result.update({
            'signal': signal,
            'signal_strength': signal_strength,
            'ema_trend': 'UP' if signal == 'BUY' else 'DOWN',
            'volume_confirmation': True,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
        })
        
        # Store signal info
        self.last_signal = signal
        self.last_signal_time = datetime.now()
        
        trading_logger.info(f"Signal detected: {signal} at {entry_price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
        
        return result

    def create_trade_order(self, analysis_result: Dict, symbol: str, account_balance: float = 10000) -> Dict:
        """Create a trade order based on analysis result"""
        if not analysis_result['signal']:
            return {}
            
        # Calculate position size
        position_size = self.calculate_position_size(
            account_balance, 
            2.0,  # 2% risk per trade
            analysis_result['entry_price'],
            analysis_result['stop_loss']
        )
        
        trade_order = {
            'trade_id': str(uuid.uuid4()),
            'symbol': symbol,
            'strategy': 'engulfing_atr',
            'side': analysis_result['signal'],
            'entry_price': analysis_result['entry_price'],
            'stop_loss': analysis_result['stop_loss'],
            'take_profit': analysis_result['take_profit'],
            'quantity': position_size,
            'atr_value': analysis_result['atr'],
            'signal_type': analysis_result['signal'],
            'signal_strength': analysis_result['signal_strength'],
            'timestamp': datetime.now()
        }
        
        return trade_order

    def get_strategy_status(self) -> Dict:
        """Get current strategy status and parameters"""
        return {
            'name': 'engulfing_atr',
            'atr_period': self.atr_period,
            'ema_length': self.ema_length,
            'current_atr': self.current_atr,
            'sl_multiplier': self.current_sl_mult,
            'tp_multiplier': self.current_tp_mult,
            'last_signal': self.last_signal,
            'last_signal_time': self.last_signal_time,
            'positions_count': len(self.positions),
            'max_positions': self.max_positions
        }
