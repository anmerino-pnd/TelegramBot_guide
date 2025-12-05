import io
import requests
from telegram_bot.settings.variables import telegram_token

def send_telegram_message(chat_id: int, message: str, reply_markup: dict = None):
    payload = {"chat_id": chat_id, "text": message}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    response = requests.post(f"{telegram_token}/sendMessage", json=payload)
    if response.status_code != 200:
        print(f"📨 Error enviando mensaje a Telegram: {response.status_code} {response.text}")

def download_file(file_path: str) -> bytes:
    file_url = f"{telegram_token}/{file_path}"
    response = requests.get(file_url)
    response.raise_for_status()
    return response.content

def send_telegram_pdf(chat_id: int, pdf_bytes: bytes, filename: str, caption: str = "Reporte listo"):
    url = f"{telegram_token}/sendDocument"

    files = {'document': (filename, pdf_bytes, 'application/pdf')}
    data = {'chat_id': chat_id, 'caption': caption}

    try:
        response = requests.post(url, data=data, files=files, timeout=60)
        response.raise_for_status()
        result = response.json()
        if not result.get('ok'):
            raise Exception(f"Error API Telegram: {result.get('description', 'Error desconocido')}")
        return True
    except requests.exceptions.Timeout:
        raise Exception("Timeout al enviar archivo a Telegram")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error de conexión: {str(e)}")
    
def send_telegram_image(chat_id: int, image_bytes: io.BytesIO, caption: str = None) -> None:
    """Envía imagen directamente a Telegram sin guardarla en disco."""
    url = f"{telegram_token}/sendPhoto"
    files = {'photo': ('table.png', image_bytes, 'image/png')}
    data = {'chat_id': chat_id}
    if caption:
        data['caption'] = caption
    
    response = requests.post(url, data=data, files=files, timeout=60)
    response.raise_for_status()
    result = response.json()
    if not result.get('ok'):
        raise Exception(f"Error API Telegram: {result.get('description', 'Error desconocido')}")
