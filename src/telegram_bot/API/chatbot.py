import rich
import requests
import tempfile
from telegram_bot.settings.config import WHITELIST_PATH
from fastapi import HTTPException, Request, BackgroundTasks
from telegram_bot.settings.variables import telegram_api_url
from telegram_bot.telegram.functions import send_telegram_message, download_file

part_state = {}

def _load_whitelist(filepath: str = WHITELIST_PATH) -> set[int]:
    try:
        with open(filepath, "r") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    except FileNotFoundError:
        print("⚠️ Archivo de whitelist no encontrado.")
        return set()
    
def _get_file_path(file_id: str) -> str:
    response = requests.get(f"{telegram_api_url}/getFile?file_id={file_id}")
    response.raise_for_status()
    return response.json()["result"]["file_path"]
    
async def _handle_message(chat_id: int, text: str, name: str):
    """Procesa una pregunta, obtiene una respuesta y la envía a Telegram."""
    try:
        # result, backup_id = await agent_multi_tools.answer(
        #     question=text,
        #     session_id=str(chat_id),
        #     name=name,
        #     feedback_context=feedback_context
        # )
        
        # part_state[chat_id] = {
        #     "text": text,
        #     "name": name,
        #     "backup_id": str(backup_id) if backup_id else None
        # }


        # final_message = f"{result}\n\n ¿Esta respuesta fue útil?"
        # feedback_keyboard = [[
        #     {"text": "👍 Sí", "callback_data": "feedback_yes"},
        #     {"text": "👎 No", "callback_data": "feedback_no"}
        # ]]
        #send_telegram_message(chat_id, final_message, reply_markup={"inline_keyboard": feedback_keyboard})
        pass
    except Exception as e:
        print(f"❌ Error al procesar mensaje para {chat_id}: {e}")
        send_telegram_message(chat_id, "⚠️ Ocurrió un error procesando tu mensaje.")


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
                part_state[chat_id] = {"text": text, "name": name}
                print(f"✅ Enviando a handle_message: chat_id={chat_id}, text='{text[:50]} ...'")

                 # 🕐 Mensaje de espera al usuario
                send_telegram_message(chat_id, "💬 Versión de Dev: Estoy procesando tu mensaje, dame un momento por favor...")

                background_tasks.add_task(_handle_message, chat_id, text, name)
            
            elif "voice" in message:
                send_telegram_message(chat_id, "🎧 Recibiendo audio y transcribiendo...")
                temp_file_path = None
                try:
                    file_path = _get_file_path(message["voice"]["file_id"])
                    audio_bytes = download_file(file_path)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio_file:
                        temp_audio_file.write(audio_bytes)
                        temp_file_path = temp_audio_file.name
                    transcribed_text = transcribe_audio(audio_bytes, os.path.basename(temp_file_path))
                    print(f"🎤 Audio transcrito: {transcribed_text}")
                    if transcribed_text:
                        send_telegram_message(chat_id, f"Tu pregunta: *{transcribed_text}*", {"parse_mode": "Markdown"})
                        background_tasks.add_task(handle_message, chat_id, transcribed_text, name)
                    else:
                        send_telegram_message(chat_id, "No pude transcribir el audio. ¿Podrías repetirlo?")
                except Exception as e:
                    print(f"❌ Error al procesar audio: {e}")
                    send_telegram_message(chat_id, f"⚠️ Ocurrió un error al procesar tu audio.")
                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
            else:
                send_telegram_message(chat_id, "Actualmente solo puedo procesar mensajes de texto y voz.")
            return {"status": "ok"}

    except Exception as e:
        print(f"❌ Error fatal en webhook de Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))