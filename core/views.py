from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
import json
from django.views import View
from decimal import Decimal

from accounts.permissions import ApprovedUserMixin
from calendar_app.models import Event
from finance.balances import compute_finance_balances
from finance.models import ReserveDirection, ReserveTransfer, Transaction, TransactionType, UtilitiesOperation, UtilitiesOperationType
from finance.utilities import compute_utilities_balance
from projects.models import Project
from tasks.models import Task


class DashboardView(ApprovedUserMixin, View):
  template_name = 'core/dashboard.html'

  def get(self, request):
    projects = Project.objects.all()[:5]
    tasks_due = Task.objects.exclude(status='done').select_related(
      'project', 'assignee',
    ).order_by('due_date', '-created_at')[:8]
    upcoming_events = Event.objects.filter(
      start__gte=timezone.now(),
    ).select_related('project')[:5]

    balances = compute_finance_balances()
    recent_movements = []
    for item in Transaction.objects.all()[:5]:
      recent_movements.append({
        'date': item.date, 'created_at': item.created_at, 'title': item.title,
        'kind': item.get_transaction_type_display(), 'amount': item.amount,
        'category': item.category.name if item.category else '',
        'project': item.project.name if item.project else '',
        'tone': 'danger' if item.transaction_type == TransactionType.EXPENSE else 'success',
        'url': item.get_absolute_url(),
      })
    for item in ReserveTransfer.objects.all()[:5]:
      recent_movements.append({
        'date': item.date, 'created_at': item.created_at, 'title': item.title,
        'kind': 'Резерв', 'amount': item.amount,
        'category': '', 'project': '',
        'tone': 'info' if item.direction == ReserveDirection.TO_RESERVE else 'success',
        'url': item.get_absolute_url(),
      })
    for item in UtilitiesOperation.objects.all()[:5]:
      recent_movements.append({
        'date': item.date, 'created_at': item.created_at, 'title': item.title,
        'kind': 'Коммунальные', 'amount': item.amount,
        'category': '', 'project': '',
        'tone': 'danger' if item.operation_type == UtilitiesOperationType.EXPENSE else 'success',
        'url': item.get_absolute_url(),
      })
    recent_movements.sort(key=lambda item: (item['date'], item['created_at']), reverse=True)

    today = timezone.localdate()
    month_start = today.replace(day=1)
    month_end = today
    transactions = Transaction.objects.all()
    month_income = transactions.filter(
      date__gte=month_start,
      date__lte=month_end,
      transaction_type=TransactionType.INCOME,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    month_expense = transactions.filter(
      date__gte=month_start,
      date__lte=month_end,
      transaction_type=TransactionType.EXPENSE,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    reserve_transfers = ReserveTransfer.objects.all()
    balance = sum((item.signed_amount for item in transactions if item.date < month_start), Decimal('0'))
    balance -= sum((item.amount for item in reserve_transfers if item.date < month_start and item.direction == ReserveDirection.TO_RESERVE and item.source == 'balance'), Decimal('0'))
    balance += sum((item.amount for item in reserve_transfers if item.date < month_start and item.direction == ReserveDirection.FROM_RESERVE), Decimal('0'))
    reserve = sum((item.amount if item.direction == ReserveDirection.TO_RESERVE else -item.amount for item in reserve_transfers if item.date < month_start), Decimal('0'))
    balance_points, reserve_points = [], []
    day = month_start
    while day <= month_end:
      for item in transactions:
        if item.date == day:
          balance += item.signed_amount
      for item in reserve_transfers:
        if item.date == day:
          if item.direction == ReserveDirection.TO_RESERVE:
            reserve += item.amount
            if item.source == 'balance': balance -= item.amount
          else:
            reserve -= item.amount
            balance += item.amount
      balance_points.append({'date': day.strftime('%d.%m'), 'value': float(balance)})
      reserve_points.append({'date': day.strftime('%d.%m'), 'value': float(reserve)})
      day += timedelta(days=1)

    pending_users_count = 0
    if request.user.is_admin:
      from accounts.models import ApprovalStatus
      from django.contrib.auth import get_user_model
      User = get_user_model()
      pending_users_count = User.objects.filter(
        approval_status=ApprovalStatus.PENDING
      ).count()

    context = {
      'projects': projects,
      'tasks_due': tasks_due,
      'upcoming_events': upcoming_events,
      'balance': balances['main_balance'],
      'reserve_balance': balances['reserve_balance'],
      'utilities_balance': compute_utilities_balance()['balance'],
      'month_profit': month_income - month_expense,
      'recent_movements': recent_movements[:5],
      'pending_users_count': pending_users_count,
      'can_edit': request.user.can_edit,
      'balance_chart': json.dumps(balance_points),
      'reserve_chart': json.dumps(reserve_points),
    }
    return render(request, self.template_name, context)
