import asyncio
from datetime import date
from django.core.management.base import BaseCommand
from telegram import Bot
from bot.models import Deadline

BOT_TOKEN = "IL_TUO_TOKEN_TELEGRAM"

class Command(BaseCommand):
    help = "Verifica le scadenze e invia notifiche preventive su Telegram."

    def handle(self, *args, **options):
        today = date.today()
        target_deltas = [30, 15, 7, 3, 1, 0]

        # 1. Query ed estrazione dati eseguite in contesto sincrono puro
        deadlines = Deadline.objects.filter(is_paid=False).select_related('vehicle__user')
        
        pending_notifications = []
        for d in deadlines:
            delta = (d.due_date - today).days
            if delta in target_deltas:
                user = d.vehicle.user
                chat_id = user.wa_id

                if delta == 0:
                    status_text = "🚨 *SCADE OGGI!*"
                else:
                    status_text = f"⚠️ *Scade tra {delta} giorni* ({d.due_date.strftime('%d/%m/%Y')})"

                tipo = d.get_deadline_type_display()
                msg = (
                    f"🔔 *PROMEMORIA SCADENZA GARAGE*\n\n"
                    f"Il tuo veicolo *{d.vehicle.model}* (`{d.vehicle.plate}`) ha una scadenza imminente:\n"
                    f"• *Tipo:* {tipo}\n"
                    f"• *Stato:* {status_text}\n\n"
                    f"💡 Quando hai pagato, rispondi con:\n"
                    f"`rinnova {d.vehicle.plate} {tipo.lower()}`"
                )
                pending_notifications.append((chat_id, msg))

        if not pending_notifications:
            self.stdout.write(self.style.NOTICE("Nessuna scadenza coincidente con i giorni di preavviso oggi."))
            return

        # 2. Invio asincrono tramite Telegram
        asyncio.run(self.send_notifications(pending_notifications))

    async def send_notifications(self, notifications):
        bot = Bot(token=BOT_TOKEN)
        sent_count = 0

        for chat_id, msg in notifications:
            try:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
                sent_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Errore invio a {chat_id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Controllo completato: inviate {sent_count} notifiche."))