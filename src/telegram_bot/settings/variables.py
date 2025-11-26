import os
from dotenv import load_dotenv

load_dotenv()

telegram_token = os.getenv("TELEGRAM_TOKEN_DEV")
telegram_api_url = f"https://api.telegram.org/bot{telegram_token}"