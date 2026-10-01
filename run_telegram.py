import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from bot.engine import handle_incoming_message

BOT_TOKEN = os.getenv("8644857704:AAELOp6ZC5dACla9l_aYxkBhL9wY7UvVuS0")

# Mini server HTTP per ingannare Render Free Web Service
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"GarageBot is running!")

    def log_message(self, format, *args):
        return  # Silenzia i log di ping

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name or "Utente"
    user_text = update.message.text

    reply = await sync_to_async(handle_incoming_message, thread_sensitive=True)(
        wa_id=user_id,
        text=user_text,
        user_name=user_name
    )
    await update.message.reply_text(reply, parse_mode='Markdown')

def main():
    # Avvia il server web in un thread separato
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.COMMAND, on_message))

    print("🤖 GarageBot Telegram avviato e in ascolto...")
    app.run_polling()

if __name__ == '__main__':
    main()