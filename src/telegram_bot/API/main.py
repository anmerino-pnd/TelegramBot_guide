from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from telegram_bot.settings.variables import telegram_api_url

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

