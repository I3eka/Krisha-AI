import sys
from loguru import logger
from src.config.settings import settings


def setup_logger():
    """
    Configures the Loguru logger.
    - Removes the default handler.
    - Adds a console handler with colors.
    - Adds a file handler with rotation and compression.
    """

    logger.remove()

    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        colorize=True,
    )

    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info(f"Logger initialized. Level: {settings.LOG_LEVEL}")
