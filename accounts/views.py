from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, UpdateView

from .forms import UserApprovalForm
from .models import ApprovalStatus, Role
from .permissions import AdminRequiredMixin

User = get_user_model()


def pending_view(request):
  if request.user.is_authenticated and request.user.is_approved:
    return redirect('core:dashboard')
  return render(request, 'accounts/pending.html')


class UserListView(AdminRequiredMixin, ListView):
  model = User
  template_name = 'accounts/user_list.html'
  context_object_name = 'users'

  def get_queryset(self):
    qs = User.objects.all()
    status = self.request.GET.get('status')
    if status:
      qs = qs.filter(approval_status=status)
    return qs


def approve_user(request, pk):
  if not request.user.is_admin:
    messages.error(request, 'Недостаточно прав.')
    return redirect('core:dashboard')
  user = get_object_or_404(User, pk=pk)
  role = request.POST.get('role', Role.OBSERVER)
  if role not in Role.values:
    role = Role.OBSERVER
  user.approve(role)
  messages.success(request, f'Пользователь {user.username} одобрен с ролью «{user.get_role_display()}».')
  return redirect('accounts:user_list')


def reject_user(request, pk):
  if not request.user.is_admin:
    messages.error(request, 'Недостаточно прав.')
    return redirect('core:dashboard')
  user = get_object_or_404(User, pk=pk)
  user.reject()
  messages.warning(request, f'Пользователь {user.username} отклонён.')
  return redirect('accounts:user_list')


class UserUpdateView(AdminRequiredMixin, UpdateView):
  model = User
  form_class = UserApprovalForm
  template_name = 'accounts/user_form.html'
  success_url = '/accounts/users/'

  def form_valid(self, form):
    user = form.save(commit=False)
    if user.approval_status == ApprovalStatus.APPROVED:
      user.is_active = True
    elif user.approval_status in (ApprovalStatus.PENDING, ApprovalStatus.REJECTED):
      user.is_active = False
    user.save()
    messages.success(self.request, 'Пользователь обновлён.')
    return redirect(self.success_url)
