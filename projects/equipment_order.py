from django.db import transaction
from django.utils import timezone

from finance.balances import compute_finance_balances
from finance.models import Transaction, TransactionType

from .models import ProjectEquipment


class InsufficientBalanceError(Exception):
  def __init__(self, available, required):
    self.available = available
    self.required = required
    super().__init__(
      f'Недостаточно средств на балансе. Доступно: {available} ₽, нужно: {required} ₽.',
    )


@transaction.atomic
def charge_equipment_order(equipment, user):
  if equipment.order_transaction_id:
    return equipment.order_transaction

  amount = equipment.total_price
  if amount <= 0:
    raise ValueError('Сумма заказа должна быть больше нуля.')

  balances = compute_finance_balances()
  if amount > balances['main_balance']:
    raise InsufficientBalanceError(balances['main_balance'], amount)

  tx = Transaction.objects.create(
    title=f'Заказ: {equipment.name[:200]}',
    amount=amount,
    transaction_type=TransactionType.EXPENSE,
    project=equipment.project,
    date=timezone.localdate(),
    created_by=user,
    notes=f'Оборудование проекта «{equipment.project.name}»',
  )
  equipment.order_transaction = tx
  equipment.save(update_fields=['order_transaction'])
  return tx
