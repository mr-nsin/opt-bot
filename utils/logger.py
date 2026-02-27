import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

class TradingLogger:
    def __init__(self, log_dir: str = "logs", max_file_size: str = "10MB", backup_count: int = 5):
        self.log_dir = log_dir
        self.max_file_size = self._parse_size(max_file_size)
        self.backup_count = backup_count
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup different loggers
        self.setup_loggers()
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        else:
            return int(size_str)
    
    def setup_loggers(self):
        """Setup different loggers for different purposes"""
        
        # Main trading logger
        self.trading_logger = self._create_logger(
            name='trading',
            filename='trading.log',
            level=logging.INFO
        )
        
        # Trades logger
        self.trades_logger = self._create_logger(
            name='trades',
            filename='trades.log',
            level=logging.INFO
        )
        
        # Error logger
        self.error_logger = self._create_logger(
            name='errors',
            filename='errors.log',
            level=logging.ERROR
        )
        
        # System logger
        self.system_logger = self._create_logger(
            name='system',
            filename='system.log',
            level=logging.DEBUG
        )
    
    def _create_logger(self, name: str, filename: str, level: int) -> logging.Logger:
        """Create a logger with rotating file handler"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create rotating file handler
        log_file = os.path.join(self.log_dir, filename)
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger
    
    def log_trade_entry(self, trade_data: dict):
        """Log trade entry"""
        message = (
            f"TRADE ENTRY - Symbol: {trade_data.get('symbol')}, "
            f"Side: {trade_data.get('side')}, "
            f"Price: {trade_data.get('entry_price')}, "
            f"Quantity: {trade_data.get('quantity')}, "
            f"SL: {trade_data.get('stop_loss')}, "
            f"TP: {trade_data.get('take_profit')}"
        )
        self.trades_logger.info(message)
        self.trading_logger.info(message)
    
    def log_trade_exit(self, trade_data: dict, pnl: float):
        """Log trade exit"""
        message = (
            f"TRADE EXIT - Symbol: {trade_data.get('symbol')}, "
            f"Side: {trade_data.get('side')}, "
            f"Exit Price: {trade_data.get('exit_price')}, "
            f"PnL: ${pnl:.2f}, "
            f"Status: {trade_data.get('status')}"
        )
        self.trades_logger.info(message)
        self.trading_logger.info(message)
    
    def log_signal(self, signal_type: str, symbol: str, price: float, strength: float, executed: bool = False):
        """Log trading signal"""
        status = "EXECUTED" if executed else "DETECTED"
        message = f"SIGNAL {status} - {signal_type} {symbol} at {price:.2f}, Strength: {strength:.2f}"
        self.trading_logger.info(message)
    
    def log_system_event(self, message: str, level: str = "INFO"):
        """Log system events"""
        if level.upper() == "ERROR":
            self.error_logger.error(message)
            self.system_logger.error(message)
        elif level.upper() == "WARNING":
            self.system_logger.warning(message)
        elif level.upper() == "DEBUG":
            self.system_logger.debug(message)
        else:
            self.system_logger.info(message)
        
        self.trading_logger.info(f"SYSTEM: {message}")
    
    def log_connection_event(self, event_type: str, details: str = ""):
        """Log broker connection events"""
        message = f"CONNECTION {event_type.upper()} - {details}"
        self.system_logger.info(message)
        self.trading_logger.info(message)
    
    def log_error(self, error_message: str, exception: Optional[Exception] = None):
        """Log errors"""
        if exception:
            message = f"ERROR: {error_message} - Exception: {str(exception)}"
            self.error_logger.error(message, exc_info=True)
        else:
            message = f"ERROR: {error_message}"
            self.error_logger.error(message)
        
        self.trading_logger.error(message)
    
    def log_performance(self, metrics: dict):
        """Log performance metrics"""
        message = (
            f"PERFORMANCE - Total Trades: {metrics.get('total_trades', 0)}, "
            f"Win Rate: {metrics.get('win_rate', 0):.1f}%, "
            f"Net PnL: ${metrics.get('net_profit', 0):.2f}, "
            f"Avg Win: ${metrics.get('avg_win', 0):.2f}, "
            f"Avg Loss: ${metrics.get('avg_loss', 0):.2f}"
        )
        self.trading_logger.info(message)
    
    def get_recent_logs(self, log_type: str = "trading", lines: int = 100) -> list:
        """Get recent log lines"""
        log_file = os.path.join(self.log_dir, f"{log_type}.log")
        
        if not os.path.exists(log_file):
            return []
        
        try:
            with open(log_file, 'r') as f:
                return f.readlines()[-lines:]
        except Exception as e:
            return [f"Error reading log file: {str(e)}"]

# Global logger instance
trading_logger = TradingLogger()
