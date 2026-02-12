import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
import uuid

class DatabaseManager:
    def __init__(self, db_path: str = "database/trades.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_time TIMESTAMP,
                    entry_price DECIMAL(10, 4),
                    exit_time TIMESTAMP,
                    exit_price DECIMAL(10, 4),
                    quantity INTEGER NOT NULL,
                    pnl DECIMAL(10, 2),
                    status TEXT NOT NULL,
                    stop_loss DECIMAL(10, 4),
                    take_profit DECIMAL(10, 4),
                    atr_value DECIMAL(10, 4),
                    signal_strength DECIMAL(5, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Signals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    signal_strength DECIMAL(5, 2),
                    price DECIMAL(10, 4),
                    atr_value DECIMAL(10, 4),
                    volume_confirmation BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    gross_profit DECIMAL(10, 2) DEFAULT 0,
                    gross_loss DECIMAL(10, 2) DEFAULT 0,
                    net_profit DECIMAL(10, 2) DEFAULT 0,
                    win_rate DECIMAL(5, 2) DEFAULT 0,
                    avg_win DECIMAL(10, 2) DEFAULT 0,
                    avg_loss DECIMAL(10, 2) DEFAULT 0,
                    max_drawdown DECIMAL(10, 2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    status TEXT NOT NULL,
                    initial_balance DECIMAL(10, 2),
                    final_balance DECIMAL(10, 2),
                    trades_count INTEGER DEFAULT 0,
                    net_pnl DECIMAL(10, 2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Candle data table for real-time market data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS candle_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp)
                )
            ''')
            
            # Add indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_candle_symbol_timestamp 
                ON candle_data(symbol, timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_symbol_time 
                ON trades(symbol, entry_time DESC)
            ''')
            
            # Add new columns to trades table if they don't exist
            try:
                cursor.execute('ALTER TABLE trades ADD COLUMN atr_value REAL')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute('ALTER TABLE trades ADD COLUMN signal_type TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute('ALTER TABLE trades ADD COLUMN volume_ratio REAL')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_trade(self, trade_data: Dict) -> str:
        """Save a trade to the database"""
        trade_id = trade_data.get('trade_id', str(uuid.uuid4()))
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO trades (
                    trade_id, symbol, strategy, side, entry_time, entry_price,
                    exit_time, exit_price, quantity, pnl, status, stop_loss,
                    take_profit, atr_value, signal_strength
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_id,
                trade_data.get('symbol'),
                trade_data.get('strategy'),
                trade_data.get('side'),
                trade_data.get('entry_time'),
                trade_data.get('entry_price'),
                trade_data.get('exit_time'),
                trade_data.get('exit_price'),
                trade_data.get('quantity'),
                trade_data.get('pnl'),
                trade_data.get('status'),
                trade_data.get('stop_loss'),
                trade_data.get('take_profit'),
                trade_data.get('atr_value'),
                trade_data.get('signal_strength')
            ))
            conn.commit()
        
        return trade_id
    
    def save_signal(self, signal_data: Dict) -> str:
        """Save a signal to the database"""
        signal_id = signal_data.get('signal_id', str(uuid.uuid4()))
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO signals (
                    signal_id, symbol, strategy, signal_type, signal_strength,
                    price, atr_value, volume_confirmation, executed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_id,
                signal_data.get('symbol'),
                signal_data.get('strategy'),
                signal_data.get('signal_type'),
                signal_data.get('signal_strength'),
                signal_data.get('price'),
                signal_data.get('atr_value'),
                signal_data.get('volume_confirmation'),
                signal_data.get('executed', False)
            ))
            conn.commit()
        
        return signal_id
    
    def get_trades(self, limit: int = 100, status: str = None) -> List[Dict]:
        """Get trades from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_daily_performance(self, date: str = None) -> Dict:
        """Get daily performance metrics"""
        if not date:
            date = datetime.now().date()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as gross_profit,
                    SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END) as gross_loss,
                    SUM(pnl) as net_profit,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
                FROM trades 
                WHERE DATE(entry_time) = ? AND status = 'CLOSED'
            ''', (date,))
            
            result = cursor.fetchone()
            if result:
                data = dict(result)
                data['win_rate'] = (data['winning_trades'] / data['total_trades'] * 100) if data['total_trades'] > 0 else 0
                return data
            
            return {}
    
    def start_session(self, initial_balance: float) -> str:
        """Start a new trading session"""
        session_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (session_id, start_time, status, initial_balance)
                VALUES (?, ?, ?, ?)
            ''', (session_id, datetime.now(), 'ACTIVE', initial_balance))
            conn.commit()
        
        return session_id
    
    def end_session(self, session_id: str, final_balance: float, trades_count: int, net_pnl: float):
        """End a trading session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions 
                SET end_time = ?, status = ?, final_balance = ?, trades_count = ?, net_pnl = ?
                WHERE session_id = ?
            ''', (datetime.now(), 'COMPLETED', final_balance, trades_count, net_pnl, session_id))
            conn.commit()
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        return self.get_trades(status='OPEN')
    
    def close_trade(self, trade_id: str, exit_price: float, exit_time: datetime = None):
        """Close a trade"""
        if not exit_time:
            exit_time = datetime.now()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get trade details to calculate PnL
            cursor.execute('SELECT * FROM trades WHERE trade_id = ?', (trade_id,))
            trade = cursor.fetchone()
            
            if trade:
                entry_price = trade['entry_price']
                quantity = trade['quantity']
                side = trade['side']
                
                # Calculate PnL
                if side == 'BUY':
                    pnl = (exit_price - entry_price) * quantity
                else:
                    pnl = (entry_price - exit_price) * quantity
                
                # Update trade
                cursor.execute('''
                    UPDATE trades 
                    SET exit_time = ?, exit_price = ?, pnl = ?, status = ?
                    WHERE trade_id = ?
                ''', (exit_time, exit_price, pnl, 'CLOSED', trade_id))
                conn.commit()
                
                return pnl
        
        return 0
    
    def save_candle_data(self, symbol: str, timestamp: datetime, open_price: float, 
                        high_price: float, low_price: float, close_price: float, volume: int = 0):
        """Save candle data to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO candle_data 
                    (symbol, timestamp, open_price, high_price, low_price, close_price, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, timestamp, open_price, high_price, low_price, close_price, volume))
                conn.commit()
        except Exception as e:
            logging.error(f"Error saving candle data: {e}")
            raise
    
    def get_latest_candles(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get latest candle data for a symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, timestamp, open_price, high_price, low_price, close_price, volume
                    FROM candle_data 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (symbol, limit))
                
                rows = cursor.fetchall()
                return [
                    {
                        'symbol': row[0],
                        'timestamp': row[1],
                        'open_price': row[2],
                        'high_price': row[3],
                        'low_price': row[4],
                        'close_price': row[5],
                        'volume': row[6]
                    }
                    for row in rows
                ]
        except Exception as e:
            logging.error(f"Error getting latest candles: {e}")
            return []
    
    def get_candles_by_timeframe(self, symbol: str, start_time: datetime, 
                                end_time: datetime) -> List[Dict]:
        """Get candle data for a specific timeframe"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, timestamp, open_price, high_price, low_price, close_price, volume
                    FROM candle_data 
                    WHERE symbol = ? AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                ''', (symbol, start_time, end_time))
                
                rows = cursor.fetchall()
                return [
                    {
                        'symbol': row[0],
                        'timestamp': row[1],
                        'open_price': row[2],
                        'high_price': row[3],
                        'low_price': row[4],
                        'close_price': row[5],
                        'volume': row[6]
                    }
                    for row in rows
                ]
        except Exception as e:
            logging.error(f"Error getting candles by timeframe: {e}")
            return []
    
    def cleanup_old_candles(self, days_to_keep: int = 30):
        """Remove candle data older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM candle_data 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                deleted_count = cursor.rowcount
                conn.commit()
                logging.info(f"Cleaned up {deleted_count} old candle records")
                return deleted_count
        except Exception as e:
            logging.error(f"Error cleaning up old candles: {e}")
            return 0
    
    def save_trade_with_strategy_data(self, trade_id: str, symbol: str, strategy: str, side: str,
                                    entry_time: datetime, entry_price: float, quantity: int,
                                    stop_loss: float, take_profit: float, atr_value: float = None,
                                    signal_type: str = None, volume_ratio: float = None):
        """Save trade with enhanced strategy-specific data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trades 
                    (trade_id, symbol, strategy, side, entry_time, entry_price, quantity, 
                     status, stop_loss, take_profit, atr_value, signal_type, volume_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (trade_id, symbol, strategy, side, entry_time, entry_price, quantity,
                     'OPEN', stop_loss, take_profit, atr_value, signal_type, volume_ratio))
                conn.commit()
                logging.info(f"Trade saved: {trade_id}")
        except Exception as e:
            logging.error(f"Error saving trade: {e}")
            raise
    
    def start_trading_session(self, mode: str) -> str:
        """Start a new trading session"""
        session_id = str(uuid.uuid4())
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sessions (session_id, initial_balance, mode)
                    VALUES (?, ?, ?)
                ''', (session_id, 0.0, mode))
                conn.commit()
            return session_id
        except Exception as e:
            logging.error(f"Error starting trading session: {e}")
            return session_id

    def end_trading_session(self, session_id: str, final_pnl: float) -> bool:
        """End a trading session"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions 
                    SET end_time = CURRENT_TIMESTAMP, net_pnl = ?
                    WHERE session_id = ?
                ''', (final_pnl, session_id))
                conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error ending trading session: {e}")
            return False

    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM trades 
                    WHERE status = 'OPEN' 
                    ORDER BY entry_time DESC
                ''')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"Error getting open positions: {e}")
            return []

    def update_trade_exit(self, entry_order_id: str, exit_price: float, pnl: float, reason: str) -> bool:
        """Update trade with exit information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE trades 
                    SET exit_time = CURRENT_TIMESTAMP, exit_price = ?, pnl = ?, status = 'CLOSED'
                    WHERE trade_id = ? OR id = ?
                ''', (exit_price, pnl, entry_order_id, entry_order_id))
                conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating trade exit: {e}")
            return False

    def save_candle(self, symbol: str, timestamp: datetime, open_price: float, 
                   high_price: float, low_price: float, close_price: float, volume: int = 0):
        """Save candle data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO candle_data 
                    (symbol, timestamp, open_price, high_price, low_price, close_price, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, timestamp, open_price, high_price, low_price, close_price, volume))
                conn.commit()
        except Exception as e:
            logging.error(f"Error saving candle data: {e}")

    def get_recent_candles(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent candle data for a symbol"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM candle_data 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (symbol, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"Error getting recent candles: {e}")
            return []
