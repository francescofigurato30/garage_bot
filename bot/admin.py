from django.contrib import admin
from .models import UserProfile, Vehicle, Deadline, Expense

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('wa_id', 'name', 'state')
    search_fields = ('wa_id', 'name')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('plate', 'model', 'vehicle_type', 'registration_year', 'display_expenses')
    list_filter = ('vehicle_type',)
    search_fields = ('plate', 'model')

    def display_expenses(self, obj):
        return f"€{obj.total_expenses:.2f}"
    display_expenses.short_description = "Totale Spese"

@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'deadline_type', 'due_date', 'is_paid')
    list_filter = ('deadline_type', 'is_paid')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'amount', 'expense_type', 'date', 'description')
    list_filter = ('expense_type', 'date')
    search_fields = ('vehicle__plate', 'description')