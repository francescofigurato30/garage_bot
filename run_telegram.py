import os
import django
from datetime import date, time
import pytz

# 1. Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from bot.engine import handle_incoming_message
from bot.models import Deadline

BOT_TOKEN = os.getenv("8644857704:AAELOp6ZC5dACla9l_aYxkBhL9wY7UvVuS0")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi in arrivo degli utenti."""
    if not update.message or not update.message.text:
        return

    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name or "Utente"
    user_text = update.message.text

    print(f"📩 Ricevuto messaggio da {user_name} ({user_id}): {user_text}")

    reply = await sync_to_async(handle_incoming_message, thread_sensitive=True)(
        wa_id=user_id,
        text=user_text,
        user_name=user_name
    )

    await update.message.reply_text(reply, parse_mode='Markdown')

def get_due_notifications():
    """Funzione sincrona per verificare le scadenze su DB."""
    today = date.today()
    target_deltas = [30, 15, 7, 3, 1, 0]
    deadlines = Deadline.objects.filter(is_paid=False).select_related('vehicle__user')

    notifications = []
    for d in deadlines:
        delta = (d.due_date - today).days
        if delta in target_deltas:
            chat_id = d.vehicle.user.wa_id
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
            notifications.append((chat_id, msg))
    return notifications

async def daily_deadline_job(context: ContextTypes.DEFAULT_TYPE):
    """Task pianificata eseguita ogni mattina alle 08:30 italiane."""
    print("⏰ Esecuzione controllo scadenze mattutino...")
    notifications = await sync_to_async(get_due_notifications, thread_sensitive=True)()

    for chat_id, msg in notifications:
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            print(f"✅ Notifica inviata a {chat_id}")
        except Exception as e:
            print(f"⚠️ Errore invio a {chat_id}: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Gestione comandi e testo
    app.add_handler(MessageHandler(filters.TEXT | filters.COMMAND, on_message))

    # Controllo scadenze automatico programmato ogni giorno alle 08:30 (fuso Roma)
    timezone_it = pytz.timezone('Europe/Rome')
    run_time = time(hour=8, minute=30, tzinfo=timezone_it)
    app.job_queue.run_daily(daily_deadline_job, time=run_time)

    print("🤖 GarageBot Telegram avviato e in ascolto (con scheduler attivo)...")
    app.run_polling()

if __name__ == '__main__':
    main()