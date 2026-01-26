"""
MEMO Logging System
Provides structured logging with file rotation and colored console output.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


class MEMOLogger:
    """Centralized logging configuration for MEMO system."""
    
    _instance: Optional['MEMOLogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.log_dir = Path("logs")
            self.log_dir.mkdir(exist_ok=True)
            self.loggers = {}
            MEMOLogger._initialized = True
    
    def setup(
        self,
        level: str = "INFO",
        log_to_file: bool = True,
        log_to_console: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """
        Configure the logging system.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Enable file logging
            log_to_console: Enable console logging
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
        """
        self.level = getattr(logging, level.upper(), logging.INFO)
        
        # File handler
        if log_to_file:
            log_file = self.log_dir / f"memo_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.level)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.file_handler = file_handler
        else:
            self.file_handler = None
        
        # Console handler with colors
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            
            if HAS_COLORLOG:
                console_formatter = colorlog.ColoredFormatter(
                    '%(log_color)s%(levelname)-8s%(reset)s %(cyan)s%(name)s%(reset)s - %(message)s',
                    datefmt='%H:%M:%S',
                    log_colors={
                        'DEBUG': 'blue',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red,bg_white',
                    }
                )
            else:
                console_formatter = logging.Formatter(
                    '%(levelname)-8s %(name)s - %(message)s',
                    datefmt='%H:%M:%S'
                )
            
            console_handler.setFormatter(console_formatter)
            self.console_handler = console_handler
        else:
            self.console_handler = None
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a logger with the given name.
        
        Args:
            name: Logger name (usually __name__ of the module)
            
        Returns:
            Configured logger instance
        """
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(self.level)
        logger.propagate = False
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Add configured handlers
        if self.file_handler:
            logger.addHandler(self.file_handler)
        if self.console_handler:
            logger.addHandler(self.console_handler)
        
        self.loggers[name] = logger
        return logger


# Global functions for easy access
_logger_instance = MEMOLogger()


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True
) -> None:
    """
    Setup the global logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable file logging
        log_to_console: Enable console logging
    """
    _logger_instance.setup(level, log_to_file, log_to_console)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the specified module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("System started")
    """
    return _logger_instance.get_logger(name)


# Performance timing decorator
def log_execution_time(func):
    """Decorator to log function execution time."""
    import time
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            logger.debug(f"{func.__name__} executed in {elapsed:.2f}ms")
            return result
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"{func.__name__} failed after {elapsed:.2f}ms: {e}")
            raise
    
    return wrapper
