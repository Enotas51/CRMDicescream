from decimal import Decimal
import json

from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import ApprovedUserMixin, CanEditMixin, user_can_edit_object
from debts.models import Debt, DebtStatus
from .balances import compute_finance_balances
from .exports import finance_excel_response
from .forms import FinanceCategoryForm, ReserveTransferForm, TransactionForm, UtilitiesOperationForm
from .models import (
  FinanceCategory,
  ReserveDirection,
  ReserveSource,
  ReserveTransfer,
  Transaction,
  TransactionType,
  UtilitiesOperation,
  UtilitiesSource,
)
from .periods import (
  build_month_choices,
  filter_queryset_by_period,
  parse_finance_period,
  period_label,
  period_query_string,
)
from .utilities import compute_utilities_balance


def _finance_period_context(request, extra=None):
  year, month, start, end, all_time = parse_finance_period(request)
  today = timezone.localdate()
  return {
    'filter_year': year or today.year,
    'filter_month': month or today.month,
    'period_start': start,
    'period_end': end,
    'period_all_time': all_time,
    'period_label': period_label(year, month, all_time),
    'month_choices': build_month_choices(),
    'export_url': 'finance:export',
    'export_query': period_query_string(year, month, all_time, extra=extra),
  }


def _period_transaction_totals(start, end, all_time):
  qs = Transaction.objects.all()
  qs = filter_queryset_by_period(qs, start, end, all_time)
  month_income = qs.filter(transaction_type=TransactionType.INCOME).aggregate(
    total=Sum('amount'),
  )['total'] or Decimal('0')
  month_expense = qs.filter(transaction_type=TransactionType.EXPENSE).aggregate(
    total=Sum('amount'),
  )['total'] or Decimal('0')
  debt_repayments = qs.filter(transaction_type=TransactionType.DEBT_REPAYMENT).aggregate(
    total=Sum('amount'),
  )['total'] or Decimal('0')
  return month_income, month_expense, debt_repayments


class FinanceDashboardView(ApprovedUserMixin, ListView):
  model = Transaction
  template_name = 'finance/dashboard.html'
  context_object_name = 'transactions'

  def get_queryset(self):
    qs = Transaction.objects.select_related('project', 'debt').all()
    _, _, start, end, all_time = parse_finance_period(self.request)
    qs = filter_queryset_by_period(qs, start, end, all_time)
    return qs[:100]

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    balances = compute_finance_balances()
    year, month, start, end, all_time = parse_finance_period(self.request)
    month_income, month_expense, debt_repayments = _period_transaction_totals(start, end, all_time)

    ctx.update(_finance_period_context(self.request))
    ctx.update({
      'total_income': balances['income'],
      'total_expense': balances['expense'],
      'balance': balances['main_balance'],
      'reserve_balance': balances['reserve_balance'],
      'utilities_balance': compute_utilities_balance()['balance'],
      'month_income': month_income,
      'month_expense': month_expense,
      'month_balance': month_income - month_expense,
      'period_debt_repayments': debt_repayments,
      'can_edit': self.request.user.can_edit,
    })
    return ctx


class TransactionListView(ApprovedUserMixin, ListView):
  model = Transaction
  template_name = 'finance/transaction_list.html'
  context_object_name = 'transactions'
  paginate_by = 30

  def get_queryset(self):
    qs = Transaction.objects.select_related('project', 'debt')
    ttype = self.request.GET.get('type')
    project = self.request.GET.get('project')
    if ttype:
      qs = qs.filter(transaction_type=ttype)
    if project:
      qs = qs.filter(project_id=project)
    _, _, start, end, all_time = parse_finance_period(self.request)
    return filter_queryset_by_period(qs, start, end, all_time)

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    extra = []
    if self.request.GET.get('type'):
      extra.append(f"type={self.request.GET['type']}")
    if self.request.GET.get('project'):
      extra.append(f"project={self.request.GET['project']}")
    ctx.update(_finance_period_context(self.request, extra=extra or None))
    return ctx


