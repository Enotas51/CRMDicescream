from django.contrib import admin

from .models import FinanceCategory, ReserveTransfer, Transaction, UtilitiesOperation

admin.site.register(FinanceCategory)
admin.site.register(Transaction)
admin.site.register(ReserveTransfer)
admin.site.register(UtilitiesOperation)
