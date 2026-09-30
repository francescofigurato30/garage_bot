import uuid
from datetime import date
from django.db import models
from django.db.models import Sum


class UserProfile(models.Model):
    wa_id = models.CharField(max_length=50, unique=True, help_text="Identificativo utente (Telegram ID / WhatsApp)")
    name = models.CharField(max_length=150, blank=True, null=True)
    state = models.CharField(max_length=30, default='IDLE')
    temp_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.name or 'Utente'} ({self.wa_id})"


class Vehicle(models.Model):
    TYPES = [
        ('AUTO', 'Auto'),
        ('MOTO', 'Moto'),
        ('ALTRO', 'Altro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='vehicles')
    plate = models.CharField(max_length=15)
    model = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=10, choices=TYPES, default='AUTO')
    registration_year = models.PositiveIntegerField(null=True, blank=True, help_text="Anno di immatricolazione")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'plate')

    @property
    def age(self):
        """Calcola l'età del veicolo in anni."""
        if not self.registration_year:
            return None
        return date.today().year - self.registration_year

    @property
    def historical_status(self):
        """Determina lo stato storico e le relative agevolazioni."""
        age = self.age
        if age is None:
            return "Anno non specificato"
        if age >= 30:
            return f"🏛️ Storico Ultra-30enne ({age} anni) - Esente bollo ordinario"
        elif age >= 20:
            return f"🎖️ Storico Ventennale ({age} anni) - Bollo ridotto 50% con CRS"
        elif age == 19:
            return f"⏳ Diventa storico il prossimo anno ({age} anni)"
        else:
            return f"Standard ({age} anni, mancano {20 - age} anni ai 20)"

    @property
    def total_expenses(self):
        """Calcola la somma totale spesa per questo veicolo."""
        total = self.expenses.aggregate(total=Sum('amount'))['total']
        return total or 0.0

    def __str__(self):
        return f"{self.model} ({self.plate})"


class Deadline(models.Model):
    TYPES = [
        ('INSURANCE', 'Assicurazione'),
        ('TAX', 'Bollo'),
        ('NOT', 'Revisione'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='deadlines')
    deadline_type = models.CharField(max_length=20, choices=TYPES)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    # Importo opzionale per associare subito il costo della scadenza (es. preventivo polizza o bollo)
    estimated_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.deadline_type} - {self.vehicle.plate} ({self.due_date})"


class Expense(models.Model):
    EXPENSE_TYPES = [
        ('INSURANCE', 'Assicurazione'),
        ('TAX', 'Bollo'),
        ('NOT', 'Revisione'),
        ('MAINTENANCE', 'Tagliando / Manutenzione'),
        ('REPAIR', 'Riparazione'),
        ('PARTS', 'Ricambi / Accessori'),
        ('FUEL', 'Carburante'),
        ('OTHER', 'Altro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='expenses')
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPES, default='MAINTENANCE')
    amount = models.DecimalField(max_digits=8, decimal_places=2, help_text="Costo in Euro (€)")
    date = models.DateField(default=date.today)
    description = models.CharField(max_length=200, blank=True, help_text="Es. Cambio gomme, scarico, pastiglie freni")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.vehicle.plate} - €{self.amount} ({self.get_expense_type_display()})"