import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from bot.engine import handle_incoming_message

BOT_TOKEN = "8644857704:AAELOp6ZC5dACla9I_aYxkBhL9wY7UvVuS0"

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.COMMAND, on_message))

    print("🤖 GarageBot Telegram avviato e in ascolto...")
    app.run_polling()

if __name__ == '__main__':
    main()