from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'core'

urlpatterns = [
  path('', views.DashboardView.as_view(), name='dashboard'),
  path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),
]
