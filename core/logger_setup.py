import logging
import os
from logging.handlers import RotatingFileHandler

# Define the log directory and ensure it exists
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Log formats for INFO and DEBUG levels
LOG_FORMAT_INFO = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_DEBUG = "%(asctime)s - %(name)s - %(levelname)s - Line: %(lineno)d - %(message)s"
LOG_LEVEL = logging.DEBUG

# Server log file
SERVER_LOG_FILE = os.path.join(LOG_DIR, "btcmesh_server.log")

def setup_logger(
    logger_name: str, log_file: str, level: int = LOG_LEVEL
) -> logging.Logger:
    """
    Configures and returns a logger instance.

    Args:
        logger_name: The name for the logger.
        log_file: The path to the log file.
        level: The logging level.

    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False  # Prevents log duplication

    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT_DEBUG if level == logging.DEBUG else LOG_FORMAT_INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Rotating File Handler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB per file, 5 backups
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Pre-configured server logger instance
server_logger = setup_logger("btcmesh_server", SERVER_LOG_FILE)

if __name__ == "__main__":
    # Example usage
    test_logger_info = setup_logger(
        "test_logger_info", os.path.join(LOG_DIR, "test_info.log"), logging.INFO
    )
    
    test_logger_debug = setup_logger(
        "test_logger_debug", os.path.join(LOG_DIR, "test_debug.log"), logging.DEBUG
    )
    
    # Logging various messages
    test_logger_info.info("This is an info message.")
    test_logger_info.warning("This is a warning message.")

    test_logger_debug.debug("This is a debug message with line number.")
    test_logger_debug.info("This is an info message from debug logger.")
    test_logger_debug.warning("This is a warning message from debug logger.")
