from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model

from debts.models import Debt, DebtDebtor, DebtStatus
from .balances import compute_finance_balances
from .models import (
  FinanceCategory,
  ReserveDirection,
  ReserveSource,
  ReserveTransfer,
  Transaction,
  TransactionType,
  UtilitiesOperation,
  UtilitiesOperationType,
  UtilitiesSource,
)
from .utilities import calculate_utilities_portion, sync_utilities_from_repayment

User = get_user_model()


class FinanceCategoryForm(forms.ModelForm):
  class Meta:
    model = FinanceCategory
    fields = ['name', 'transaction_type', 'color']
    widgets = {
      'name': forms.TextInput(attrs={'class': 'form-control'}),
      'transaction_type': forms.Select(attrs={'class': 'form-select'}),
      'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
    }
    labels = {
      'name': 'Название',
      'transaction_type': 'Тип',
      'color': 'Цвет',
    }


class TransactionForm(forms.ModelForm):
  class Meta:
    model = Transaction
    fields = [
      'title', 'amount', 'transaction_type',
      'project', 'debt', 'debt_debtor', 'skip_utilities',
      'date', 'notes',
    ]
    widgets = {
      'title': forms.TextInput(attrs={'class': 'form-control'}),
      'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
      'transaction_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_transaction_type'}),
      'project': forms.Select(attrs={'class': 'form-select'}),
      'debt': forms.Select(attrs={'class': 'form-select', 'id': 'id_debt'}),
      'debt_debtor': forms.Select(attrs={'class': 'form-select', 'id': 'id_debt_debtor'}),
      'skip_utilities': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_skip_utilities'}),
      'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
      'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    }
    labels = {
      'title': 'Название',
      'amount': 'Сумма',
      'transaction_type': 'Тип',
      'project': 'Проект',
      'debt': 'Задолженность',
      'debt_debtor': 'Должник',
      'skip_utilities': 'Не удерживать коммунальные',
      'date': 'Дата',
      'notes': 'Заметки',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['debt'].queryset = Debt.objects.exclude(
      status__in=[DebtStatus.CLOSED, DebtStatus.CANCELLED],
    ).order_by('-created_at')
    self.fields['debt'].required = False
    self.fields['debt'].empty_label = '— выберите задолженность —'
    self.fields['debt_debtor'].queryset = DebtDebtor.objects.none()
    self.fields['debt_debtor'].required = False
    self.fields['debt_debtor'].empty_label = '— выберите должника —'
    self.fields['skip_utilities'].required = False

    if self.instance.pk and self.instance.transaction_type != TransactionType.DEBT_REPAYMENT:
      self.fields['skip_utilities'].widget = forms.HiddenInput()

    debt_id = None
    if self.data.get('debt'):
      debt_id = self.data.get('debt')
    elif self.instance.pk and self.instance.debt_id:
      debt_id = self.instance.debt_id
    elif self.initial.get('debt'):
      debt_id = self.initial.get('debt')

    if debt_id:
      self.fields['debt_debtor'].queryset = DebtDebtor.objects.filter(
        debt_id=debt_id,
      ).select_related('debtor_user')

    if self.instance.pk and self.instance.debt_id:
      self.fields['debt'].queryset = Debt.objects.filter(
        pk=self.instance.debt_id,
      ) | self.fields['debt'].queryset

  def clean(self):
    cleaned = super().clean()
    ttype = cleaned.get('transaction_type')
    debt = cleaned.get('debt')
    amount = cleaned.get('amount')
    debt_debtor = cleaned.get('debt_debtor')
    skip_utilities = cleaned.get('skip_utilities', False)

    if ttype == TransactionType.DEBT_REPAYMENT:
      if not debt:
        self.add_error('debt', 'Выберите задолженность для погашения.')
      if not debt_debtor:
        self.add_error('debt_debtor', 'Выберите должника, который погашает долг.')
      elif debt and debt_debtor.debt_id != debt.pk:
        self.add_error('debt_debtor', 'Должник не относится к выбранной задолженности.')

      if debt and debt_debtor and amount:
        utilities_portion = calculate_utilities_portion(
          debt,
          amount,
          exclude_repayment_pk=self.instance.pk if self.instance.pk else None,
          skip=skip_utilities,
        )
        debt_reduction = amount - utilities_portion
        remaining = debt_debtor.get_repaid_amount(
          exclude_repayment_pk=self.instance.pk if self.instance.pk else None,
        )
        debtor_remaining = debt_debtor.amount - remaining
        if debt_reduction > debtor_remaining:
          self.add_error(
            'amount',
            f'На погашение долга (без коммунальных) приходится {debt_reduction} ₽, '
            f'но у должника осталось {debtor_remaining} ₽.',
          )
    else:
      cleaned['debt'] = None
      cleaned['debt_debtor'] = None
      cleaned['skip_utilities'] = False

    return cleaned

  def save(self, commit=True):
    instance = super().save(commit=False)
    if instance.transaction_type == TransactionType.DEBT_REPAYMENT and instance.debt_debtor:
      instance.repaid_by_user = instance.debt_debtor.debtor_user
      instance.repaid_by_name = instance.debt_debtor.debtor_name
    elif instance.transaction_type != TransactionType.DEBT_REPAYMENT:
      instance.repaid_by_user = None
      instance.repaid_by_name = ''
      instance.debt_debtor = None
      instance.skip_utilities = False
    if commit:
      instance.save()
      if instance.debt_id:
        instance.debt.refresh_status()
      sync_utilities_from_repayment(instance)
      Transaction.objects.filter(pk=instance.pk).update(
        utilities_portion=instance.utilities_portion,
      )
    return instance


class UtilitiesOperationForm(forms.ModelForm):
  class Meta:
    model = UtilitiesOperation
    fields = ['title', 'amount', 'operation_type', 'project', 'date', 'notes']
    widgets = {
      'title': forms.TextInput(attrs={'class': 'form-control'}),
      'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
      'operation_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_operation_type'}),
      'project': forms.Select(attrs={'class': 'form-select'}),
      'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
      'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    }
    labels = {
      'title': 'Название',
      'amount': 'Сумма',
      'operation_type': 'Тип операции',
      'project': 'Проект',
      'date': 'Дата',
      'notes': 'Заметки',
    }

  def __init__(self, *args, **kwargs):
    self.balances = kwargs.pop('balances', None)
    super().__init__(*args, **kwargs)
    if self.instance.pk and self.instance.source == UtilitiesSource.DEBT:
      for field in self.fields.values():
        field.disabled = True

  def clean(self):
    cleaned = super().clean()
    operation_type = cleaned.get('operation_type')
    amount = cleaned.get('amount')

    if (
      operation_type == UtilitiesOperationType.EXPENSE
      and amount
      and not (self.instance.pk and self.instance.source == UtilitiesSource.DEBT)
    ):
      from .utilities import compute_utilities_balance
      balances = self.balances or compute_utilities_balance(
        exclude_pk=self.instance.pk if self.instance.pk else None,
      )
      if amount > balances['balance']:
        self.add_error(
          'amount',
          f'Недостаточно средств на коммунальных. Доступно: {balances["balance"]} ₽.',
        )
    return cleaned

  def save(self, commit=True):
    instance = super().save(commit=False)
    if instance.operation_type == UtilitiesOperationType.DEPOSIT and not instance.pk:
      instance.source = UtilitiesSource.EXTERNAL
    if commit:
      instance.save()
    return instance


