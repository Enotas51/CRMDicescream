from django import forms

from projects.models import Project
from .models import Task, TaskPriority, TaskStatus


class TaskForm(forms.ModelForm):
  class Meta:
    model = Task
    fields = [
      'title', 'description', 'project', 'status', 'priority',
      'assignee', 'due_date',
    ]
    widgets = {
      'title': forms.TextInput(attrs={'class': 'form-control'}),
      'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
      'project': forms.Select(attrs={'class': 'form-select'}),
      'status': forms.Select(attrs={'class': 'form-select'}),
      'priority': forms.Select(attrs={'class': 'form-select'}),
      'assignee': forms.Select(attrs={'class': 'form-select'}),
      'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    }
    labels = {
      'title': 'Заголовок',
      'description': 'Описание',
      'project': 'Проект',
      'status': 'Статус',
      'priority': 'Приоритет',
      'assignee': 'Исполнитель',
      'due_date': 'Срок',
    }


class TaskStatusForm(forms.ModelForm):
  class Meta:
    model = Task
    fields = ['status']
    widgets = {
      'status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
    }
