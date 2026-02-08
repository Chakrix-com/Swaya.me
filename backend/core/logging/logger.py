"""
Logging configuration for structured logging
"""
import logging
import sys
from pythonjsonlogger import jsonlogger

from core.config.settings import settings


def setup_logging():
    """Configure structured logging"""
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.app.log_level.upper()))
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    # JSON formatter for production
    if settings.app.environment == "production":
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            rename_fields={
                "asctime": "timestamp",
                "name": "logger",
                "levelname": "level"
            }
        )
    else:
        # Simple formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Initialize logger
logger = setup_logging()
