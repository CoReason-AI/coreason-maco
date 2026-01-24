import sys

from loguru import logger

# Remove default handler and add a structured one
logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
)

__all__ = ["logger"]
