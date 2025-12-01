import io
import os
import rich
import requests
import tempfile
from faster_whisper import WhisperModel
from telegram_bot.ollama.llm import Agent
from telegram_bot.settings.paths import WHITELIST_PATH
from fastapi import HTTPException, Request, BackgroundTasks
from telegram_bot.settings.variables import telegram_api_url
from telegram_bot.telegram.functions import send_telegram_message, download_file

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

def _transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    try:
        audio_stream = io.BytesIO(audio_bytes)
        segments, _ = model.transcribe(audio_stream, beam_size=5, language="es")

        transcription_text = ""
        for segment in segments:
            transcription_text += segment.text + " "

        return transcription_text.strip()

    except Exception as e:
        print(f"Error in local transcription: {e}")
        raise e

# def _transcribe_audio(audio_bytes: bytes, filename: str) -> str:
#     headers = {"Authorization": f"Bearer {openai_api_key}"}
#     files = {"file": (filename, audio_bytes, "audio/ogg")}
#     data = {"model": "whisper-1"}
#     response = requests.post(OPENAI_TRANSCRIPTION_URL, headers=headers, files=files, data=data)
#     response.raise_for_status()
#     return response.json()["text"]
    
def _handle_message(chat_id: int, text: str, name: str):
    try:
        result = agent.answer(
            question=text
        )

        send_telegram_message(chat_id, result)
        return {"status": "ok"}
    except Exception as e:
        print(f" Error while processing the message for {chat_id}: {e}")
        send_telegram_message(chat_id, "There was an error processing your message.")
        return {"status": "error", "message": f"e"}


def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        data = request.json()
        print("📥 Payload:")
        rich.print(data)

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            name = f"{message['from'].get('first_name', '')} {message['from'].get('last_name', '')}".strip() or "user"

            whitelist = _load_whitelist()
            if chat_id not in whitelist:
                print(f"Chat_id {chat_id} unauthorized")
                send_telegram_message(chat_id, " You are not allowed to use this chatbot.")
                return {"status": "unauthorized"}

            if "text" in message:
                text = message["text"]

                send_telegram_message(chat_id, "I'm processing your message...")

                background_tasks.add_task(_handle_message, chat_id, text, name)
            
            elif "voice" in message:
                send_telegram_message(chat_id, "Transcribing your audio...")
                temp_file_path = None
                try:
                    file_path = _get_file_path(message["voice"]["file_id"])
                    audio_bytes = download_file(file_path)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio_file:
                        temp_audio_file.write(audio_bytes)
                        temp_file_path = temp_audio_file.name
                    transcribed_text = _transcribe_audio(audio_bytes, os.path.basename(temp_file_path))
                    
                    if transcribed_text:
                        send_telegram_message(chat_id, f"Transcribed audio: {transcribed_text}")
                        background_tasks.add_task(_handle_message, chat_id, transcribed_text, name)

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