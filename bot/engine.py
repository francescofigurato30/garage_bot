from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from .models import UserProfile, Vehicle, Deadline, Expense

def get_status_indicator(due_status):
    """ Calcola il semaforo in base ai giorni mancanti alla scadenza"""
    today = date.today()
    delta = (due_date  - today).days
    if delta < 0:
        return f"🔴 Scaduto da{abs(delta)}gg"
    elif delta <= 30:
        return f"🟡 Tra {delta}gg"
    return f"🟢 Tra {delta}gg"

def format_garage(user):
    """Genera la vista del Garage con stato storico e totale spese."""
    vehicles = user.vehicles.prefetch_related('deadlines', 'expenses').all()
    if not vehicles.exists():
        return (
            "🚗🏍️ *Il tuo Garage Digitale è vuoto!*\n\n"
            "Non hai ancora registrato nessun mezzo.\n"
            "Scrivi *aggiungi* per inserire la tua prima auto o moto."
        )

    msg = "🚗🏍️ *Il tuo Garage Digitale*\n\n"
    for idx, v in enumerate(vehicles, 1):
        icon = "🏍️" if v.vehicle_type == 'MOTO' else "🚗"
        msg += f"*{idx}. {icon} {v.model}* (`{v.plate}`)\n"
        
        if v.registration_year:
            msg += f"   🏛️ _Anno {v.registration_year}:_ {v.historical_status}\n"

        total_spent = v.total_expenses
        msg += f"   💰 _Spese registrate:_ *€{total_spent:.2f}*\n"

        deadlines = v.deadlines.all().order_by('due_date')
        if not deadlines:
            msg += "   └ Nessuna scadenza impostata\n"
        else:
            for d in deadlines:
                if d.deadline_type == 'INSURANCE':
                    tipo = "🛡️ Polizza"
                elif d.deadline_type == 'TAX':
                    tipo = "🏷️️ Bollo"
                else:
                    tipo = "🔧 Revisione"
                status = get_status_indicator(d.due_date)
                msg += f"   ├ {tipo}: {d.due_date.strftime('%d/%m/%Y')} ({status})\n"
        msg += "\n"

    msg += "💡 Scrivi *aiuto* per vedere l'elenco dei comandi disponibili."
    return msg

def get_help_message():
    return (
        "🤖 *Comandi GarageBot:*\n\n"
        "• *garage* ➔ Mostra tutti i veicoli, scadenze e totale spese\n"
        "• *aggiungi* ➔ Registra un nuovo veicolo (auto o moto)\n"
        "• *anno <targa> <anno>* ➔ Imposta l'anno (es. `anno AB123CD 2003`)\n"
        "• *spesa <targa> <importo> <descrizione>* ➔ Registra una spesa\n"
        "• *spese <targa>* ➔ Mostra lo storico spese del mezzo\n"
        "• *rinnova <targa> <tipo>* ➔ Sposta avanti la scadenza\n"
        "• *elimina <targa>* ➔ Cancella un mezzo\n"
        "• *aiuto* ➔ Mostra questo messaggio"
    )

def handle_expense_add(user, plate_arg, amount_str, desc_arg):
    plate_clean = plate_arg.upper().replace(" ", "")
    v = user.vehicles.filter(plate=plate_clean).first()
    if not v:
        return f"⚠️ Nessun veicolo trovato con targa `{plate_clean}`."

    try:
        amount_clean = amount_str.replace("€", "").replace(",", ".").strip()
        amount = Decimal(amount_clean)
        if amount <= 0:
            return "⚠️ L'importo deve essere maggiore di zero."
    except (InvalidOperation, ValueError):
        return f"⚠️ Importo non valido: `{amount_str}`. Usa numeri tipo `120` o `45.50`."

    description = desc_arg.strip() if desc_arg else "Spesa generica"
    Expense.objects.create(vehicle=v, amount=amount, description=description, date=date.today())

    return (
        f"💸 *Spesa registrata con successo!*\n\n"
        f"Mezzo: *{v.model}* (`{v.plate}`)\n"
        f"Importo: *€{amount:.2f}*\n"
        f"Dettaglio: _{description}_\n\n"
        f"💰 *Totale speso finora per questo mezzo:* *€{v.total_expenses:.2f}*"
    )

def handle_expenses_list(user, plate_arg):
    plate_clean = plate_arg.upper().replace(" ", "")
    v = user.vehicles.filter(plate=plate_clean).first()
    if not v:
        return f"⚠️ Nessun veicolo trovato con targa `{plate_clean}`."

    expenses = v.expenses.all().order_by('-date', '-created_at')
    if not expenses.exists():
        return f"ℹ️ Nessuna spesa registrata per *{v.model}* (`{plate_clean}`)."

    msg = f"🧾 *Storico Spese per {v.model}* (`{plate_clean}`)\n\n"
    for e in expenses:
        msg += f"• *€{e.amount:.2f}* - {e.date.strftime('%d/%m/%Y')} ➔ _{e.description}_\n"
    msg += f"\n💰 *Totale complessivo:* *€{v.total_expenses:.2f}*"
    return msg

