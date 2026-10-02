import json
import logging
import os
import traceback
from datetime import date, timedelta
import requests
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Deadline, Expense, UserProfile, Vehicle

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN", "8644857704:AAELOp6ZC5dACla9I_aYxkBhL9wY7UvVuS0"
)
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(chat_id, text):
    """Invia un messaggio di testo a Telegram formattato in HTML."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except Exception as e:
        logger.error(f"Errore invio Telegram: {e}")
        return False


def handle_user_command(user, text, chat_id):
    """Gestisce la logica dei comandi e risponde interrogando Neon DB."""
    text_clean = text.strip()
    cmd = text_clean.lower()

    if cmd == "/start":
        return (
            f"👋 Ciao <b>{user.name or 'Pilota'}</b>!\n\n"
            "Benvenuto nel tuo <b>Garage Bot H24</b>.\n\n"
            "Comandi disponibili:\n"
            "🚗 <code>garage</code> - Lista veicoli e stato storico\n"
            "📅 <code>scadenze</code> - Prossime scadenze (bollo, assicurazione, revisione)\n"
            "💶 <code>spese</code> - Totale spese per veicolo"
        )

    elif "garage" in cmd:
        vehicles = user.vehicles.all()
        if not vehicles.exists():
            return "🚘 Il tuo garage è attualmente vuoto. Nessun veicolo associato."

        out = ["🚗 <b>I tuoi Veicoli:</b>\n"]
        for v in vehicles:
            out.append(
                f"• <b>{v.model}</b> ({v.plate})\n"
                f"  Tipo: {v.get_vehicle_type_display()} | Anno: {v.registration_year or 'N/D'}\n"
                f"  Stato: {v.historical_status}\n"
            )
        return "\n".join(out)

    elif "scadenze" in cmd:
        # Prende le scadenze non pagate dei veicoli dell'utente
        deadlines = Deadline.objects.filter(
            vehicle__user=user, is_paid=False
        ).order_by("due_date")
        if not deadlines.exists():
            return "✅ Ottimo! Non hai scadenze arretrate o imminenti registrate."

        out = ["📅 <b>Scadenze da saldare:</b>\n"]
        today = date.today()
        for d in deadlines:
            giorni = (d.due_date - today).days
            if giorni < 0:
                stato = f"⚠️ <b>SCADUTA da {abs(giorni)} giorni</b>"
            elif giorni <= 15:
                stato = f"⏳ In scadenza tra {giorni} giorni"
            else:
                stato = f"Prevista per il {d.due_date.strftime('%d/%m/%Y')}"

            costo = f" (€{d.estimated_cost})" if d.estimated_cost else ""
            out.append(
                f"• <b>{d.get_deadline_type_display()}</b> {costo} - {d.vehicle.model} ({d.vehicle.plate})\n  {stato}\n"
            )
        return "\n".join(out)

    elif "spese" in cmd:
        vehicles = user.vehicles.all()
        if not vehicles.exists():
            return "Nessun veicolo trovato su cui calcolare le spese."

        out = ["💶 <b>Riepilogo Spese Garage:</b>\n"]
        totale_globale = 0.0
        for v in vehicles:
            tot = float(v.total_expenses)
            totale_globale += tot
            out.append(f"• <b>{v.model}</b> ({v.plate}): € {tot:.2f}")

        out.append(f"\n<b>Totale complessivo garage:</b> € {totale_globale:.2f}")
        return "\n".join(out)

    else:
        return (
            "Comando non riconosciuto.\n"
            "Scrivi <code>garage</code>, <code>scadenze</code> o <code>spese</code>."
        )


@csrf_exempt
def telegram_webhook(request):
    """Endpoint per Telegram Webhook."""
    if request.method == "GET":
        return HttpResponse("Telegram Webhook Endpoint Active", status=200)

    if request.method == "POST":
        try:
            body = request.body.decode("utf-8")
            if not body:
                return JsonResponse({"status": "empty body"}, status=200)

            data = json.loads(body)
            msg = data.get("message") or data.get("edited_message")

            if msg:
                chat_id = msg.get("chat", {}).get("id")
                from_user = msg.get("from", {})
                user_id_str = str(chat_id)
                first_name = from_user.get("first_name", "Utente")
                text = msg.get("text", "")

                if chat_id and text:
                    # Ottieni o crea il profilo utente su Neon DB
                    user_profile, _ = UserProfile.objects.get_or_create(
                        wa_id=user_id_str,
                        defaults={"name": first_name}
                    )

                    # Elabora la risposta interrogando il database
                    risposta = handle_user_command(user_profile, text, chat_id)
                    send_message(chat_id, risposta)

            return JsonResponse({"status": "ok"}, status=200)

        except Exception as e:
            print("========================================")
            print("❌ ERRORE NEL WEBHOOK DI TELEGRAM:")
            print(traceback.format_exc())
            print("========================================")
            return JsonResponse({"status": "error", "message": str(e)}, status=200)

    return HttpResponse("Metodo non consentito", status=405)


@csrf_exempt
def vercel_cron_check_deadlines(request):
    """Endpoint per il controllo automatico notturno delle scadenze via Vercel Cron."""
    try:
        today = date.today()
        avviso_limite = today + timedelta(days=7)

        # Cerca scadenze nei prossimi 7 giorni non pagate
        upcoming = Deadline.objects.filter(
            is_paid=False, due_date__range=[today, avviso_limite]
        ).select_related("vehicle", "vehicle__user")

        for d in upcoming:
            chat_id = d.vehicle.user.wa_id
            msg = (
                f"🔔 <b>Promemoria Scadenza Imminente!</b>\n\n"
                f"Veicolo: <b>{d.vehicle.model}</b> ({d.vehicle.plate})\n"
                f"Tipo: {d.get_deadline_type_display()}\n"
                f"Data: {d.due_date.strftime('%d/%m/%Y')}"
            )
            send_message(chat_id, msg)

        return JsonResponse(
            {"status": "ok", "checked": upcoming.count()}, status=200
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)