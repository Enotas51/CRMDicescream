from django.urls import path

from . import views

app_name = 'calendar_app'

urlpatterns = [
  path('', views.CalendarView.as_view(), name='calendar'),
  path('create/', views.EventCreateView.as_view(), name='create'),
  path('<int:pk>/', views.EventDetailView.as_view(), name='detail'),
  path('<int:pk>/edit/', views.EventUpdateView.as_view(), name='edit'),
  path('<int:pk>/delete/', views.EventDeleteView.as_view(), name='delete'),
]
