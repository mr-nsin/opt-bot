"""
DataBento real-time candle streaming client
Streams live trade data and builds 1-minute OHLCV candles
"""

import time
from datetime import datetime
from threading import Thread
from typing import Dict, List, Optional, Callable

import databento as db
import pandas as pd

from utils.logger import trading_logger
from utils.database_manager import DatabaseManager


class DataBentoStreamer:
    """
    Professional DataBento streaming client for real-time candle data
    Builds 1-minute OHLCV candles from live trade ticks
    """
    
    def __init__(self, api_key: str, symbols: List[str], callback: Optional[Callable] = None):
        self.api_key = api_key
        self.symbols = symbols
        self.callback = callback
        self.dataframes = {}
        self.client = None
        self.is_streaming = False
        self.prev_minute = {}
        self.symbols_id_mapper = {}
        self.prev_fmt_date = {s: None for s in self.symbols}
        self.symbol_ohlcv = {}
        self.db_manager = DatabaseManager()
        
        trading_logger.info(f"DataBento streamer initialized for symbols: {symbols}")

    def set_ohlcv(self, symbol: str, price: float) -> Dict:
        """Set OHLCV data for a specific symbol"""
        if symbol not in self.symbol_ohlcv:
            self.symbol_ohlcv[symbol] = {'high': 0, 'low': 0, 'open': 0, 'close': 0}
        
        ohlc = self.symbol_ohlcv[symbol]
        if not ohlc['open']:
            ohlc['open'] = price
        if not ohlc['high'] or price > ohlc['high']:
            ohlc['high'] = price
        if not ohlc['low'] or price < ohlc['low']:
            ohlc['low'] = price
        ohlc['close'] = price
        
        return {
            'close': ohlc['close'], 
            'open': ohlc['open'], 
            'high': ohlc['high'], 
            'low': ohlc['low']
        }

    def reset_ohlcv(self, symbol: str):
        """Reset OHLCV data for a specific symbol"""
        if symbol not in self.symbol_ohlcv:
            self.symbol_ohlcv[symbol] = {}
        self.symbol_ohlcv[symbol] = {'high': 0, 'low': 0, 'open': 0, 'close': 0}

    def save_candle_to_db(self, symbol: str, timestamp: datetime, data: Dict):
        """Save candle data to database"""
        try:
            self.db_manager.save_candle(
                symbol=symbol,
                timestamp=timestamp,
                open_price=float(data['open']),
                high_price=float(data['high']),
                low_price=float(data['low']),
                close_price=float(data['close']),
                volume=0  # Volume not available in trades schema
            )
            trading_logger.debug(f'Saved candle: {symbol} at {timestamp} OHLC({data["open"]:.2f}, {data["high"]:.2f}, {data["low"]:.2f}, {data["close"]:.2f})')
        except Exception as e:
            trading_logger.error(f'Error saving candle to DB for {symbol}: {e}')

    def get_database_stats(self) -> Dict:
        """Get database statistics for monitored symbols"""
        stats = {}
        for symbol in self.symbols:
            try:
                candles = self.db_manager.get_recent_candles(symbol, limit=1)
                stats[symbol] = {
                    'has_data': len(candles) > 0,
                    'latest_candle': candles[0]['timestamp'] if candles else None,
                    'latest_close': float(candles[0]['close']) if candles else None
                }
            except Exception as e:
                stats[symbol] = {'error': str(e)}
        return stats

    def user_callback(self, record: db.DBNRecord) -> None:
        """Handle incoming DBN records from DataBento"""
        try:
            if hasattr(record, 'price'):
                inst_id = str(record.instrument_id)
                symbol = self.symbols_id_mapper.get(inst_id)
                
                if symbol:
                    # Convert timestamp to datetime with proper timezone
                    est_dt = datetime.fromtimestamp(record.ts_event / 1000000000).replace(second=0, microsecond=0)
                    price = record.price / 1000000000
                    
                    # Initialize dataframe if needed
                    if symbol not in self.dataframes:
                        self.dataframes[symbol] = pd.DataFrame(columns=['open', 'high', 'low', 'close'])
                    
                    # Check if we need to start a new candle
                    if symbol not in self.prev_minute:
                        self.prev_minute[symbol] = est_dt.minute
                        
                    if est_dt.minute != self.prev_minute[symbol]:
                        # Save previous minute's candle to database before starting new one
                        if symbol in self.symbol_ohlcv and self.symbol_ohlcv[symbol].get('open'):
                            prev_timestamp = est_dt.replace(minute=self.prev_minute[symbol])
                            prev_data = self.symbol_ohlcv[symbol].copy()
                            self.save_candle_to_db(symbol, prev_timestamp, prev_data)
                            
                            # Trigger callback for completed candle
                            if self.callback:
                                self.callback(symbol, prev_timestamp, prev_data)
                        
                        self.prev_minute[symbol] = est_dt.minute
                        self.reset_ohlcv(symbol)

                    # Update current candle data
                    data = self.set_ohlcv(symbol, price)
                    self.dataframes[symbol].loc[est_dt] = data
                    
                    # Also save current candle to database (update)
                    self.save_candle_to_db(symbol, est_dt, data)

            elif hasattr(record, 'stype_out_symbol'):
                symbol = record.stype_out_symbol
                if symbol in self.symbols:
                    self.symbols_id_mapper[str(record.instrument_id)] = symbol
                    trading_logger.info(f'{symbol} mapped with instrument id: {record.instrument_id}')
                else:
                    trading_logger.debug(f'{symbol} not found in monitored symbols')
                    
        except Exception as e:
            trading_logger.error(f"Error in user_callback: {e}")

    def error_handler(self, exception: Exception) -> None:
        """Handle exceptions from DataBento streaming"""
        trading_logger.error(f"DataBento streaming error: {exception}")
        time.sleep(5)

    def subscribe(self):
        """Subscribe to DataBento live data feed"""
        try:
            if not self.client:
                self.client = db.Live(key=self.api_key)
            
            self.client.subscribe(
                dataset="GLBX.MDP3",
                schema="trades",
                stype_in="parent",
                symbols=['NQ.FUT', 'MNQ.FUT']  # DataBento symbol format
            )
            trading_logger.info(f'Subscribed to live data for symbols: {self.symbols}')
            
        except Exception as e:
            trading_logger.error(f"Error subscribing to DataBento: {e}")
            raise

    def start_streaming(self):
        """Start the DataBento streaming thread"""
        try:
            if not self.client:
                raise Exception("Must call subscribe() before start_streaming()")
                
            # Add callbacks to the client
            self.client.add_callback(
                record_callback=self.user_callback,
                exception_callback=self.error_handler
            )

            # Create and start streaming thread
            streaming_thread = Thread(target=self.client.start, daemon=True)
            streaming_thread.start()
            
            self.is_streaming = True
            trading_logger.info("DataBento streaming started")
            
        except Exception as e:
            trading_logger.error(f"Error starting DataBento stream: {e}")
            raise

    def stop_streaming(self):
        """Stop the DataBento streaming"""
        try:
            if self.client and self.is_streaming:
                self.client.stop()
                self.is_streaming = False
                trading_logger.info("DataBento streaming stopped")
        except Exception as e:
            trading_logger.error(f"Error stopping DataBento stream: {e}")

    def get_latest_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get latest candle data for a symbol"""
        return self.dataframes.get(symbol)

    def get_streaming_status(self) -> Dict:
        """Get streaming status information"""
        return {
            'is_streaming': self.is_streaming,
            'symbols': self.symbols,
            'mapped_symbols': list(self.symbols_id_mapper.values()),
            'dataframes_available': list(self.dataframes.keys()),
            'has_client': self.client is not None
        }

    def get_current_prices(self) -> Dict:
        """Get current prices for all symbols"""
        prices = {}
        for symbol in self.symbols:
            if symbol in self.symbol_ohlcv and self.symbol_ohlcv[symbol].get('close'):
                prices[symbol] = self.symbol_ohlcv[symbol]['close']
        return prices
