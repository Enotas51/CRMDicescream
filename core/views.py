from django.contrib import messages
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from accounts.permissions import ApprovedUserMixin
from calendar_app.models import Event
from finance.balances import compute_finance_balances
from finance.utilities import compute_utilities_balance
from projects.models import Project
from tasks.models import Task


class DashboardView(ApprovedUserMixin, View):
  template_name = 'core/dashboard.html'

  def get(self, request):
    today = timezone.localdate()
    projects = Project.objects.all()[:5]
    tasks_due = Task.objects.filter(
      due_date__lte=today + timezone.timedelta(days=7),
    ).exclude(status='done').select_related('project', 'assignee')[:8]
    upcoming_events = Event.objects.filter(
      start__gte=timezone.now(),
    ).select_related('project')[:5]

    balances = compute_finance_balances()

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
      'pending_users_count': pending_users_count,
      'can_edit': request.user.can_edit,
    }
    return render(request, self.template_name, context)
