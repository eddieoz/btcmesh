import os
from dotenv import load_dotenv
from typing import Optional

from core.logger_setup import server_logger

# Load environment variables from .env file in the project root
# Determine the project root by going up one level from the 'core' directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")

# A flag to ensure dotenv is loaded only once
dotenv_loaded = False


def load_app_config() -> None:
    """Loads the .env file. Can be called explicitly at app startup."""
    global dotenv_loaded
    if not dotenv_loaded:
        if os.path.exists(DOTENV_PATH):
            load_dotenv(dotenv_path=DOTENV_PATH)
            server_logger.info(f".env file loaded from {DOTENV_PATH}")
            dotenv_loaded = True
        else:
            server_logger.info(
                f".env file not found at {DOTENV_PATH}. "
                "Using environment variables or defaults."
            )
            # dotenv_loaded can be set to True even if not found,
            # to prevent re-checks or kept False if we want to allow
            # retries/reloads in some scenarios. For typical app startup,
            # one check is enough.
            dotenv_loaded = True


def get_meshtastic_serial_port() -> Optional[str]:
    """
    Retrieves the Meshtastic serial port from environment variables.
    Ensures .env is loaded before attempting to retrieve.
    """
    if not dotenv_loaded:
        load_app_config()  # Ensure config is loaded

    return os.getenv("MESHTASTIC_SERIAL_PORT")


def load_bitcoin_rpc_config():
    """
    Loads Bitcoin RPC config from environment variables (.env).
    Returns a dict with host, port, user, password, cookie.
    Raises ValueError if any required field is missing.
    Story 4.1.
    """
    config = {
        "host": os.getenv("BITCOIN_RPC_HOST", "127.0.0.1"),
        "port": int(os.getenv("BITCOIN_RPC_PORT", 8332)),
        "user": os.environ.get("BITCOIN_RPC_USER"),
        "password": os.environ.get("BITCOIN_RPC_PASSWORD"),
    }
    cookie_path = os.getenv("BITCOIN_RPC_COOKIE")
    if cookie_path:
        if not os.path.isfile(cookie_path):
            raise ValueError(f".cookie file not found: {cookie_path}")
        try:
            with open(cookie_path, "r") as f:
                cookie = f.read().strip()
                config["user"], config["password"] = cookie.split(":", 1)
        except Exception as e:
            raise ValueError(f"Error to read file .cookie: {e}")
    else:
        config["user"] = os.getenv("BITCOIN_RPC_USER")
        config["password"] = os.getenv("BITCOIN_RPC_PASSWORD")
        if not config["user"] or not config["password"]:
            raise ValueError(
                "Wrong credentials. "
                "Define BITCOIN_RPC_COOKIE or BITCOIN_RPC_USER and BITCOIN_RPC_PASSWORD."
            )
    return config


def load_reassembly_timeout():
    """
    Loads reassembly timeout (seconds) from environment variables (.env).
    Returns (timeout_seconds: int, source: str); source is 'env' or 'default'.
    Logs the loaded value and its source.
    Falls back to default (30s) if missing/invalid.
    """
    if not dotenv_loaded:
        load_app_config()
    val = os.environ.get("REASSEMBLY_TIMEOUT_SECONDS")
    default = 30
    if val is None:
        server_logger.info(
            f"REASSEMBLY_TIMEOUT_SECONDS not set. Using default: {default}s."
        )
        return default, "default"
    try:
        timeout = int(val)
        if timeout <= 0:
            raise ValueError()
        server_logger.info(f"Loaded reassembly timeout from env: {timeout}s.")
        return timeout, "env"
    except Exception:
        server_logger.warning(
            f"Invalid REASSEMBLY_TIMEOUT_SECONDS value '{val}'. "
            f"Using default: {default}s."
        )
        return default, "default"


# Example of how to extend for more configurations:
# def get_rpc_host() -> Optional[str]:
#     if not dotenv_loaded:
#         load_app_config()
#     return os.getenv('BITCOIN_RPC_HOST')

# Call load_app_config at module import time if you want it to load
# automatically when this module is imported. Or, call it explicitly
# from your main script. For now, let's make it explicit by calling
# from functions that need the config.
