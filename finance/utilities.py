from decimal import Decimal

from django.db.models import Sum

from .models import (
  UtilitiesOperation,
  UtilitiesOperationType,
  UtilitiesSource,
)


def compute_utilities_balance(exclude_pk=None):
  qs = UtilitiesOperation.objects.all()
  if exclude_pk:
    qs = qs.exclude(pk=exclude_pk)

  deposits = qs.filter(
    operation_type=UtilitiesOperationType.DEPOSIT,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  expenses = qs.filter(
    operation_type=UtilitiesOperationType.EXPENSE,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  from_debt = qs.filter(
    operation_type=UtilitiesOperationType.DEPOSIT,
    source=UtilitiesSource.DEBT,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  from_external = qs.filter(
    operation_type=UtilitiesOperationType.DEPOSIT,
    source=UtilitiesSource.EXTERNAL,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  return {
    'balance': deposits - expenses,
    'deposits': deposits,
    'expenses': expenses,
    'from_debt': from_debt,
    'from_external': from_external,
  }


def get_debt_utilities_credited(debt, exclude_repayment_pk=None):
  qs = UtilitiesOperation.objects.filter(
    debt=debt,
    source=UtilitiesSource.DEBT,
    operation_type=UtilitiesOperationType.DEPOSIT,
  )
  if exclude_repayment_pk:
    qs = qs.exclude(repayment_id=exclude_repayment_pk)
  return qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')


def calculate_utilities_portion(debt, payment_amount, exclude_repayment_pk=None, skip=False):
  """Фиксированная сумма с каждого погашения (не часть долга, без общего лимита)."""
  if skip or not debt.utilities_amount or debt.utilities_amount <= 0:
    return Decimal('0')
  return min(debt.utilities_amount, payment_amount)


def sync_utilities_from_repayment(transaction):
  from finance.models import TransactionType

  if transaction.transaction_type != TransactionType.DEBT_REPAYMENT or not transaction.debt_id:
    UtilitiesOperation.objects.filter(repayment=transaction).delete()
    transaction.utilities_portion = Decimal('0')
    return

  debt = transaction.debt
  portion = calculate_utilities_portion(
    debt,
    transaction.amount,
    exclude_repayment_pk=transaction.pk,
    skip=transaction.skip_utilities,
  )
  transaction.utilities_portion = portion

  if portion > 0:
    op, _ = UtilitiesOperation.objects.update_or_create(
      repayment=transaction,
      defaults={
        'title': f'Коммунальные: погашение «{debt.title}»',
        'amount': portion,
        'operation_type': UtilitiesOperationType.DEPOSIT,
        'source': UtilitiesSource.DEBT,
        'debt': debt,
        'date': transaction.date,
        'notes': transaction.notes,
        'created_by': transaction.created_by,
      },
    )
    if not op.created_by_id and transaction.created_by_id:
      op.created_by = transaction.created_by
      op.save(update_fields=['created_by'])
  else:
    UtilitiesOperation.objects.filter(repayment=transaction).delete()
