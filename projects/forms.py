from django import forms

from .models import Project, ProjectStatus


class ProjectForm(forms.ModelForm):
  class Meta:
    model = Project
    fields = [
      'name', 'description', 'status', 'start_date', 'end_date',
      'budget', 'members', 'color',
    ]
    widgets = {
      'name': forms.TextInput(attrs={'class': 'form-control'}),
      'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
      'status': forms.Select(attrs={'class': 'form-select'}),
      'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
      'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
      'budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
      'members': forms.SelectMultiple(attrs={'class': 'form-select'}),
      'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
    }
    labels = {
      'name': 'Название',
      'description': 'Описание',
      'status': 'Статус',
      'start_date': 'Дата начала',
      'end_date': 'Дата окончания',
      'budget': 'Бюджет',
      'members': 'Участники',
      'color': 'Цвет',
    }
