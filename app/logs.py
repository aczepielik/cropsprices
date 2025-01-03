import functools
import inspect
import logging
import time
from typing import List, Literal, Optional


# Configure logging
def setup_logger(env: Literal["dev", "staging", "prod"]):
    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO if env != "dev" else logging.DEBUG)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add our handlers
    logger.addHandler(console_handler)

    return logger


# Decorator for database operations


def log_db_operation(args: Optional[List[str]] = None):
    """
    Decorator for logging database operations with specified argument values.

    Args:
        args: List of argument names whose values should be included in the log message
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*func_args, **func_kwargs):
            start_time = time.time()

            # Get the argument values if args parameter is provided
            arg_values = {}
            if args:
                # Get positional arguments using function's signature
                bound_args = inspect.signature(func).bind(*func_args, **func_kwargs)
                bound_args.apply_defaults()
                arg_dict = bound_args.arguments

                # Extract requested argument values
                arg_values = {
                    arg_name: arg_dict[arg_name]
                    for arg_name in args
                    if arg_name in arg_dict
                }

            # Format argument string
            args_str = (
                ", ".join(f"{k}={repr(v)}" for k, v in arg_values.items())
                if arg_values
                else ""
            )
            args_msg = f" Args: {args_str}" if args_str else ""

            try:
                result = func(*func_args, **func_kwargs)
                execution_time = time.time() - start_time

                logging.info(
                    f"DB Operation: {func.__name__} completed in {execution_time:.2f} seconds."
                    f"{args_msg}"
                )
                return result

            except Exception as e:
                logging.error(
                    f"DB Operation: {func.__name__} failed after {time.time() - start_time:.2f} seconds."
                    f"{args_msg} Error: {str(e)}"
                )
                raise

        return wrapper

    # Handle cases where decorator is used without parameters
    if callable(args):
        func = args
        args = None
        return decorator(func)

    return decorator


# Decorator for UI interactions
def log_ui_interaction(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logging.debug(f"UI Interaction: {func.__name__} started")
            result = func(*args, **kwargs)
            logging.debug(f"UI Interaction: {func.__name__} completed successfully")
            return result

        except Exception as e:
            logging.error(f"UI Interaction: {func.__name__} failed. Error: {str(e)}")
            raise

    return wrapper


# Decorator for application initialization
def log_initialization(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Initializing: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logging.info(f"Initialization complete: {func.__name__}")
            return result

        except Exception as e:
            logging.error(f"Initialization failed: {func.__name__}. Error: {str(e)}")
            raise

    return wrapper
