from django import forms

from projects.models import Project
from .models import Event


class EventForm(forms.ModelForm):
  class Meta:
    model = Event
    fields = [
      'title', 'description', 'start', 'end', 'all_day',
      'project', 'participants', 'color', 'location',
    ]
    widgets = {
      'title': forms.TextInput(attrs={'class': 'form-control'}),
      'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
      'start': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'class': 'form-control', 'type': 'datetime-local'}),
      'end': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'class': 'form-control', 'type': 'datetime-local'}),
      'all_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
      'project': forms.Select(attrs={'class': 'form-select'}),
      'participants': forms.SelectMultiple(attrs={'class': 'form-select'}),
      'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
      'location': forms.TextInput(attrs={'class': 'form-control'}),
    }
    labels = {
      'title': 'Название',
      'description': 'Описание',
      'start': 'Начало',
      'end': 'Окончание',
      'all_day': 'Весь день',
      'project': 'Проект',
      'participants': 'Участники',
      'color': 'Цвет',
      'location': 'Место',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['start'].input_formats = ['%Y-%m-%dT%H:%M']
    self.fields['end'].input_formats = ['%Y-%m-%dT%H:%M']

  def clean(self):
    cleaned = super().clean()
    start = cleaned.get('start')
    end = cleaned.get('end')
    if start and end and end < start:
      self.add_error('end', 'Окончание не может быть раньше начала.')
    return cleaned
