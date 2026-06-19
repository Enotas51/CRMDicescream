from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import ApprovalStatus, Role


class CRMAccountAdapter(DefaultAccountAdapter):
  def save_user(self, request, user, form, commit=True):
    user = super().save_user(request, user, form, commit=False)
    user.approval_status = ApprovalStatus.PENDING
    user.role = Role.OBSERVER
    user.is_active = False
    if commit:
      user.save()
    return user

  def get_login_redirect_url(self, request):
    user = request.user
    if not user.is_approved:
      return '/accounts/pending/'
    return super().get_login_redirect_url(request)


class CRMSocialAccountAdapter(DefaultSocialAccountAdapter):
  def save_user(self, request, sociallogin, form=None):
    user = sociallogin.user
    if not user.pk:
      user.approval_status = ApprovalStatus.PENDING
      user.role = Role.OBSERVER
      user.is_active = False
    user = super().save_user(request, sociallogin, form)
    extra = sociallogin.account.extra_data or {}
    if extra.get('default_email'):
      user.email = extra['default_email']
    if extra.get('default_avatar_id'):
      user.avatar_url = f"https://avatars.yandex.net/get-yapic/{extra['default_avatar_id']}/islands-200"
    if extra.get('id'):
      user.yandex_id = str(extra['id'])
    user.save()
    return user

  def is_open_for_signup(self, request, sociallogin):
    return True
