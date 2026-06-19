from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
  path('', views.TaskListView.as_view(), name='list'),
  path('kanban/', views.TaskKanbanView.as_view(), name='kanban'),
  path('create/', views.TaskCreateView.as_view(), name='create'),
  path('<int:pk>/', views.TaskDetailView.as_view(), name='detail'),
  path('<int:pk>/edit/', views.TaskUpdateView.as_view(), name='edit'),
  path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='delete'),
  path('<int:pk>/status/', views.task_update_status, name='update_status'),
]
