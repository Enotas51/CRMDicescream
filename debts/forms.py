from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory

from .models import Debt, DebtDebtor

User = get_user_model()


class DebtForm(forms.ModelForm):
  class Meta:
    model = Debt
    fields = [
      'title', 'description', 'utilities_amount',
      'creditor_user', 'creditor_name',
      'project', 'due_date',
    ]
    widgets = {
      'title': forms.TextInput(attrs={'class': 'form-control'}),
      'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
      'utilities_amount': forms.NumberInput(attrs={
        'class': 'form-control', 'step': '0.01', 'min': '0',
        'placeholder': '0 — если не удерживается',
      }),
      'creditor_user': forms.Select(attrs={'class': 'form-select'}),
      'creditor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Или введите имя вручную'}),
      'project': forms.Select(attrs={'class': 'form-select'}),
      'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    }
    labels = {
      'title': 'Название',
      'description': 'Описание',
      'utilities_amount': 'Коммунальные (с каждого платежа)',
      'creditor_user': 'Кредитор (из пользователей)',
      'creditor_name': 'Кредитор (вручную)',
      'project': 'Проект',
      'due_date': 'Срок погашения',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    users = User.objects.filter(approval_status='approved', is_active=True).order_by('username')
    self.fields['creditor_user'].queryset = users
    self.fields['creditor_user'].required = False
    self.fields['creditor_user'].empty_label = '— не выбран —'

  def clean(self):
    cleaned = super().clean()
    creditor_user = cleaned.get('creditor_user')
    creditor_name = (cleaned.get('creditor_name') or '').strip()

    if not creditor_user and not creditor_name:
      self.add_error('creditor_name', 'Укажите кредитора: выберите пользователя или введите имя.')
    return cleaned

  def save(self, commit=True):
    instance = super().save(commit=False)
    instance.sync_creditor_name()
    if commit:
      instance.save()
    return instance


class DebtDebtorForm(forms.ModelForm):
  class Meta:
    model = DebtDebtor
    fields = ['debtor_user', 'debtor_name', 'amount']
    widgets = {
      'debtor_user': forms.Select(attrs={'class': 'form-select debtor-user'}),
      'debtor_name': forms.TextInput(attrs={
        'class': 'form-control debtor-name',
        'placeholder': 'Имя вручную',
      }),
      'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
    }
    labels = {
      'debtor_user': 'Пользователь',
      'debtor_name': 'Имя вручную',
      'amount': 'Сумма долга',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['debtor_user'].queryset = User.objects.filter(
      approval_status='approved', is_active=True,
    ).order_by('username')
    self.fields['debtor_user'].required = False
    self.fields['debtor_user'].empty_label = '— не выбран —'

  def clean(self):
    cleaned = super().clean()
    if cleaned.get('DELETE'):
      return cleaned
    debtor_user = cleaned.get('debtor_user')
    debtor_name = (cleaned.get('debtor_name') or '').strip()
    amount = cleaned.get('amount')
    if not debtor_user and not debtor_name:
      raise forms.ValidationError('Укажите должника: пользователя или имя вручную.')
    if amount is None or amount <= 0:
      raise forms.ValidationError('Укажите сумму долга больше нуля.')
    if self.instance.pk and amount < self.instance.get_repaid_amount():
      raise forms.ValidationError(
        f'Сумма не может быть меньше уже погашенной ({self.instance.get_repaid_amount()} ₽).',
      )
    return cleaned

  def save(self, commit=True):
    instance = super().save(commit=False)
    instance.sync_name()
    if commit:
      instance.save()
    return instance


DebtDebtorFormSet = inlineformset_factory(
  Debt,
  DebtDebtor,
  form=DebtDebtorForm,
  extra=1,
  can_delete=True,
  min_num=1,
  validate_min=True,
)


class LinkDebtorForm(forms.Form):
  user = forms.ModelChoiceField(
    label='Пользователь',
    queryset=User.objects.filter(approval_status='approved', is_active=True).order_by('username'),
    widget=forms.Select(attrs={'class': 'form-select'}),
  )