class ReserveTransferForm(forms.ModelForm):
  class Meta:
    model = ReserveTransfer
    fields = ['title', 'amount', 'direction', 'source', 'project', 'date', 'notes']
    widgets = {
      'title': forms.TextInput(attrs={'class': 'form-control'}),
      'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
      'direction': forms.Select(attrs={'class': 'form-select', 'id': 'id_direction'}),
      'source': forms.Select(attrs={'class': 'form-select', 'id': 'id_source'}),
      'project': forms.Select(attrs={'class': 'form-select'}),
      'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
      'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    }
    labels = {
      'title': 'Название',
      'amount': 'Сумма',
      'direction': 'Операция',
      'source': 'Источник',
      'project': 'Проект',
      'date': 'Дата',
      'notes': 'Заметки',
    }

  def clean(self):
    cleaned = super().clean()
    direction = cleaned.get('direction')
    source = cleaned.get('source')
    amount = cleaned.get('amount')

    if direction == ReserveDirection.TO_RESERVE:
      if not source:
        self.add_error('source', 'Укажите источник пополнения резерва.')
      if source == ReserveSource.BALANCE and amount:
        balances = compute_finance_balances(
          exclude_reserve_pk=self.instance.pk if self.instance.pk else None,
        )
        available = balances['main_balance']
        if amount > available:
          self.add_error(
            'amount',
            f'Недостаточно средств на балансе. Доступно: {available} ₽.',
          )
    elif direction == ReserveDirection.FROM_RESERVE:
      cleaned['source'] = ''
      if amount:
        balances = compute_finance_balances(
          exclude_reserve_pk=self.instance.pk if self.instance.pk else None,
        )
        available = balances['reserve_balance']
        if amount > available:
          self.add_error(
            'amount',
            f'Недостаточно средств в резерве. Доступно: {available} ₽.',
          )

    return cleaned
