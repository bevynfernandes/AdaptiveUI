import io
from sys import stderr

from loguru import logger

min_level = "DEBUG"
history = io.StringIO()


def my_filter(record: dict) -> bool:
    return record["level"].no >= logger.level(min_level).no


logger.remove()
logger.add(history, backtrace=True, diagnose=True, enqueue=True)
logger.add(stderr, filter=my_filter, backtrace=True, diagnose=True, enqueue=True)


def write_log(file: str = "debug.log"):
    """
    Writes log messages to a specified file.

    Args:
        file (str): The name of the log file. Defaults to "debug.log".
    """
    logger.add(file, backtrace=True, diagnose=True, enqueue=True)