class TransactionDetailView(ApprovedUserMixin, DetailView):
  model = Transaction
  template_name = 'finance/transaction_detail.html'
  context_object_name = 'transaction'

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['can_edit'] = user_can_edit_object(self.request.user, self.object)
    return ctx


class TransactionCreateView(CanEditMixin, CreateView):
  model = Transaction
  form_class = TransactionForm
  template_name = 'finance/transaction_form.html'
  success_url = reverse_lazy('finance:dashboard')

  def get_initial(self):
    initial = super().get_initial()
    debt_id = self.request.GET.get('debt')
    debtor_id = self.request.GET.get('debtor')
    if debt_id:
      initial['debt'] = debt_id
    if debtor_id:
      initial['debt_debtor'] = debtor_id
    if self.request.GET.get('type') == 'debt_repayment':
      initial['transaction_type'] = TransactionType.DEBT_REPAYMENT
    return initial

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['debts_json'] = _build_debts_json()
    return ctx

  def form_valid(self, form):
    form.instance.created_by = self.request.user
    messages.success(self.request, 'Транзакция добавлена.')
    return super().form_valid(form)


class TransactionUpdateView(CanEditMixin, UpdateView):
  model = Transaction
  form_class = TransactionForm
  template_name = 'finance/transaction_form.html'
  success_url = reverse_lazy('finance:dashboard')

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['debts_json'] = _build_debts_json(self.object)
    return ctx

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and not user_can_edit_object(request.user, self.object):
      messages.error(request, 'Недостаточно прав.')
      return redirect('finance:transaction_detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)

  def form_valid(self, form):
    messages.success(self.request, 'Транзакция обновлена.')
    return super().form_valid(form)


class TransactionDeleteView(CanEditMixin, DeleteView):
  model = Transaction
  template_name = 'finance/confirm_delete.html'
  success_url = reverse_lazy('finance:dashboard')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and self.object.created_by != request.user:
      messages.error(request, 'Недостаточно прав.')
      return redirect('finance:transaction_detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)


class CategoryListView(ApprovedUserMixin, ListView):
  model = FinanceCategory
  template_name = 'finance/category_list.html'
  context_object_name = 'categories'


class CategoryCreateView(CanEditMixin, CreateView):
  model = FinanceCategory
  form_class = FinanceCategoryForm
  template_name = 'finance/category_form.html'
  success_url = reverse_lazy('finance:categories')

  def form_valid(self, form):
    form.instance.created_by = self.request.user
    messages.success(self.request, 'Категория создана.')
    return super().form_valid(form)


class ReserveDashboardView(ApprovedUserMixin, ListView):
  model = ReserveTransfer
  template_name = 'finance/reserve.html'
  context_object_name = 'transfers'
  paginate_by = 30

  def get_queryset(self):
    qs = ReserveTransfer.objects.select_related('project').all()
    _, _, start, end, all_time = parse_finance_period(self.request)
    return filter_queryset_by_period(qs, start, end, all_time)

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    balances = compute_finance_balances()
    ctx.update(_finance_period_context(self.request))
    ctx.update({
      'balances': balances,
      'can_edit': self.request.user.can_edit,
    })
    return ctx


class ReserveTransferCreateView(CanEditMixin, CreateView):
  model = ReserveTransfer
  form_class = ReserveTransferForm
  template_name = 'finance/reserve_form.html'
  success_url = reverse_lazy('finance:reserve')

  def get_initial(self):
    initial = super().get_initial()
    direction = self.request.GET.get('direction')
    source = self.request.GET.get('source')
    if direction == 'from_reserve':
      initial['direction'] = ReserveDirection.FROM_RESERVE
    if source == 'external':
      initial['source'] = ReserveSource.EXTERNAL
    elif source == 'balance':
      initial['source'] = ReserveSource.BALANCE
    return initial

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['balances'] = compute_finance_balances()
    return ctx

  def form_valid(self, form):
    form.instance.created_by = self.request.user
    messages.success(self.request, 'Операция с резервом сохранена.')
    return super().form_valid(form)


class ReserveTransferDetailView(ApprovedUserMixin, DetailView):
  model = ReserveTransfer
  template_name = 'finance/reserve_detail.html'
  context_object_name = 'transfer'

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['can_edit'] = user_can_edit_object(self.request.user, self.object)
    return ctx


class ReserveTransferUpdateView(CanEditMixin, UpdateView):
  model = ReserveTransfer
  form_class = ReserveTransferForm
  template_name = 'finance/reserve_form.html'
  success_url = reverse_lazy('finance:reserve')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and not user_can_edit_object(request.user, self.object):
      messages.error(request, 'Недостаточно прав.')
      return redirect('finance:reserve_detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['balances'] = compute_finance_balances(exclude_reserve_pk=self.object.pk)
    return ctx

  def form_valid(self, form):
    messages.success(self.request, 'Операция обновлена.')
    return super().form_valid(form)


class ReserveTransferDeleteView(CanEditMixin, DeleteView):
  model = ReserveTransfer
  template_name = 'finance/reserve_confirm_delete.html'
  success_url = reverse_lazy('finance:reserve')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and self.object.created_by != request.user:
      messages.error(request, 'Недостаточно прав.')
      return redirect('finance:reserve_detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)


class UtilitiesDashboardView(ApprovedUserMixin, ListView):
  model = UtilitiesOperation
  template_name = 'finance/utilities.html'
  context_object_name = 'operations'
  paginate_by = 30

  def get_queryset(self):
    qs = UtilitiesOperation.objects.select_related('project', 'debt').all()
    _, _, start, end, all_time = parse_finance_period(self.request)
    return filter_queryset_by_period(qs, start, end, all_time)

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx.update(_finance_period_context(self.request))
    ctx.update({
      'balances': compute_utilities_balance(),
      'can_edit': self.request.user.can_edit,
    })
    return ctx


class UtilitiesOperationCreateView(CanEditMixin, CreateView):
  model = UtilitiesOperation
  form_class = UtilitiesOperationForm
  template_name = 'finance/utilities_form.html'
  success_url = reverse_lazy('finance:utilities')

  def get_form_kwargs(self):
    kwargs = super().get_form_kwargs()
    kwargs['balances'] = compute_utilities_balance()
    return kwargs

  def get_initial(self):
    initial = super().get_initial()
    op_type = self.request.GET.get('type')
    if op_type == 'expense':
      from .models import UtilitiesOperationType
      initial['operation_type'] = UtilitiesOperationType.EXPENSE
    elif op_type == 'deposit':
      from .models import UtilitiesOperationType
      initial['operation_type'] = UtilitiesOperationType.DEPOSIT
    return initial

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['balances'] = compute_utilities_balance()
    return ctx

  def form_valid(self, form):
    form.instance.created_by = self.request.user
    messages.success(self.request, 'Операция сохранена.')
    return super().form_valid(form)


class UtilitiesOperationDetailView(ApprovedUserMixin, DetailView):
  model = UtilitiesOperation
  template_name = 'finance/utilities_detail.html'
  context_object_name = 'operation'

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['can_edit'] = (
      user_can_edit_object(self.request.user, self.object)
      and self.object.source != UtilitiesSource.DEBT
    )
    ctx['is_from_debt'] = self.object.source == UtilitiesSource.DEBT
    return ctx


class UtilitiesOperationUpdateView(CanEditMixin, UpdateView):
  model = UtilitiesOperation
  form_class = UtilitiesOperationForm
  template_name = 'finance/utilities_form.html'
  success_url = reverse_lazy('finance:utilities')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if self.object.source == UtilitiesSource.DEBT:
      messages.error(request, 'Операции из погашения задолженности редактируются через финансы.')
      return redirect('finance:utilities_detail', pk=self.object.pk)
    if not request.user.is_admin and not user_can_edit_object(request.user, self.object):
      messages.error(request, 'Недостаточно прав.')
      return redirect('finance:utilities_detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)

  def get_form_kwargs(self):
    kwargs = super().get_form_kwargs()
    kwargs['balances'] = compute_utilities_balance(exclude_pk=self.object.pk)
    return kwargs

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['balances'] = compute_utilities_balance(exclude_pk=self.object.pk)
    return ctx

  def form_valid(self, form):
    messages.success(self.request, 'Операция обновлена.')
    return super().form_valid(form)


class UtilitiesOperationDeleteView(CanEditMixin, DeleteView):
  model = UtilitiesOperation
  template_name = 'finance/utilities_confirm_delete.html'
  success_url = reverse_lazy('finance:utilities')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if self.object.source == UtilitiesSource.DEBT:
      messages.error(request, 'Операции из погашения удаляются вместе с транзакцией погашения.')
      return redirect('finance:utilities_detail', pk=self.object.pk)
    if not request.user.is_admin and self.object.created_by != request.user:
      messages.error(request, 'Недостаточно прав.')
      return redirect('finance:utilities_detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)


class FinanceExportView(ApprovedUserMixin, View):
  def get(self, request):
    year, month, start, end, all_time = parse_finance_period(request)
    month_income, month_expense, debt_repayments = _period_transaction_totals(start, end, all_time)
    balances = compute_finance_balances()

    transactions = filter_queryset_by_period(
      Transaction.objects.select_related('project', 'debt', 'debt_debtor'),
      start, end, all_time,
    ).order_by('-date', '-created_at')

    reserve_transfers = filter_queryset_by_period(
      ReserveTransfer.objects.select_related('project'),
      start, end, all_time,
    ).order_by('-date', '-created_at')

    utilities_ops = filter_queryset_by_period(
      UtilitiesOperation.objects.select_related('project', 'debt'),
      start, end, all_time,
    ).order_by('-date', '-created_at')

    summary = {
      'period': period_label(year, month, all_time),
      'income': month_income,
      'expense': month_expense,
      'net': month_income - month_expense,
      'debt_repayments': debt_repayments,
      'main_balance': balances['main_balance'],
      'reserve_balance': balances['reserve_balance'],
      'utilities_balance': compute_utilities_balance()['balance'],
      'transactions_count': transactions.count(),
      'reserve_count': reserve_transfers.count(),
      'utilities_count': utilities_ops.count(),
    }
    return finance_excel_response(
      summary, transactions, reserve_transfers, utilities_ops, year, month, all_time,
    )


def _build_debts_json(current_transaction=None):
  qs = Debt.objects.exclude(status=DebtStatus.CANCELLED).prefetch_related('debtors__debtor_user')
  if current_transaction and current_transaction.debt_id:
    qs = qs.filter(
      Q(status__in=[DebtStatus.OPEN, DebtStatus.PARTIAL]) | Q(pk=current_transaction.debt_id),
    )
  else:
    qs = qs.exclude(status=DebtStatus.CLOSED)

  result = []
  for d in qs.distinct():
    debtors = []
    for dd in d.debtors.all():
      debtors.append({
        'id': dd.pk,
        'display': dd.display_name,
        'amount': str(dd.amount),
        'remaining': str(dd.remaining_amount),
        'repaid': str(dd.get_repaid_amount()),
      })
    result.append({
      'id': d.pk,
      'title': d.title,
      'creditor_display': d.creditor_display,
      'remaining': str(d.remaining_amount),
      'amount': str(d.amount),
      'utilities_amount': str(d.utilities_amount),
      'utilities_per_payment': str(d.utilities_amount),
      'debtors': debtors,
    })
  return json.dumps(result)
