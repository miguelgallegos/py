import os
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.environ.get("APP_ENV", "development")
TEST_MODE = os.environ.get("TEST_MODE", "true").lower() in ("1", "true", "yes", "on")
DEFAULT_AUTO_TRADE_PERCENT = float(os.environ.get("DEFAULT_AUTO_TRADE_PERCENT", "10"))

EXCHANGE_CONFIG = {
    "robinhood": {
        "username": os.environ.get("ROBINHOOD_USERNAME"),
        "password": os.environ.get("ROBINHOOD_PASSWORD"),
        "two_factor_method": os.environ.get("ROBINHOOD_2FA_METHOD", "sms"),
    },
    "webull": {
        "app_key": os.environ.get("WEBULL_APP_KEY"),
        "app_secret": os.environ.get("WEBULL_APP_SECRET"),
        "region": os.environ.get("WEBULL_REGION", "us"),
        "account_id": os.environ.get("WEBULL_ACCOUNT_ID"),
        "api_endpoint": os.environ.get("WEBULL_API_ENDPOINT"),
        "token_dir": os.environ.get("WEBULL_TOKEN_DIR"),
    },
    "kraken": {
        "api_key": os.environ.get("KRAKEN_API_KEY"),
        "api_secret": os.environ.get("KRAKEN_API_SECRET"),
    },
    "alpaca": {
        "api_key": os.environ.get("ALPACA_API_KEY"),
        "api_secret": os.environ.get("ALPACA_API_SECRET"),
        "base_url": os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
    },
}
