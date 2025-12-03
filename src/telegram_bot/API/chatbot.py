import io
import os
import rich
import whisper
import requests
import tempfile
from faster_whisper import WhisperModel
from telegram_bot.ollama.llm import Agent
from telegram_bot.settings.paths import WHITELIST_PATH
from fastapi import HTTPException, Request, BackgroundTasks
from telegram_bot.settings.variables import telegram_api_url
from telegram_bot.telegram.functions import send_telegram_message, download_file

audio_model = whisper.load_model('base') # tiny, base, small, medium, large

agent = Agent()

def _load_whitelist(filepath: str = WHITELIST_PATH) -> set[int]:
    try:
        with open(filepath, "r") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    except FileNotFoundError:
        print("Whitelist not found.")
        return set()
    
def _get_file_path(file_id: str) -> str:
    response = requests.get(f"{telegram_api_url}/getFile?file_id={file_id}")
    response.raise_for_status()
    return response.json()["result"]["file_path"]

model_size = "small"
model = WhisperModel(model_size, device="cuda", compute_type="float16")

def _transcribe_audio(audio_bytes: bytes) -> str:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
        segments, _ = model.transcribe(
            temp_path, 
            beam_size=5, 
            language="es",
            vad_filter=True)

        transcription_text = " ".join(segment.text.strip() for segment in segments)

        return transcription_text

    except Exception as e:
        print(f"Error in local transcription: {e}")
        raise e
    
def _handle_message(chat_id: int, text: str):
    try:
        response, metadata = agent.answer(
            question=text
        )

        send_telegram_message(chat_id, f"{response}\n\n{metadata}")
        return {"status": "ok"}
    except Exception as e:
        print(f" Error while processing the message for {chat_id}: {e}")
        send_telegram_message(chat_id, "There was an error processing your message.")
        return {"status": "error", "message": f"e"}


async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    chat_id = None
    try:
        data = await request.json()
        print("📥 Payload:")
        rich.print(data)

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]

            whitelist = _load_whitelist()
            if chat_id not in whitelist:
                print(f"Chat_id {chat_id} unauthorized")
                send_telegram_message(chat_id, " You are not allowed to use this chatbot.")
                return {"status": "unauthorized"}

            if "text" in message:
                text = message["text"]

                send_telegram_message(chat_id, "I'm processing your message...")

                background_tasks.add_task(_handle_message, chat_id, text)
            
            elif "voice" in message:
                send_telegram_message(chat_id, "Transcribing your audio...")
                temp_file_path = None
                try:
                    file_path = _get_file_path(message["voice"]["file_id"])
                    audio_bytes = download_file(file_path)
                    transcribed_text = _transcribe_audio(audio_bytes)
                    
                    if transcribed_text:
                        send_telegram_message(chat_id, f"Transcribed audio: {transcribed_text}")
                        background_tasks.add_task(_handle_message, chat_id, transcribed_text)

                    else:
                        send_telegram_message(chat_id, "I couldn't transcribe your audio. Can you repeat it?")
                except Exception as e:
                    print(f"Error processing the audio: {e}")
                    send_telegram_message(chat_id, f"Error while processing your audio.\n{e}")
                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
            else:
                send_telegram_message(chat_id, "Only text and voice messages can be answered.")
            return {"status": "ok"}

    except Exception as e:
        print(f"Telegram webhook error: {e}")
        send_telegram_message(chat_id, f"Telegram webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))