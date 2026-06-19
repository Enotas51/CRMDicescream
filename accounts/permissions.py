from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

from .models import Role


class ApprovedUserMixin(LoginRequiredMixin):
  def dispatch(self, request, *args, **kwargs):
    if not request.user.is_authenticated:
      return self.handle_no_permission()
    if not request.user.is_approved:
      from django.shortcuts import redirect
      return redirect('accounts:pending')
    return super().dispatch(request, *args, **kwargs)


class CanEditMixin(ApprovedUserMixin):
  def dispatch(self, request, *args, **kwargs):
    response = super().dispatch(request, *args, **kwargs)
    if response.status_code == 302:
      return response
    if not request.user.can_edit:
      raise PermissionDenied('Недостаточно прав для редактирования.')
    return response


class AdminRequiredMixin(ApprovedUserMixin, UserPassesTestMixin):
  def test_func(self):
    return self.request.user.is_admin


def user_can_edit_object(user, obj=None):
  if not user.is_authenticated or not user.is_approved:
    return False
  if user.is_admin:
    return True
  if user.is_editor:
    if obj is None:
      return True
    for attr in ('created_by', 'owner', 'assignee', 'author'):
      owner = getattr(obj, attr, None)
      if owner is not None:
        return owner == user
    return True
  return False


def user_can_view_object(user, obj=None):
  if not user.is_authenticated or not user.is_approved:
    return False
  return True
