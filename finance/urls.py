from django.urls import path

from . import views

app_name = 'finance'

urlpatterns = [
  path('', views.FinanceDashboardView.as_view(), name='dashboard'),
  path('transactions/', views.TransactionListView.as_view(), name='transactions'),
  path('transactions/create/', views.TransactionCreateView.as_view(), name='transaction_create'),
  path('transactions/<int:pk>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
  path('transactions/<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='transaction_edit'),
  path('transactions/<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
  path('categories/', views.CategoryListView.as_view(), name='categories'),
  path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
  path('reserve/', views.ReserveDashboardView.as_view(), name='reserve'),
  path('reserve/create/', views.ReserveTransferCreateView.as_view(), name='reserve_create'),
  path('reserve/<int:pk>/', views.ReserveTransferDetailView.as_view(), name='reserve_detail'),
  path('reserve/<int:pk>/edit/', views.ReserveTransferUpdateView.as_view(), name='reserve_edit'),
  path('reserve/<int:pk>/delete/', views.ReserveTransferDeleteView.as_view(), name='reserve_delete'),
  path('utilities/', views.UtilitiesDashboardView.as_view(), name='utilities'),
  path('utilities/create/', views.UtilitiesOperationCreateView.as_view(), name='utilities_create'),
  path('utilities/<int:pk>/', views.UtilitiesOperationDetailView.as_view(), name='utilities_detail'),
  path('utilities/<int:pk>/edit/', views.UtilitiesOperationUpdateView.as_view(), name='utilities_edit'),
  path('utilities/<int:pk>/delete/', views.UtilitiesOperationDeleteView.as_view(), name='utilities_delete'),
  path('export/', views.FinanceExportView.as_view(), name='export'),
]
