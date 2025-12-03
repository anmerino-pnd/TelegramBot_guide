from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from telegram_bot.API.chatbot import telegram_webhook
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/webhook")
async def telegram_webhook_handler(request: Request, background_tasks: BackgroundTasks):
    try:
        await telegram_webhook(request, background_tasks)
        return {"status": "ok"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error en webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando webhook: {str(e)}")

