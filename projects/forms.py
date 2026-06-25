from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Project, ProjectEquipment, ProjectFile, ProjectStatus

MAX_PROJECT_FILE_SIZE = 25 * 1024 * 1024


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


class ProjectEquipmentForm(forms.ModelForm):
  class Meta:
    model = ProjectEquipment
    fields = [
      'name', 'price', 'quantity', 'ozon_url',
    ]
    widgets = {
      'name': forms.TextInput(attrs={
        'class': 'form-control equipment-name',
        'placeholder': 'Наименование товара',
      }),
      'price': forms.NumberInput(attrs={
        'class': 'form-control equipment-price',
        'step': '0.01',
        'min': '0',
      }),
      'quantity': forms.NumberInput(attrs={
        'class': 'form-control equipment-quantity',
        'min': '1',
      }),
      'ozon_url': forms.URLInput(attrs={
        'class': 'form-control equipment-ozon-url',
        'placeholder': 'https://www.ozon.ru/product/...',
      }),
    }
    labels = {
      'name': 'Наименование',
      'price': 'Цена, ₽',
      'quantity': 'Кол-во',
      'ozon_url': 'Ссылка OZON',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['name'].required = False
    self.fields['price'].required = False
    self.fields['quantity'].required = False

  def clean(self):
    cleaned = super().clean()
    if cleaned.get('DELETE'):
      return cleaned

    name = (cleaned.get('name') or '').strip()
    price = cleaned.get('price')
    ozon_url = (cleaned.get('ozon_url') or '').strip()
    quantity = cleaned.get('quantity') or 1

    has_data = any([
      name,
      price is not None,
      ozon_url,
      quantity and quantity != 1,
    ])

    if not has_data:
      cleaned['name'] = ''
      return cleaned

    if not name:
      self.add_error('name', 'Укажите наименование или подтяните товар с OZON.')
    if price is None:
      self.add_error('price', 'Укажите цену.')
    if not quantity or quantity < 1:
      self.add_error('quantity', 'Количество должно быть не меньше 1.')

    cleaned['name'] = name
    cleaned['ozon_url'] = ozon_url
    cleaned['quantity'] = quantity or 1
    return cleaned


class BaseProjectEquipmentFormSet(BaseInlineFormSet):
  def save(self, commit=True):
    instances = super().save(commit=False)
    for instance in self.deleted_objects:
      if instance.pk:
        instance.delete()
    for instance in instances:
      if not (instance.name or '').strip():
        continue
      if commit:
        instance.save()
    return instances


ProjectEquipmentFormSet = inlineformset_factory(
  Project,
  ProjectEquipment,
  form=ProjectEquipmentForm,
  formset=BaseProjectEquipmentFormSet,
  extra=1,
  can_delete=True,
)


class ProjectQuickUpdateForm(forms.ModelForm):
  class Meta:
    model = Project
    fields = ['status', 'description', 'budget', 'start_date', 'end_date']
    widgets = {
      'status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
      'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
      'budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
      'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
      'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    }
    labels = {
      'status': 'Статус',
      'description': 'Описание',
      'budget': 'Бюджет, ₽',
      'start_date': 'Дата начала',
      'end_date': 'Дата окончания',
    }


class ProjectEquipmentQuickForm(forms.ModelForm):
  class Meta:
    model = ProjectEquipment
    fields = ['name', 'price', 'quantity', 'ozon_url']
    widgets = {
      'name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Наименование'}),
      'price': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0'}),
      'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1'}),
      'ozon_url': forms.URLInput(attrs={
        'class': 'form-control form-control-sm',
        'placeholder': 'https://www.ozon.ru/product/...',
      }),
    }
    labels = {
      'name': 'Наименование',
      'price': 'Цена, ₽',
      'quantity': 'Кол-во',
      'ozon_url': 'Ссылка OZON',
    }


class ProjectEquipmentEditForm(forms.ModelForm):
  class Meta:
    model = ProjectEquipment
    fields = ['name', 'price', 'quantity', 'ozon_url']
    widgets = {
      'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
      'price': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0'}),
      'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1'}),
      'ozon_url': forms.URLInput(attrs={'class': 'form-control form-control-sm'}),
    }


class ProjectFileForm(forms.ModelForm):
  class Meta:
    model = ProjectFile
    fields = ['file', 'name']
    widgets = {
      'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
      'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Необязательно'}),
    }
    labels = {
      'file': 'Файл',
      'name': 'Название',
    }

  def clean_file(self):
    uploaded = self.cleaned_data.get('file')
    if uploaded and uploaded.size > MAX_PROJECT_FILE_SIZE:
      raise forms.ValidationError('Файл слишком большой (максимум 25 МБ).')
    return uploaded
