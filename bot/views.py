import os
import json
from datetime import date, timedelta
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import requests

from bot.engine import handle_incoming_message
from bot.models import Deadline

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@csrf_exempt
def telegram_webhook(request):
    """Riceve i messaggi inviati dagli utenti su Telegram."""
    if request.method == "POST":
        try:
            payload = json.loads(request.body.decode('utf-8'))
            message = payload.get("message") or payload.get("edited_message")
            
            if message and "text" in message:
                user_id = str(message["from"]["id"])
                user_name = message["from"].get("first_name", "Utente")
                text = message["text"]

                # Elabora il messaggio con la tua logica esistente
                reply_text = handle_incoming_message(
                    wa_id=user_id,
                    text=text,
                    user_name=user_name
                )

                # Invia la risposta a Telegram
                send_data = {
                    "chat_id": user_id,
                    "text": reply_text,
                    "parse_mode": "Markdown"
                }
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=send_data, timeout=5)

            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
            
    return HttpResponse("Telegram Webhook Endpoint Active")

@csrf_exempt
def vercel_cron_check_deadlines(request):
    """Endpoint chiamato automaticamente dal Cron Job di Vercel ogni mattina."""
    today = date.today()
    alert_windows = [0, 7, 15, 30]
    notifications_sent = 0

    for window in alert_windows:
        target_date = today + timedelta(days=window)
        deadlines = Deadline.objects.filter(due_date=target_date, is_paid=False).select_related('vehicle', 'vehicle__user')

        for d in deadlines:
            v = d.vehicle
            user = v.user

            if d.deadline_type == 'INSURANCE':
                tipo = "🛡️ Polizza Assicurativa"
                cmd_tipo = "polizza"
            elif d.deadline_type == 'TAX':
                tipo = "🏷️ Bollo"
                cmd_tipo = "bollo"
            else:
                tipo = "🔧 Revisione Ministeriale"
                cmd_tipo = "revisione"

            urgency = "OGGI!" if window == 0 else f"tra {window} giorni ({d.due_date.strftime('%d/%m/%Y')})"

            alert_text = (
                f"🔔 *PROMEMORIA SCADENZA GARAGE*\n\n"
                f"Ciao {user.name or 'Utente'}, il tuo mezzo *{v.model}* (`{v.plate}`) ha una scadenza imminente:\n"
                f"👉 *{tipo}*: {urgency}\n\n"
                f"💡 Per aggiornare rispondi con:\n"
                f"`rinnova {v.plate} {cmd_tipo}`"
            )

            try:
                send_data = {
                    "chat_id": user.wa_id,
                    "text": alert_text,
                    "parse_mode": "Markdown"
                }
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=send_data, timeout=5)
                notifications_sent += 1
            except Exception:
                pass

    return JsonResponse({"status": "completed", "notifications_sent": notifications_sent})