def handle_set_year(user, plate_arg, year_str):
    plate_clean = plate_arg.upper().replace(" ", "")
    v = user.vehicles.filter(plate=plate_clean).first()
    if not v:
        return f"⚠️ Nessun veicolo trovato con targa `{plate_clean}`."

    if not year_str.isdigit() or len(year_str) != 4:
        return "⚠️ Inserisci un anno valido a 4 cifre (es. `2003`)."

    reg_year = int(year_str)
    current_year = date.today().year
    if reg_year < 1900 or reg_year > current_year + 1:
        return f"⚠️ Anno non valido (deve essere tra 1900 e {current_year})."

    v.registration_year = reg_year
    v.save()
    return (
        f"🗓️ *Anno aggiornato per {v.model}* (`{plate_clean}`): *{reg_year}*\n\n"
        f"🏛️ *Stato storico:* {v.historical_status}"
    )

def handle_renew(user, plate_arg, kind_arg):
    plate_clean = plate_arg.upper().replace(" ", "")
    v = user.vehicles.filter(plate=plate_clean).first()
    if not v:
        return f"⚠️ Nessun veicolo trovato con targa `{plate_clean}`."

    if 'bollo' in kind_arg:
        deadline_type = 'TAX'
        years_to_add = 1
        label = "Bollo"
    elif 'polizza' in kind_arg or 'ass' in kind_arg:
        deadline_type = 'INSURANCE'
        years_to_add = 1
        label = "Polizza assicurativa"
    elif 'rev' in kind_arg:
        deadline_type = 'NOT'
        years_to_add = 2
        label = "Revisione ministeriale"
    else:
        return "⚠️ Specifica cosa rinnovare: *bollo*, *polizza* o *revisione*."

    deadline = v.deadlines.filter(deadline_type=deadline_type).first()
    if not deadline:
        return f"⚠️ Nessuna scadenza registrata per `{label}` sul veicolo `{plate_clean}`."

    old_date = deadline.due_date
    try:
        new_date = date(old_date.year + years_to_add, old_date.month, old_date.day)
    except ValueError:
        new_date = date(old_date.year + years_to_add, old_date.month, old_date.day - 1)

    deadline.due_date = new_date
    deadline.is_paid = True
    deadline.save()

    return (
        f"✅ *{label} rinnovato!*\n\n"
        f"Mezzo: *{v.model}* (`{v.plate}`)\n"
        f"Nuova scadenza: *{new_date.strftime('%d/%m/%Y')}* 🟢\n\n"
        + format_garage(user)
    )

def handle_delete(user, plate_arg):
    plate_clean = plate_arg.upper().replace(" ", "")
    v = user.vehicles.filter(plate=plate_clean).first()
    if not v:
        return f"⚠️ Nessun veicolo trovato con targa `{plate_clean}`."

    model_name = v.model
    v.delete()
    return f"🗑️ *{model_name}* (`{plate_clean}`) è stato rimosso.\n\n" + format_garage(user)

