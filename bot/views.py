import json
import logging
import os
import traceback
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8644857704:AAELOp6ZC5dACla9I_aYxkBhL9wY7UvVuS0")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(chat_id, text):
    """Invia un messaggio su Telegram via API HTTP."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except Exception as e:
        print(f"Errore invio Telegram: {e}")
        return False


@csrf_exempt
def telegram_webhook(request):
    """Riceve i messaggi in arrivo da Telegram."""
    if request.method == "GET":
        return HttpResponse("Telegram Webhook Endpoint Active", status=200)

    if request.method == "POST":
        try:
            body = request.body.decode("utf-8")
            if not body:
                return JsonResponse({"status": "empty body"}, status=200)

            data = json.loads(body)
            message = data.get("message") or data.get("edited_message")

            if message:
                chat_id = message.get("chat", {}).get("id")
                text = (message.get("text") or "").strip()

                if chat_id and text:
                    if text.startswith("/start"):
                        risposta = (
                            "👋 <b>Garage Bot è Online!</b>\n\n"
                            "Connessione con Vercel e Neon riuscita.\n"
                            "Scrivi <code>garage</code> per visualizzare i veicoli registrati."
                        )
                        send_message(chat_id, risposta)
                    elif "garage" in text.lower():
                        send_message(chat_id, "🚗 Modulo Veicoli attivo! Sistema pronto.")
                    else:
                        send_message(chat_id, f"Comando ricevuto: {text}")

            return JsonResponse({"status": "ok"}, status=200)

        except Exception as e:
            print("========================================")
            print("❌ ERRORE NEL WEBHOOK TELEGRAM:")
            print(traceback.format_exc())
            print("========================================")
            return JsonResponse({"status": "error", "message": str(e)}, status=200)

    return HttpResponse("Metodo non consentito", status=405)


@csrf_exempt
def vercel_cron_check_deadlines(request):
    """Endpoint chiamato dal Cron Job di Vercel per il controllo scadenze."""
    return JsonResponse({"status": "cron ok", "message": "Nessuna scadenza imminente"}, status=200)