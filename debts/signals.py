from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from finance.models import Transaction, TransactionType
from finance.utilities import sync_utilities_from_repayment


@receiver(post_save, sender=Transaction)
def update_debt_after_transaction_save(sender, instance, **kwargs):
  if instance.transaction_type == TransactionType.DEBT_REPAYMENT and instance.debt_id:
    instance.debt.refresh_status()
    sync_utilities_from_repayment(instance)
    if instance.utilities_portion is not None:
      Transaction.objects.filter(pk=instance.pk).update(
        utilities_portion=instance.utilities_portion,
      )


@receiver(post_delete, sender=Transaction)
def update_debt_after_transaction_delete(sender, instance, **kwargs):
  if instance.debt_id:
    try:
      from debts.models import Debt
      debt = Debt.objects.get(pk=instance.debt_id)
      debt.refresh_status()
    except Debt.DoesNotExist:
      pass
