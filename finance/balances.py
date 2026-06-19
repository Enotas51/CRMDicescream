from decimal import Decimal

from django.db.models import Sum

from .models import (
  ReserveDirection,
  ReserveSource,
  ReserveTransfer,
  Transaction,
  TransactionType,
)


def compute_finance_balances(exclude_reserve_pk=None):
  income = Transaction.objects.filter(
    transaction_type=TransactionType.INCOME,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  expense = Transaction.objects.filter(
    transaction_type=TransactionType.EXPENSE,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  reserve_qs = ReserveTransfer.objects.all()
  if exclude_reserve_pk:
    reserve_qs = reserve_qs.exclude(pk=exclude_reserve_pk)

  to_reserve = reserve_qs.filter(
    direction=ReserveDirection.TO_RESERVE,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  to_reserve_from_balance = reserve_qs.filter(
    direction=ReserveDirection.TO_RESERVE,
    source=ReserveSource.BALANCE,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  to_reserve_external = reserve_qs.filter(
    direction=ReserveDirection.TO_RESERVE,
    source=ReserveSource.EXTERNAL,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  from_reserve = reserve_qs.filter(
    direction=ReserveDirection.FROM_RESERVE,
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  reserve_balance = to_reserve - from_reserve
  main_balance = income - expense - to_reserve_from_balance + from_reserve

  return {
    'income': income,
    'expense': expense,
    'main_balance': main_balance,
    'reserve_balance': reserve_balance,
    'to_reserve_from_balance': to_reserve_from_balance,
    'to_reserve_external': to_reserve_external,
    'from_reserve': from_reserve,
  }
