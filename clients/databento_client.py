"""
DataBento client for real-time market data streaming
Handles tick data streaming and candle aggregation for MNQ and NQ futures
"""

import time
from datetime import datetime
from threading import Thread
import uuid

import databento as db
import pandas as pd

from utils.logger import trading_logger
from utils.database_manager import DatabaseManager


class DataBentoClient:
    def __init__(self, api_key, symbols, timezone):
        self.api_key = api_key
        self.symbols = symbols
        self.timezone = timezone
        self.dataframes = {}
        self.client = db.Live(key=self.api_key)
        self.db_manager = DatabaseManager()
        
        # Per-symbol tracking
        self.prev_minute = {}
        self.symbols_id_mapper = {}
        self.prev_fmt_date = {s: None for s in self.symbols}
        self.symbol_ohlcv = {}
        
        # Callbacks
        self.data_callback = None
        self.error_callback = None
        
        # Status
        self.is_streaming = False
        self.stream_thread = None
        
        trading_logger.info(f"DataBento client initialized for symbols: {symbols}")

    def set_ohlcv(self, symbol, price):
        """Set OHLCV data for a specific symbol"""
        if symbol not in self.symbol_ohlcv:
            self.symbol_ohlcv[symbol] = {'high': 0, 'low': 0, 'open': 0, 'close': 0, 'volume': 0}
        
        ohlc = self.symbol_ohlcv[symbol]
        if not ohlc['open']:
            ohlc['open'] = price
        if not ohlc['high'] or price > ohlc['high']:
            ohlc['high'] = price
        if not ohlc['low'] or price < ohlc['low']:
            ohlc['low'] = price
        ohlc['close'] = price
        ohlc['volume'] += 1  # Increment tick count as volume proxy
        
        return {
            'open': ohlc['open'],
            'high': ohlc['high'], 
            'low': ohlc['low'],
            'close': ohlc['close'],
            'volume': ohlc['volume']
        }

    def reset_ohlcv(self, symbol):
        """Reset OHLCV data for a specific symbol"""
        if symbol not in self.symbol_ohlcv:
            self.symbol_ohlcv[symbol] = {}
        self.symbol_ohlcv[symbol] = {'high': 0, 'low': 0, 'open': 0, 'close': 0, 'volume': 0}

    def save_candle_to_db(self, symbol, timestamp, data):
        """Save candle data to database"""
        try:
            self.db_manager.save_candle_data(
                symbol=symbol,
                timestamp=timestamp,
                open_price=float(data['open']),
                high_price=float(data['high']),
                low_price=float(data['low']),
                close_price=float(data['close']),
                volume=int(data['volume'])
            )
            trading_logger.debug(f'Saved candle: {symbol} at {timestamp} OHLCV({data["open"]:.2f}, {data["high"]:.2f}, {data["low"]:.2f}, {data["close"]:.2f}, {data["volume"]})')
        except Exception as e:
            trading_logger.error(f'Error saving candle to DB for {symbol}: {e}')

    def user_callback(self, record: db.DBNRecord) -> None:
        """Handle incoming market data records"""
        try:
            if hasattr(record, 'price') and hasattr(record, 'instrument_id'):
                inst_id = str(record.instrument_id)
                symbol = self.symbols_id_mapper.get(inst_id)
                
                if symbol:
                    est_dt = datetime.fromtimestamp(record.ts_event / 1000000000).astimezone(tz=self.timezone).replace(second=0, microsecond=0)
                    price = record.price / 1000000000
                    
                    # Initialize dataframe if not exists
                    if symbol not in self.dataframes:
                        self.dataframes[symbol] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                    
                    # Check if we need to start a new candle
                    if symbol not in self.prev_minute:
                        self.prev_minute[symbol] = est_dt.minute
                        
                    if est_dt.minute != self.prev_minute[symbol]:
                        # Save previous minute's candle to database
                        if symbol in self.symbol_ohlcv and self.symbol_ohlcv[symbol].get('open'):
                            prev_timestamp = est_dt.replace(minute=self.prev_minute[symbol])
                            prev_data = self.symbol_ohlcv[symbol].copy()
                            self.save_candle_to_db(symbol, prev_timestamp, prev_data)
                        
                        self.prev_minute[symbol] = est_dt.minute
                        self.reset_ohlcv(symbol)

                    # Update current candle
                    data = self.set_ohlcv(symbol, price)
                    self.dataframes[symbol].loc[est_dt] = data
                    
                    # Save current candle (update)
                    self.save_candle_to_db(symbol, est_dt, data)
                    
                    # Trigger callback if set
                    if self.data_callback:
                        self.data_callback(symbol, est_dt, data)

            elif hasattr(record, 'stype_out_symbol'):
                symbol = record.stype_out_symbol
                if symbol in self.symbols:
                    self.symbols_id_mapper[str(record.instrument_id)] = symbol
                    trading_logger.info(f'{symbol} mapped with instrument id: {record.instrument_id}')
                else:
                    trading_logger.warning(f'{symbol} not found in configured symbols: {self.symbols}')
                    
        except Exception as e:
            trading_logger.error(f"Error in user_callback: {e}")

    def error_handler(self, exception: Exception) -> None:
        """Handle streaming exceptions"""
        trading_logger.error(f"DataBento streaming error: {exception}")
        if self.error_callback:
            self.error_callback(exception)
        time.sleep(5)

    def subscribe(self):
        """Subscribe to market data streams"""
        try:
            self.client.subscribe(
                dataset="GLBX.MDP3",
                schema="trades",
                stype_in="parent",
                symbols=['NQ.FUT', 'MNQ.FUT']
            )
            trading_logger.info(f'Live data subscribed for symbols: {self.symbols}')
            return True
        except Exception as e:
            trading_logger.error(f"Failed to subscribe to DataBento: {e}")
            return False

    def start_streaming(self):
        """Start the data streaming process"""
        try:
            # Add callbacks to client
            self.client.add_callback(
                record_callback=self.user_callback,
                exception_callback=self.error_handler
            )

            # Create and start streaming thread
            self.stream_thread = Thread(target=self.client.start, daemon=True)
            self.stream_thread.start()
            self.is_streaming = True
            
            trading_logger.info("DataBento streaming started successfully")
            return True
            
        except Exception as e:
            trading_logger.error(f"Failed to start DataBento streaming: {e}")
            return False

    def stop_streaming(self):
        """Stop the data streaming process"""
        try:
            if self.client:
                self.client.stop()
            self.is_streaming = False
            trading_logger.info("DataBento streaming stopped")
            return True
        except Exception as e:
            trading_logger.error(f"Error stopping DataBento streaming: {e}")
            return False

    def get_latest_data(self, symbol, limit=100):
        """Get latest candle data for a symbol"""
        if symbol in self.dataframes:
            return self.dataframes[symbol].tail(limit)
        return pd.DataFrame()

    def get_database_stats(self):
        """Get database statistics for monitored symbols"""
        stats = {}
        for symbol in self.symbols:
            try:
                candles = self.db_manager.get_latest_candles(symbol, limit=1)
                stats[symbol] = {
                    'has_data': len(candles) > 0,
                    'latest_candle': candles[0]['timestamp'] if candles else None,
                    'latest_close': float(candles[0]['close_price']) if candles else None,
                    'candle_count': len(self.dataframes.get(symbol, []))
                }
            except Exception as e:
                stats[symbol] = {'error': str(e)}
        return stats

    def set_data_callback(self, callback):
        """Set callback function for new data"""
        self.data_callback = callback

    def set_error_callback(self, callback):
        """Set callback function for errors"""
        self.error_callback = callback
