import os
import ollama as ollama_api
from dotenv import load_dotenv

load_dotenv()

ollama_api_key: str = os.getenv("OLLAMA_API_KEY") or ""

# If you're using the cloud models you'll need an api key. Otherwise will run local model
ollama = ollama_api.Client(
    host="https://ollama.com", 
    headers={'Authorization': 'Bearer ' + ollama_api_key}) if ollama_api_key else ollama_api.Client()

telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_api_url = f"https://api.telegram.org/bot{telegram_token}"