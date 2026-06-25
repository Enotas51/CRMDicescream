from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
  path('', views.ProjectListView.as_view(), name='list'),
  path('create/', views.ProjectCreateView.as_view(), name='create'),
  path('ozon/fetch/', views.fetch_ozon_product_view, name='ozon_fetch'),
  path('<int:pk>/', views.ProjectDetailView.as_view(), name='detail'),
  path('<int:pk>/quick-update/', views.project_quick_update_view, name='quick_update'),
  path('<int:pk>/equipment/add/', views.project_equipment_add_view, name='equipment_add'),
  path('<int:pk>/equipment/<int:equipment_pk>/update/', views.project_equipment_update_view, name='equipment_update'),
  path('<int:pk>/equipment/<int:equipment_pk>/delete/', views.project_equipment_delete_view, name='equipment_delete'),
  path('<int:pk>/equipment/<int:equipment_pk>/toggle-ordered/', views.project_equipment_toggle_ordered_view, name='equipment_toggle_ordered'),
  path('<int:pk>/equipment/<int:equipment_pk>/toggle-received/', views.project_equipment_toggle_received_view, name='equipment_toggle_received'),
  path('<int:pk>/files/upload/', views.project_file_upload_view, name='file_upload'),
  path('<int:pk>/files/<int:file_pk>/delete/', views.project_file_delete_view, name='file_delete'),
  path('<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='edit'),
  path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='delete'),
]
