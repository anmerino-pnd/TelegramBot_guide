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
        print("Archivo de whitelist no encontrado.")
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
        print(f"Error en transcripción local: {e}")
        raise e

# def _transcribe_audio(audio_bytes: bytes, filename: str) -> str:
#     headers = {"Authorization": f"Bearer {openai_api_key}"}
#     files = {"file": (filename, audio_bytes, "audio/ogg")}
#     data = {"model": "whisper-1"}
#     response = requests.post(OPENAI_TRANSCRIPTION_URL, headers=headers, files=files, data=data)
#     response.raise_for_status()
#     return response.json()["text"]
    
async def _handle_message(chat_id: int, text: str, name: str):
    """Procesa una pregunta, obtiene una respuesta y la envía a Telegram."""
    try:
        result = agent.answer(
            question=text
        )

        send_telegram_message(chat_id, result)
        pass
    except Exception as e:
        print(f"❌ Error al procesar mensaje para {chat_id}: {e}")
        send_telegram_message(chat_id, "Ocurrió un error procesando tu mensaje.")


async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        print("📥 Payload recibido:")
        rich.print(data)

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            name = f"{message['from'].get('first_name', '')} {message['from'].get('last_name', '')}".strip() or "Usuario"

            whitelist = _load_whitelist()
            if chat_id not in whitelist:
                print(f"🚫 chat_id {chat_id} no autorizado")
                send_telegram_message(chat_id, "❌ No estás autorizado para usar este bot.")
                return {"status": "unauthorized"}

            if "text" in message:
                text = message["text"]

                send_telegram_message(chat_id, "Estoy procesando tu mensaje, dame un momento por favor...")

                background_tasks.add_task(_handle_message, chat_id, text, name)
            
            elif "voice" in message:
                send_telegram_message(chat_id, "Recibiendo audio y transcribiendo...")
                temp_file_path = None
                try:
                    file_path = _get_file_path(message["voice"]["file_id"])
                    audio_bytes = download_file(file_path)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio_file:
                        temp_audio_file.write(audio_bytes)
                        temp_file_path = temp_audio_file.name
                    transcribed_text = _transcribe_audio(audio_bytes, os.path.basename(temp_file_path))
                    
                    if transcribed_text:
                        send_telegram_message(chat_id, f"Audio transcrito: {transcribed_text}")
                        background_tasks.add_task(_handle_message, chat_id, transcribed_text, name)

                    else:
                        send_telegram_message(chat_id, "No pude transcribir el audio. ¿Podrías repetirlo?")
                except Exception as e:
                    print(f"Error al procesar audio: {e}")
                    send_telegram_message(chat_id, f"Ocurrió un error al procesar tu audio.")
                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
            else:
                send_telegram_message(chat_id, "Actualmente solo puedo procesar mensajes de texto y voz.")
            return {"status": "ok"}

    except Exception as e:
        print(f"Error fatal en webhook de Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))