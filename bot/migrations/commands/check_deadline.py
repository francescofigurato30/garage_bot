import os
import asyncio
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from telegram import Bot
from bot.models import Deadline

class Command(BaseCommand):
    help = "Controlla le scadenze imminenti e invia i promemoria su Telegram"

    def handle(self, *args, **options):
        # 1. Recupera il token dalla variabile d'ambiente corretta
        bot_token = os.getenv("8644857704:AAELOp6ZC5dACla9I_aYxkBhL9wY7UvVuS0")
        if not bot_token:
            self.stdout.write(self.style.ERROR("ERRORE: TELEGRAM_BOT_TOKEN non trovato nelle variabili d'ambiente."))
            return

        bot = Bot(token=bot_token)
        today = date.today()
        alert_windows = [0, 7, 15, 30]

        self.stdout.write(self.style.NOTICE(f"🔍 Controllo scadenze in data odierna: {today.strftime('%d/%m/%Y')}"))
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

                # Invio effettivo del messaggio su Telegram all'utente
                chat_id = user.wa_id
                try:
                    asyncio.run(bot.send_message(chat_id=chat_id, text=alert_text, parse_mode="Markdown"))
                    self.stdout.write(self.style.SUCCESS(f"✅ Notifica inviata a {chat_id} ({v.plate} - {tipo})"))
                    notifications_sent += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Errore invio a {chat_id}: {e}"))

        if notifications_sent == 0:
            self.stdout.write(self.style.WARNING("Nessuna scadenza critica rilevata per le finestre 0, 7, 15 o 30 giorni."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Operazione conclusa: {notifications_sent} notifiche inviate."))