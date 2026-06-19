from django.urls import path

from . import views, yandex

app_name = 'accounts'

urlpatterns = [
  path('pending/', views.pending_view, name='pending'),
  path('users/', views.UserListView.as_view(), name='user_list'),
  path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
  path('users/<int:pk>/approve/', views.approve_user, name='user_approve'),
  path('users/<int:pk>/reject/', views.reject_user, name='user_reject'),
  path('yandex/login/', yandex.yandex_login_redirect, name='yandex_login'),
  path('yandex/callback/', yandex.yandex_callback, name='yandex_callback'),
]
