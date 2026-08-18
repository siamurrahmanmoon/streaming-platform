import sys
from pathlib import Path
from loguru import logger

# Remove default logger
logger.remove()

# Console logger (colorful, for development)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# File logger (for production, with rotation)
log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)

logger.add(
    log_dir / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="30 days",
    compression="zip"
)

# Error-only logger
logger.add(
    log_dir / "errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="5 MB",
    retention="60 days"
)

def get_logger(name: str = "app"):
    """Get a logger instance with module name"""
    return logger.bind(module=name)