def handle_incoming_message(wa_id, text, user_name="Utente"):
    user, _ = UserProfile.objects.get_or_create(wa_id=wa_id, defaults={'name': user_name})
    clean_text = text.strip()
    cmd = clean_text.lower().strip('*_~')

    if cmd in ['aiuto', 'help', 'info', '/help', '/aiuto']:
        return get_help_message()

    if cmd in ['garage', 'menu', 'ciao', 'start', '/start', '/garage']:
        user.state = 'IDLE'
        user.save()
        return format_garage(user)

    if cmd.startswith("elimina"):
        parts = clean_text.split()
        if len(parts) >= 2:
            return handle_delete(user, parts[1])
        return "⚠️ Specifica la targa: `elimina AB123CD`"

    if cmd.startswith("rinnova"):
        parts = clean_text.split()
        if len(parts) >= 3:
            return handle_renew(user, parts[1], parts[2].lower())
        return "⚠️ Formato: `rinnova <targa> <bollo/polizza/revisione>`"

    if cmd.startswith("anno"):
        parts = clean_text.split()
        if len(parts) >= 3:
            return handle_set_year(user, parts[1], parts[2])
        return "⚠️ Formato: `anno <targa> <anno>` (es. `anno AB123CD 2003`)"

    if cmd.startswith("spese"):
        parts = clean_text.split()
        if len(parts) >= 2:
            return handle_expenses_list(user, parts[1])
        return "⚠️ Formato: `spese <targa>`"

    if cmd.startswith("spesa"):
        parts = clean_text.split(maxsplit=3)
        if len(parts) >= 3:
            return handle_expense_add(user, parts[1], parts[2], parts[3] if len(parts) > 3 else "")
        return "⚠️ Formato: `spesa <targa> <importo> <descrizione>`"

    if cmd in ['aggiungi', '/aggiungi']:
        user.state = 'AWAITING_TYPE'
        user.temp_data = {}
        user.save()
        return (
            "➕ *Nuovo Veicolo (Passo 1/5)*\n\n"
            "Che tipo di veicolo vuoi registrare?\n"
            "Rispondi con: *AUTO*, *MOTO* o *ALTRO*"
        )

    if user.state == 'AWAITING_TYPE':
        choice = cmd.upper()
        if choice in ['AUTO', 'MOTO', 'ALTRO']:
            user.temp_data['vehicle_type'] = choice
            user.state = 'AWAITING_PLATE_MODEL'
            user.save()
            return (
                f"Hai scelto: *{choice}*\n\n"
                "📝 *Passo 2/5: Targa e Modello*\n"
                "Scrivi la targa, il modello e facoltativamente l'anno separati da virgola.\n"
                "_Esempio:_ `AB123CD, Mercedes C220, 2003`"
            )
        return "⚠️ Scelta non valida. Rispondi con *AUTO*, *MOTO* o *ALTRO*."

    if user.state == 'AWAITING_PLATE_MODEL':
        if ',' in clean_text:
            parts = [p.strip() for p in clean_text.split(',')]
            plate = parts[0].upper().replace(" ", "")
            model = parts[1]
            reg_year = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None

            user.temp_data['plate'] = plate
            user.temp_data['model'] = model
            if reg_year:
                user.temp_data['registration_year'] = reg_year

            user.state = 'AWAITING_INSURANCE'
            user.save()
            return (
                f"✅ Registrato: *{model}* (`{plate}`)\n\n"
                "🛡️ *Passo 3/5: Assicurazione*\n"
                "Inserisci scadenza in formato *GG/MM/AAAA* (oppure scrivi *salta*)."
            )
        return "⚠️ Separa i campi con una virgola (es. `AB123CD, Ford Focus`)."

    if user.state == 'AWAITING_INSURANCE':
        if cmd != 'salta':
            try:
                parsed_date = datetime.strptime(clean_text, "%d/%m/%Y").date()
                user.temp_data['ins_date'] = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                return "⚠️️ Formato errato. Usa *GG/MM/AAAA* (es. `20/10/2026`) o *salta*."

        user.state = 'AWAITING_TAX'
        user.save()
        return "🏷️ *Passo 4/5: Bollo*\nInserisci data *GG/MM/AAAA* o scrivi *salta*."

    if user.state == 'AWAITING_TAX':
        if cmd != 'salta':
            try:
                tax_date = datetime.strptime(clean_text, "%d/%m/%Y").date()
                user.temp_data['tax_date'] = tax_date.strftime("%Y-%m-%d")
            except ValueError:
                return "⚠️ Formato errato. Usa *GG/MM/AAAA* o *salta*."

        user.state = 'AWAITING_MOT'
        user.save()
        return "🔧 *Passo 5/5: Revisione*\nInserisci data *GG/MM/AAAA* o scrivi *salta*."

    if user.state == 'AWAITING_MOT':
        mot_date = None
        if cmd != 'salta':
            try:
                mot_date = datetime.strptime(clean_text, "%d/%m/%Y").date()
            except ValueError:
                return "⚠️ Formato errato. Usa *GG/MM/AAAA* o *salta*."

        temp = user.temp_data
        vehicle = Vehicle.objects.create(
            user=user,
            plate=temp.get('plate', 'SCONOSCIUTA'),
            model=temp.get('model', 'Veicolo'),
            vehicle_type=temp.get('vehicle_type', 'AUTO'),
            registration_year=temp.get('registration_year')
        )

        if 'ins_date' in temp:
            try:
                d = datetime.strptime(temp['ins_date'], "%Y-%m-%d").date()
                Deadline.objects.create(vehicle=vehicle, deadline_type='INSURANCE', due_date=d)
            except (ValueError, TypeError):
                pass

        if 'tax_date' in temp:
            try:
                d = datetime.strptime(temp['tax_date'], "%Y-%m-%d").date()
                Deadline.objects.create(vehicle=vehicle, deadline_type='TAX', due_date=d)
            except (ValueError, TypeError):
                pass

        if mot_date:
            Deadline.objects.create(vehicle=vehicle, deadline_type='NOT', due_date=mot_date)

        user.state = 'IDLE'
        user.temp_data = {}
        user.save()

        return f"🎉 *{vehicle.model}* registrato con successo!\n\n" + format_garage(user)

    return "Non ho capito il comando. 🤔 Scrivi *garage* o *aiuto*."