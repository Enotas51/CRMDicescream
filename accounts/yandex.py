import urllib.parse

import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect
from django.urls import reverse

from .models import ApprovalStatus, Role

User = get_user_model()

YANDEX_AUTH_URL = 'https://oauth.yandex.ru/authorize'
YANDEX_TOKEN_URL = 'https://oauth.yandex.ru/token'
YANDEX_USER_URL = 'https://login.yandex.ru/info'


def yandex_login_redirect(request):
  if not settings.YANDEX_CLIENT_ID:
    return redirect('account_login')
  params = {
    'response_type': 'code',
    'client_id': settings.YANDEX_CLIENT_ID,
    'redirect_uri': request.build_absolute_uri(reverse('accounts:yandex_callback')),
  }
  return redirect(f'{YANDEX_AUTH_URL}?{urllib.parse.urlencode(params)}')


def yandex_callback(request):
  code = request.GET.get('code')
  if not code:
    return redirect('account_login')

  token_resp = requests.post(
    YANDEX_TOKEN_URL,
    data={
      'grant_type': 'authorization_code',
      'code': code,
      'client_id': settings.YANDEX_CLIENT_ID,
      'client_secret': settings.YANDEX_CLIENT_SECRET,
    },
    timeout=15,
  )
  if token_resp.status_code != 200:
    return redirect('account_login')

  access_token = token_resp.json().get('access_token')
  user_resp = requests.get(
    YANDEX_USER_URL,
    headers={'Authorization': f'OAuth {access_token}'},
    params={'format': 'json'},
    timeout=15,
  )
  if user_resp.status_code != 200:
    return redirect('account_login')

  data = user_resp.json()
  yandex_id = str(data.get('id', ''))
  email = data.get('default_email') or data.get('login', '') + '@yandex.ru'
  login_name = data.get('login', f'yandex_{yandex_id}')
  display_name = data.get('display_name') or data.get('real_name') or login_name

  user = User.objects.filter(yandex_id=yandex_id).first()
  if not user:
    user = User.objects.filter(email=email).first()

  if not user:
    username = login_name
    base = username
    counter = 1
    while User.objects.filter(username=username).exists():
      username = f'{base}_{counter}'
      counter += 1
    user = User(
      username=username,
      email=email,
      yandex_id=yandex_id,
      approval_status=ApprovalStatus.PENDING,
      role=Role.OBSERVER,
      is_active=False,
    )
    user.set_unusable_password()
  else:
    if not user.yandex_id:
      user.yandex_id = yandex_id

  if data.get('default_avatar_id'):
    user.avatar_url = f"https://avatars.yandex.net/get-yapic/{data['default_avatar_id']}/islands-200"

  parts = display_name.split(' ', 1)
  if not user.first_name and parts:
    user.first_name = parts[0]
  if not user.last_name and len(parts) > 1:
    user.last_name = parts[1]

  user.save()
  login(request, user, backend='django.contrib.auth.backends.ModelBackend')

  if user.is_approved:
    return redirect('core:dashboard')
  return redirect('accounts:pending')
