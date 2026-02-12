"""
Enhanced DataBento Real-time Data Streaming Client
Provides OHLCV candle data from futures market data
"""

import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd

try:
    import databento as db
except ImportError:
    print("Warning: databento not installed, using mock implementation")
    db = None

try:
    from utils.logger import trading_logger
except ImportError:
    import logging
    trading_logger = logging.getLogger(__name__)


class DataBentoStreamer:
    def __init__(self, api_key: str, symbols: List[str], dataset: str = "GLBX.MDP3", schema: str = "trades"):
        """Initialize DataBento streaming client"""
        self.api_key = api_key
        self.symbols = symbols
        self.dataset = dataset
        self.schema = schema
        
        # Data storage
        self.dataframes = {}
        self.latest_prices = {}
        self.symbol_id_mapping = {}
        
        # OHLCV tracking per symbol
        self.current_candles = {}
        self.prev_minute = {}
        
        # Client
        self.client = None
        self.streaming_thread = None
        self.running = False
        
        trading_logger.info(f"DataBento client initialized for symbols: {symbols}")

    def subscribe(self):
        """Subscribe to real-time data"""
        try:
            if db is None:
                trading_logger.warning("DataBento not available, using mock data")
                self._start_mock_streaming()
                return
            
            self.client = db.Live(key=self.api_key)
            
            # Subscribe to futures data
            self.client.subscribe(
                dataset=self.dataset,
                schema=self.schema,
                stype_in="parent",
                symbols=self.symbols
            )
            
            trading_logger.info(f"Subscribed to {self.dataset} {self.schema} for {self.symbols}")
            
        except Exception as e:
            trading_logger.error(f"Failed to subscribe to DataBento: {e}")
            self._start_mock_streaming()

    def start_streaming(self):
        """Start the data streaming"""
        try:
            if self.client and db:
                # Add callbacks
                self.client.add_callback(
                    record_callback=self._on_market_data,
                    exception_callback=self._on_error
                )
                
                # Start streaming in background thread
                self.streaming_thread = threading.Thread(target=self.client.start, daemon=True)
                self.streaming_thread.start()
            else:
                self._start_mock_streaming()
                
            self.running = True
            trading_logger.info("DataBento streaming started")
            
        except Exception as e:
            trading_logger.error(f"Failed to start streaming: {e}")
            self._start_mock_streaming()

    def _start_mock_streaming(self):
        """Start mock data streaming for development"""
        def mock_stream():
            import random
            base_prices = {'MNQ.FUT': 15000, 'NQ.FUT': 15000}
            
            while self.running:
                try:
                    for symbol in self.symbols:
                        # Generate mock OHLCV data
                        base_price = base_prices.get(symbol, 15000)
                        current_time = datetime.now()
                        
                        price = base_price + random.uniform(-100, 100)
                        volume = random.randint(100, 1000)
                        
                        # Create mock candle data
                        if symbol not in self.dataframes:
                            self.dataframes[symbol] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                        
                        # Update current candle
                        minute_key = current_time.replace(second=0, microsecond=0)
                        
                        if symbol not in self.current_candles:
                            self.current_candles[symbol] = {
                                'open': price,
                                'high': price,
                                'low': price,
                                'close': price,
                                'volume': volume
                            }
                        else:
                            candle = self.current_candles[symbol]
                            candle['high'] = max(candle['high'], price)
                            candle['low'] = min(candle['low'], price)
                            candle['close'] = price
                            candle['volume'] += volume
                        
                        # Add to dataframe
                        self.dataframes[symbol].loc[minute_key] = self.current_candles[symbol]
                        
                        # Keep only last 1000 candles
                        if len(self.dataframes[symbol]) > 1000:
                            self.dataframes[symbol] = self.dataframes[symbol].tail(1000)
                        
                        self.latest_prices[symbol] = price
                
                except Exception as e:
                    trading_logger.error(f"Mock streaming error: {e}")
                
                time.sleep(1)  # Update every second
        
        self.streaming_thread = threading.Thread(target=mock_stream, daemon=True)
        self.streaming_thread.start()
        trading_logger.info("Mock data streaming started")

    def _on_market_data(self, record):
        """Handle incoming market data"""
        try:
            if hasattr(record, 'price') and hasattr(record, 'instrument_id'):
                # Map instrument ID to symbol
                inst_id = str(record.instrument_id)
                symbol = self.symbol_id_mapping.get(inst_id)
                
                if symbol:
                    price = record.price / 1_000_000_000  # Convert price
                    timestamp = datetime.fromtimestamp(record.ts_event / 1_000_000_000, tz=timezone.utc)
                    
                    self._update_candle_data(symbol, price, timestamp)
                    self.latest_prices[symbol] = price
            
            elif hasattr(record, 'stype_out_symbol'):
                # Symbol mapping record
                symbol = record.stype_out_symbol
                if symbol in self.symbols:
                    self.symbol_id_mapping[str(record.instrument_id)] = symbol
                    trading_logger.info(f"Mapped {symbol} to instrument ID {record.instrument_id}")
                    
        except Exception as e:
            trading_logger.error(f"Error processing market data: {e}")

    def _update_candle_data(self, symbol: str, price: float, timestamp: datetime):
        """Update OHLCV candle data"""
        try:
            minute_key = timestamp.replace(second=0, microsecond=0)
            
            # Initialize dataframe if needed
            if symbol not in self.dataframes:
                self.dataframes[symbol] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            # Check if we need to start a new candle
            if symbol not in self.prev_minute:
                self.prev_minute[symbol] = minute_key.minute
                self.current_candles[symbol] = {
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': 1
                }
            
            # New minute - finalize previous candle
            if minute_key.minute != self.prev_minute[symbol]:
                if symbol in self.current_candles:
                    prev_minute_key = minute_key.replace(minute=self.prev_minute[symbol])
                    self.dataframes[symbol].loc[prev_minute_key] = self.current_candles[symbol]
                
                # Start new candle
                self.current_candles[symbol] = {
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': 1
                }
                self.prev_minute[symbol] = minute_key.minute
            else:
                # Update current candle
                candle = self.current_candles[symbol]
                candle['high'] = max(candle['high'], price)
                candle['low'] = min(candle['low'], price)
                candle['close'] = price
                candle['volume'] += 1
            
            # Update current candle in dataframe
            self.dataframes[symbol].loc[minute_key] = self.current_candles[symbol]
            
            # Keep reasonable size
            if len(self.dataframes[symbol]) > 1000:
                self.dataframes[symbol] = self.dataframes[symbol].tail(1000)
                
        except Exception as e:
            trading_logger.error(f"Error updating candle data for {symbol}: {e}")

    def _on_error(self, exception: Exception):
        """Handle streaming errors"""
        trading_logger.error(f"DataBento streaming error: {exception}")
        time.sleep(5)  # Wait before retrying

    def get_latest_data(self) -> Dict[str, pd.DataFrame]:
        """Get latest market data for all symbols"""
        return self.dataframes.copy()

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        return self.latest_prices.get(symbol)

    def stop_streaming(self):
        """Stop data streaming"""
        try:
            self.running = False
            
            if self.client:
                self.client.stop()
            
            trading_logger.info("DataBento streaming stopped")
            
        except Exception as e:
            trading_logger.error(f"Error stopping DataBento streaming: {e}")

    def get_candle_history(self, symbol: str, periods: int = 100) -> pd.DataFrame:
        """Get historical candle data for a symbol"""
        if symbol in self.dataframes:
            return self.dataframes[symbol].tail(periods).copy()
        return pd.DataFrame()


# Alias for backward compatibility  
DataBentoClient = DataBentoStreamer
