from django.contrib import admin
from django.urls import path
from bot.views import telegram_webhook, vercel_cron_check_deadlines

urlpatterns = [
    path('admin/', admin.site.urls),
    path('telegram/webhook/', telegram_webhook, name='telegram_webhook'),
    path('cron/check-deadlines/', vercel_cron_check_deadlines, name='cron_check_deadlines'),
]