from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
  path('', views.ProjectListView.as_view(), name='list'),
  path('create/', views.ProjectCreateView.as_view(), name='create'),
  path('ozon/fetch/', views.fetch_ozon_product_view, name='ozon_fetch'),
  path('<int:pk>/', views.ProjectDetailView.as_view(), name='detail'),
  path('<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='edit'),
  path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='delete'),
]
