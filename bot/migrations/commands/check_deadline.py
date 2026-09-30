from datetime import date, timedelta
from django.core.management.base import BaseCommand
from bot.models import Deadline

class Command(BaseCommand):
    help = "Controlla le scadenze imminenti e prepara i promemoria"

    def handle(self, *args, **options):
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
                    f"🔔 [PROMEMORIA per {user.name or user.wa_id}]\n"
                    f"Il tuo mezzo *{v.model}* (`{v.plate}`) ha la seguente scadenza:\n"
                    f"👉 *{tipo}*: {urgency}\n"
                    f"Per aggiornare scrivi: `rinnova {v.plate} {cmd_tipo}`"
                )

                self.stdout.write(self.style.SUCCESS(f"\n[NOTIFICA DA INVIARE]:\n{alert_text}\n"))
                notifications_sent += 1

        if notifications_sent == 0:
            self.stdout.write(self.style.WARNING("Nessuna scadenza critica rilevata per le finestre 0, 7, 15 o 30 giorni."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Controllo completato: {notifications_sent} notifiche pronte."))