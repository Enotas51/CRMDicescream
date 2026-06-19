from django.urls import path

from . import views

app_name = 'debts'

urlpatterns = [
  path('', views.DebtListView.as_view(), name='list'),
  path('create/', views.DebtCreateView.as_view(), name='create'),
  path('<int:pk>/', views.DebtDetailView.as_view(), name='detail'),
  path('<int:pk>/edit/', views.DebtUpdateView.as_view(), name='edit'),
  path('<int:pk>/delete/', views.DebtDeleteView.as_view(), name='delete'),
  path('<int:pk>/link-creditor/', views.link_creditor, name='link_creditor'),
  path('<int:pk>/debtors/<int:debtor_pk>/link/', views.link_debtor, name='link_debtor'),
]
