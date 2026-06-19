from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from projects.models import Project


class TransactionType(models.TextChoices):
  INCOME = 'income', _('Доход')
  EXPENSE = 'expense', _('Расход')
  DEBT_REPAYMENT = 'debt_repayment', _('Погашение задолженности')


class FinanceCategory(TimeStampedModel):
  name = models.CharField(_('Название'), max_length=100)
  transaction_type = models.CharField(
    _('Тип'),
    max_length=20,
    choices=[
      (TransactionType.INCOME, TransactionType.INCOME.label),
      (TransactionType.EXPENSE, TransactionType.EXPENSE.label),
    ],
  )
  color = models.CharField(_('Цвет'), max_length=7, default='#64748b')

  class Meta:
    verbose_name = _('Категория')
    verbose_name_plural = _('Категории')
    ordering = ['name']

  def __str__(self):
    return self.name


class Transaction(TimeStampedModel):
  title = models.CharField(_('Название'), max_length=255)
  amount = models.DecimalField(_('Сумма'), max_digits=12, decimal_places=2)
  transaction_type = models.CharField(
    _('Тип'),
    max_length=20,
    choices=TransactionType.choices,
  )
  category = models.ForeignKey(
    FinanceCategory,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='transactions',
    verbose_name=_('Категория'),
  )
  project = models.ForeignKey(
    Project,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='transactions',
    verbose_name=_('Проект'),
  )
  debt = models.ForeignKey(
    'debts.Debt',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='repayments',
    verbose_name=_('Задолженность'),
  )
  debt_debtor = models.ForeignKey(
    'debts.DebtDebtor',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='repayments',
    verbose_name=_('Должник'),
  )
  repaid_by_user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='debt_repayments',
    verbose_name=_('Кто погашает (должник)'),
  )
  repaid_by_name = models.CharField(
    _('Кто погашает (вручную)'),
    max_length=255,
    blank=True,
  )
  utilities_portion = models.DecimalField(
    _('На коммунальные'),
    max_digits=12,
    decimal_places=2,
    default=0,
  )
  skip_utilities = models.BooleanField(
    _('Не удерживать коммунальные'),
    default=False,
    help_text=_('Вся сумма погашения пойдёт на долг, без отчисления на коммунальные'),
  )
  date = models.DateField(_('Дата'))
  notes = models.TextField(_('Заметки'), blank=True)

  class Meta:
    verbose_name = _('Транзакция')
    verbose_name_plural = _('Транзакции')
    ordering = ['-date', '-created_at']

  def __str__(self):
    return f'{self.title} — {self.amount}'

  def get_absolute_url(self):
    return reverse_lazy('finance:transaction_detail', kwargs={'pk': self.pk})

  @property
  def signed_amount(self):
    if self.transaction_type == TransactionType.EXPENSE:
      return -self.amount
    if self.transaction_type == TransactionType.DEBT_REPAYMENT:
      return Decimal('0')
    return self.amount

  @property
  def repaid_by_display(self):
    if self.debt_debtor_id:
      return self.debt_debtor.display_name
    if self.repaid_by_user:
      return self.repaid_by_user.get_full_name() or self.repaid_by_user.username
    return self.repaid_by_name or '—'

  @property
  def debt_reduction_amount(self):
    return self.amount - self.utilities_portion


class ReserveSource(models.TextChoices):
  BALANCE = 'balance', _('С основного баланса')
  EXTERNAL = 'external', _('Извне')


class ReserveDirection(models.TextChoices):
  TO_RESERVE = 'to_reserve', _('Пополнение резерва')
  FROM_RESERVE = 'from_reserve', _('Возврат в баланс')


class ReserveTransfer(TimeStampedModel):
  title = models.CharField(_('Название'), max_length=255)
  amount = models.DecimalField(_('Сумма'), max_digits=12, decimal_places=2)
  direction = models.CharField(
    _('Операция'),
    max_length=20,
    choices=ReserveDirection.choices,
    default=ReserveDirection.TO_RESERVE,
  )
  source = models.CharField(
    _('Источник'),
    max_length=20,
    choices=ReserveSource.choices,
    blank=True,
  )
  project = models.ForeignKey(
    Project,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='reserve_transfers',
    verbose_name=_('Проект'),
  )
  date = models.DateField(_('Дата'))
  notes = models.TextField(_('Заметки'), blank=True)

  class Meta:
    verbose_name = _('Операция резерва')
    verbose_name_plural = _('Операции резерва')
    ordering = ['-date', '-created_at']

  def __str__(self):
    return f'{self.title} — {self.amount}'

  def get_absolute_url(self):
    return reverse_lazy('finance:reserve_detail', kwargs={'pk': self.pk})

  @property
  def source_display(self):
    if self.direction == ReserveDirection.FROM_RESERVE:
      return 'Резерв'
    return self.get_source_display() if self.source else '—'


class UtilitiesOperationType(models.TextChoices):
  DEPOSIT = 'deposit', _('Пополнение')
  EXPENSE = 'expense', _('Расход')


class UtilitiesSource(models.TextChoices):
  EXTERNAL = 'external', _('Извне')
  DEBT = 'debt', _('Из погашения задолженности')


class UtilitiesOperation(TimeStampedModel):
  title = models.CharField(_('Название'), max_length=255)
  amount = models.DecimalField(_('Сумма'), max_digits=12, decimal_places=2)
  operation_type = models.CharField(
    _('Тип операции'),
    max_length=20,
    choices=UtilitiesOperationType.choices,
  )
  source = models.CharField(
    _('Источник'),
    max_length=20,
    choices=UtilitiesSource.choices,
    blank=True,
  )
  project = models.ForeignKey(
    Project,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='utilities_operations',
    verbose_name=_('Проект'),
  )
  debt = models.ForeignKey(
    'debts.Debt',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='utilities_credits',
    verbose_name=_('Задолженность'),
  )
  repayment = models.OneToOneField(
    Transaction,
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='utilities_credit',
    verbose_name=_('Погашение'),
  )
  date = models.DateField(_('Дата'))
  notes = models.TextField(_('Заметки'), blank=True)

  class Meta:
    verbose_name = _('Операция (коммунальные)')
    verbose_name_plural = _('Операции (коммунальные)')
    ordering = ['-date', '-created_at']

  def __str__(self):
    return f'{self.title} — {self.amount}'

  def get_absolute_url(self):
    return reverse_lazy('finance:utilities_detail', kwargs={'pk': self.pk})

  @property
  def source_display(self):
    if self.operation_type == UtilitiesOperationType.EXPENSE:
      return 'Расход'
    return self.get_source_display() if self.source else '—'
