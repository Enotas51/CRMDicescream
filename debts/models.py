from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Sum
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from projects.models import Project


class DebtStatus(models.TextChoices):
  OPEN = 'open', _('Открыта')
  PARTIAL = 'partial', _('Частично погашена')
  CLOSED = 'closed', _('Закрыта')
  CANCELLED = 'cancelled', _('Отменена')


class Debt(TimeStampedModel):
  title = models.CharField(_('Название'), max_length=255)
  description = models.TextField(_('Описание'), blank=True)
  amount = models.DecimalField(
    _('Общая сумма долга'),
    max_digits=12,
    decimal_places=2,
    default=0,
  )

  creditor_user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='debts_as_creditor',
    verbose_name=_('Кредитор (пользователь)'),
  )
  creditor_name = models.CharField(_('Кредитор (вручную)'), max_length=255, blank=True)

  project = models.ForeignKey(
    Project,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='debts',
    verbose_name=_('Проект'),
  )
  due_date = models.DateField(_('Срок погашения'), null=True, blank=True)
  utilities_amount = models.DecimalField(
    _('Коммунальные с каждого платежа'),
    max_digits=12,
    decimal_places=2,
    default=0,
    help_text=_('Фиксированная сумма, которая удерживается с каждого погашения на коммунальные (не входит в долг)'),
  )
  status = models.CharField(
    _('Статус'),
    max_length=20,
    choices=DebtStatus.choices,
    default=DebtStatus.OPEN,
  )

  class Meta:
    verbose_name = _('Задолженность')
    verbose_name_plural = _('Задолженности')
    ordering = ['-created_at']

  def __str__(self):
    return self.title

  def get_absolute_url(self):
    return reverse_lazy('debts:detail', kwargs={'pk': self.pk})

  @property
  def creditor_display(self):
    if self.creditor_user:
      return self.creditor_user.get_full_name() or self.creditor_user.username
    return self.creditor_name or '—'

  @property
  def debtors_display(self):
    debtors = self.debtors.all()
    if not debtors:
      return '—'
    return ', '.join(d.display_name for d in debtors)

  def recalculate_amount(self, save=True):
    total = self.debtors.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    self.amount = total
    if save:
      self.save(update_fields=['amount'])

  def get_debt_reduction_total(self, exclude_repayment_pk=None):
    from finance.models import Transaction, TransactionType
    qs = self.repayments.filter(transaction_type=TransactionType.DEBT_REPAYMENT)
    if exclude_repayment_pk:
      qs = qs.exclude(pk=exclude_repayment_pk)
    total = qs.aggregate(
      total=Sum(F('amount') - F('utilities_portion')),
    )['total']
    return total or Decimal('0')

  def get_repaid_amount(self):
    return self.get_debt_reduction_total()

  @property
  def remaining_amount(self):
    return self.amount - self.get_repaid_amount()

  def get_utilities_credited(self):
    from finance.utilities import get_debt_utilities_credited
    return get_debt_utilities_credited(self)

  def refresh_status(self, save=True):
    if self.status == DebtStatus.CANCELLED:
      return
    repaid = self.get_debt_reduction_total()
    if self.amount > 0 and repaid >= self.amount:
      self.status = DebtStatus.CLOSED
    elif repaid > 0:
      self.status = DebtStatus.PARTIAL
    else:
      self.status = DebtStatus.OPEN
    if save:
      self.save(update_fields=['status'])

  def sync_creditor_name(self):
    if self.creditor_user:
      self.creditor_name = self.creditor_user.get_full_name() or self.creditor_user.username


class DebtDebtor(models.Model):
  debt = models.ForeignKey(
    Debt,
    on_delete=models.CASCADE,
    related_name='debtors',
    verbose_name=_('Задолженность'),
  )
  debtor_user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='debt_obligations',
    verbose_name=_('Должник (пользователь)'),
  )
  debtor_name = models.CharField(_('Должник (вручную)'), max_length=255, blank=True)
  amount = models.DecimalField(_('Сумма долга'), max_digits=12, decimal_places=2)

  class Meta:
    verbose_name = _('Должник')
    verbose_name_plural = _('Должники')
    ordering = ['id']

  def __str__(self):
    return f'{self.display_name} — {self.amount}'

  @property
  def display_name(self):
    if self.debtor_user:
      return self.debtor_user.get_full_name() or self.debtor_user.username
    return self.debtor_name or '—'

  def sync_name(self):
    if self.debtor_user:
      self.debtor_name = self.debtor_user.get_full_name() or self.debtor_user.username

  def get_repaid_amount(self, exclude_repayment_pk=None):
    from finance.models import Transaction, TransactionType
    qs = self.repayments.filter(transaction_type=TransactionType.DEBT_REPAYMENT)
    if exclude_repayment_pk:
      qs = qs.exclude(pk=exclude_repayment_pk)
    total = qs.aggregate(
      total=Sum(F('amount') - F('utilities_portion')),
    )['total']
    return total or Decimal('0')

  @property
  def remaining_amount(self):
    return self.amount - self.get_repaid_amount()

  @property
  def can_link_user(self):
    return not self.debtor_user and bool(self.debtor_name)
