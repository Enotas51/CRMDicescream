from django.contrib import admin

from .models import Debt, DebtDebtor


class DebtDebtorInline(admin.TabularInline):
  model = DebtDebtor
  extra = 1


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
  list_display = ('title', 'amount', 'status', 'creditor_name', 'due_date')
  list_filter = ('status',)
  inlines = [DebtDebtorInline]


@admin.register(DebtDebtor)
class DebtDebtorAdmin(admin.ModelAdmin):
  list_display = ('debt', 'debtor_name', 'amount')
