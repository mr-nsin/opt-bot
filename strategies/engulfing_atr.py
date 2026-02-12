import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from utils.logger import trading_logger

class EngulfingATRStrategy:
    def __init__(self, config: Dict):
        self.config = config
        self.strategy_config = config.get('strategy', {})
        
        # Strategy parameters
        self.atr_period = self.strategy_config.get('atr_period', 14)
        self.ema_length = self.strategy_config.get('ema_length', 9)
        self.sl_multiplier = self.strategy_config.get('sl_multiplier', 1.9)
        self.tp_multiplier = self.strategy_config.get('tp_multiplier', 1.0)
        self.sl_move_profit = self.strategy_config.get('sl_move_profit', 0.8)
        self.sl_move_to = self.strategy_config.get('sl_move_to', 0.5)
        self.high_atr_threshold = self.strategy_config.get('high_atr_threshold', 26)
        
        # Volume confirmation parameters
        volume_config = self.strategy_config.get('volume_confirmation', {})
        self.buy_volume_mult = volume_config.get('buy_volume_mult', 0.65)
        self.sell_volume_mult = volume_config.get('sell_volume_mult', 0.85)
        
        # Trading hours
        trading_hours = config.get('trading', {}).get('trading_hours', {})
        self.trading_start = self._parse_time(trading_hours.get('start', '06:00'))
        self.trading_end = self._parse_time(trading_hours.get('end', '17:00'))
        
        trading_logger.log_system_event(f"EngulfingATRStrategy initialized with ATR period: {self.atr_period}")
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string to time object"""
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except:
            return time(6, 0)  # Default to 6:00 AM
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        current_time = datetime.now().time()
        return self.trading_start <= current_time <= self.trading_end
    
    def calculate_atr(self, df: pd.DataFrame, period: int = None) -> float:
        """Calculate ATR (Average True Range)"""
        if period is None:
            period = self.atr_period
        
        if len(df) < period + 1:
            return 0.0
        
        # Calculate True Range
        df = df.copy()
        df['prev_close'] = df['close'].shift(1)
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['prev_close'])
        df['low_close'] = abs(df['low'] - df['prev_close'])
        df['true_range'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        
        # Calculate ATR
        atr = df['true_range'].rolling(window=period).mean().iloc[-1]
        return atr if not pd.isna(atr) else 0.0
    
    def calculate_ema(self, df: pd.DataFrame, period: int = None) -> float:
        """Calculate EMA (Exponential Moving Average)"""
        if period is None:
            period = self.ema_length
        
        if len(df) < period:
            return df['close'].iloc[-1]
        
        ema = df['close'].ewm(span=period).mean().iloc[-1]
        return ema if not pd.isna(ema) else df['close'].iloc[-1]
    
    def detect_engulfing_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect engulfing candlestick pattern with enhanced logic"""
        if len(df) < 7:
            return None
        
        # Get last 7 candles for analysis
        recent_candles = df.iloc[-7:].copy()
        
        # Extract OHLCV data
        opens = recent_candles['open'].values
        highs = recent_candles['high'].values
        lows = recent_candles['low'].values
        closes = recent_candles['close'].values
        volumes = recent_candles['volume'].values
        
        # Calculate ATR and EMA
        atr = self.calculate_atr(df)
        ema = self.calculate_ema(df)
        current_price = closes[-1]
        
        # Enhanced signal detection
        signal = self._analyze_engulfing_pattern(opens, highs, lows, closes, volumes, atr, ema, current_price)
        
        if signal:
            trading_logger.log_signal(
                signal['type'], 
                'MNQ', 
                current_price, 
                signal['strength'], 
                False
            )
        
        return signal
    
    def _analyze_engulfing_pattern(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, 
                                 closes: np.ndarray, volumes: np.ndarray, atr: float, 
                                 ema: float, current_price: float) -> Optional[Dict]:
        """Analyze engulfing pattern with multiple confirmations"""
        
        # Basic engulfing pattern detection
        bullish_engulfing = self._check_bullish_engulfing(opens, highs, lows, closes, volumes)
        bearish_engulfing = self._check_bearish_engulfing(opens, highs, lows, closes, volumes)
        
        if not bullish_engulfing and not bearish_engulfing:
            return None
        
        # Calculate signal strength
        signal_strength = 0.0
        signal_type = None
        
        if bullish_engulfing:
            signal_type = "BUY"
            signal_strength = self._calculate_bullish_strength(opens, highs, lows, closes, volumes, ema, current_price)
        elif bearish_engulfing:
            signal_type = "SELL"
            signal_strength = self._calculate_bearish_strength(opens, highs, lows, closes, volumes, ema, current_price)
        
        # Filter weak signals
        if signal_strength < 0.6:  # Minimum strength threshold
            return None
        
        # Calculate dynamic stop loss and take profit
        sl_mult = 1.8 if atr > self.high_atr_threshold else self.sl_multiplier
        tp_mult = 0.9 if atr > self.high_atr_threshold else self.tp_multiplier
        
        if signal_type == "BUY":
            stop_loss = current_price - (atr * sl_mult)
            take_profit = current_price + (atr * tp_mult)
        else:
            stop_loss = current_price + (atr * sl_mult)
            take_profit = current_price - (atr * tp_mult)
        
        return {
            'type': signal_type,
            'strength': signal_strength,
            'price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'atr': atr,
            'ema': ema,
            'timestamp': datetime.now()
        }
    
    def _check_bullish_engulfing(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, 
                               closes: np.ndarray, volumes: np.ndarray) -> bool:
        """Check for bullish engulfing pattern"""
        # Current candle engulfs previous candle
        current_engulfs = (closes[-1] >= closes[-2] and 
                          (closes[-2] >= opens[-3] or closes[-2] >= highs[-3]) and 
                          closes[-3] <= closes[-4])
        
        # Volume confirmation
        volume_confirm = (volumes[-1] >= volumes[-2] * self.buy_volume_mult and 
                         volumes[-2] >= volumes[-3] * self.buy_volume_mult)
        
        return current_engulfs and volume_confirm
    
    def _check_bearish_engulfing(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, 
                               closes: np.ndarray, volumes: np.ndarray) -> bool:
        """Check for bearish engulfing pattern"""
        # Current candle engulfs previous candle
        current_engulfs = (closes[-1] <= opens[-3] and 
                          closes[-1] <= opens[-2] and 
                          highs[-2] >= highs[-3] and 
                          closes[-1] <= lows[-2])
        
        # Volume confirmation
        volume_confirm = (volumes[-1] >= volumes[-2] * self.sell_volume_mult and 
                         volumes[-1] >= volumes[-3] * (self.sell_volume_mult * 0.94))
        
        return current_engulfs and volume_confirm
    
    def _calculate_bullish_strength(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, 
                                  closes: np.ndarray, volumes: np.ndarray, ema: float, 
                                  current_price: float) -> float:
        """Calculate bullish signal strength"""
        strength = 0.5  # Base strength
        
        # EMA trend confirmation
        if current_price > ema:
            strength += 0.2
        
        # Volume strength
        volume_ratio = volumes[-1] / volumes[-2] if volumes[-2] > 0 else 1
        if volume_ratio > 1.5:
            strength += 0.15
        elif volume_ratio > 1.2:
            strength += 0.1
        
        # Candle body size
        body_size = abs(closes[-1] - opens[-1])
        prev_body_size = abs(closes[-2] - opens[-2])
        if body_size > prev_body_size * 1.2:
            strength += 0.1
        
        # Price momentum
        if closes[-1] > closes[-2] and closes[-2] > closes[-3]:
            strength += 0.05
        
        return min(strength, 1.0)
    
    def _calculate_bearish_strength(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, 
                                  closes: np.ndarray, volumes: np.ndarray, ema: float, 
                                  current_price: float) -> float:
        """Calculate bearish signal strength"""
        strength = 0.5  # Base strength
        
        # EMA trend confirmation
        if current_price < ema:
            strength += 0.2
        
        # Volume strength
        volume_ratio = volumes[-1] / volumes[-2] if volumes[-2] > 0 else 1
        if volume_ratio > 1.5:
            strength += 0.15
        elif volume_ratio > 1.2:
            strength += 0.1
        
        # Candle body size
        body_size = abs(closes[-1] - opens[-1])
        prev_body_size = abs(closes[-2] - opens[-2])
        if body_size > prev_body_size * 1.2:
            strength += 0.1
        
        # Price momentum
        if closes[-1] < closes[-2] and closes[-2] < closes[-3]:
            strength += 0.05
        
        return min(strength, 1.0)
    
    def should_move_stop_loss(self, entry_price: float, current_price: float, 
                            take_profit: float, side: str) -> Tuple[bool, float]:
        """Check if stop loss should be moved to breakeven"""
        profit_distance = abs(take_profit - entry_price)
        profit_80_level = entry_price + (self.sl_move_profit * profit_distance) if side == "BUY" else entry_price - (self.sl_move_profit * profit_distance)
        
        should_move = False
        new_sl = None
        
        if side == "BUY" and current_price >= profit_80_level:
            should_move = True
            new_sl = entry_price + (self.sl_move_to * profit_distance)
        elif side == "SELL" and current_price <= profit_80_level:
            should_move = True
            new_sl = entry_price - (self.sl_move_to * profit_distance)
        
        return should_move, new_sl
    
    def get_position_size(self, account_balance: float, risk_per_trade: float, 
                         entry_price: float, stop_loss: float) -> int:
        """Calculate position size based on risk management"""
        risk_amount = account_balance * risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            return 1
        
        position_size = int(risk_amount / price_risk)
        return max(1, position_size)  # Minimum 1 contract
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Generate trading signal from candle data
        Returns signal dict with action, price, stop_loss, take_profit, etc.
        """
        try:
            if not self.is_trading_hours():
                return {'action': 'HOLD', 'reason': 'Outside trading hours'}
            
            if len(df) < self.atr_period + 5:
                return {'action': 'HOLD', 'reason': 'Insufficient data'}
            
            # Get the engulfing pattern signal
            engulfing_signal = self.detect_engulfing_pattern(df)
            
            if not engulfing_signal:
                return {'action': 'HOLD', 'reason': 'No engulfing pattern detected'}
            
            # Calculate ATR for stop loss and take profit
            current_atr = self.calculate_atr(df)
            current_price = df.iloc[-1]['close']
            
            signal_type = engulfing_signal['type']  # 'BUY' or 'SELL'
            
            # Calculate stop loss and take profit based on ATR
            if signal_type == 'BUY':
                stop_loss = current_price - (current_atr * self.sl_multiplier)
                take_profit = current_price + (current_atr * self.tp_multiplier)
            else:  # SELL
                stop_loss = current_price + (current_atr * self.sl_multiplier)
                take_profit = current_price - (current_atr * self.tp_multiplier)
            
            return {
                'action': signal_type,
                'price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'atr': current_atr,
                'strength': engulfing_signal.get('strength', 1.0),
                'reason': f"Engulfing pattern detected with strength {engulfing_signal.get('strength', 1.0):.2f}"
            }
            
        except Exception as e:
            trading_logger.error(f"Error generating signal: {e}")
            return {'action': 'HOLD', 'reason': f'Error: {str(e)}'}
