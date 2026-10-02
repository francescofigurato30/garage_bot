import json
import logging
import os
import traceback
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Recupera il token dalle variabili d'ambiente
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8644857704:AAELOp6ZC5dACla9I_aYxkBhL9wY7UvVuS0")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(chat_id, text):
    """Invia un messaggio di testo a Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as e:
        print(f"Errore durante l'invio su Telegram: {e}")


@csrf_exempt
def telegram_webhook(request):
    """Endpoint webhook per ricevere gli aggiornamenti da Telegram."""
    # Controllo GET dal browser
    if request.method == "GET":
        return HttpResponse("Telegram Webhook Endpoint Active", status=200)

    # Gestione richieste POST da Telegram
    if request.method == "POST":
        try:
            body = request.body.decode("utf-8")
            if not body:
                return JsonResponse({"status": "empty body"}, status=200)

            data = json.loads(body)

            # Estrai i dettagli del messaggio se presenti
            message = data.get("message") or data.get("edited_message")
            if message:
                chat_id = message.get("chat", {}).get("id")
                text = (message.get("text") or "").strip()

                if chat_id and text:
                    # Gestione comandi base
                    if text.startswith("/start"):
                        risposta = (
                            "👋 <b>Benvenuto nel Garage Bot!</b>\n\n"
                            "Il bot è attivo e operativo su Vercel.\n"
                            "Scrivi <code>garage</code> o <code>scadenze</code> per verificare lo stato."
                        )
                        send_message(chat_id, risposta)

                    elif "garage" in text.lower():
                        send_message(chat_id, "🚗 Modulo Garage attivo! Controllo veicoli in corso...")

                    else:
                        send_message(chat_id, f"Ricevuto: {text}\n(Bot online su Vercel)")

            return JsonResponse({"status": "ok"}, status=200)

        except Exception as e:
            # Cattura qualsiasi errore Python e lo stampa chiaramente nei log di Vercel
            print("========================================")
            print("❌ ERRORE NEL WEBHOOK DI TELEGRAM:")
            print(traceback.format_exc())
            print("========================================")
            # Restituiamo 200 con l'errore per evitare loop di retry continui da Telegram
            return JsonResponse({
                "status": "error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }, status=200)

    return HttpResponse("Metodo non consentito", status=405)