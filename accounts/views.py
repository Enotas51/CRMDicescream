from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, ListView, UpdateView

from .forms import ProfileForm, UserApprovalForm
from .models import ApprovalStatus, Role
from .permissions import AdminRequiredMixin, ApprovedUserMixin

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


class TeamView(ApprovedUserMixin, ListView):
  model = User
  template_name = 'accounts/team.html'
  context_object_name = 'team_members'

  def get_queryset(self):
    return User.objects.filter(
      approval_status=ApprovalStatus.APPROVED,
      show_in_team=True,
    ).order_by('first_name', 'last_name', 'username')


class ProfileView(ApprovedUserMixin, UpdateView):
  model = User
  form_class = ProfileForm
  template_name = 'accounts/profile.html'
  success_url = '/accounts/profile/'

  def get_object(self, queryset=None):
    return self.request.user


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


@require_POST
def toggle_team_visibility(request, pk):
  if not request.user.is_admin:
    messages.error(request, 'Недостаточно прав.')
    return redirect('core:dashboard')
  user = get_object_or_404(User, pk=pk)
  user.show_in_team = not user.show_in_team
  user.save(update_fields=['show_in_team'])
  action = 'показан в команде' if user.show_in_team else 'скрыт из команды'
  messages.success(request, f'Пользователь {user.username} {action}.')
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


class UserDeleteView(AdminRequiredMixin, DeleteView):
  model = User
  template_name = 'accounts/user_confirm_delete.html'
  success_url = reverse_lazy('accounts:user_list')

  def dispatch(self, request, *args, **kwargs):
    target = self.get_object()
    if target.pk == request.user.pk:
      messages.error(request, 'Нельзя удалить собственный аккаунт.')
      return redirect('accounts:user_list')
    if (
      target.role == Role.ADMIN
      and target.approval_status == ApprovalStatus.APPROVED
      and not User.objects.filter(
        role=Role.ADMIN,
        approval_status=ApprovalStatus.APPROVED,
      ).exclude(pk=target.pk).exists()
    ):
      messages.error(request, 'Нельзя удалить единственного активного администратора.')
      return redirect('accounts:user_list')
    return super().dispatch(request, *args, **kwargs)

  def form_valid(self, form):
    username = self.object.username
    messages.success(self.request, f'Пользователь {username} удалён.')
    return super().form_valid(form)
