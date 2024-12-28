import logging
import sys


def setup_logging(env: str) -> None:
    """Configure logging for the application"""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler and set level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(
        logging.DEBUG if env.lower() == "staging" else logging.INFO
    )

    # Create formatter with environment info
    formatter = logging.Formatter(
        f"%(asctime)s - {env.upper()} - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add console handler to logger
    logger.addHandler(console_handler)
