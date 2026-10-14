from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth import get_user_model

from .models import Role

User = get_user_model()


class CRMSignupForm(SignupForm):
  first_name = forms.CharField(label='Имя', max_length=150, required=False)
  last_name = forms.CharField(label='Фамилия', max_length=150, required=False)

  def save(self, request):
    user = super().save(request)
    user.first_name = self.cleaned_data.get('first_name', '')
    user.last_name = self.cleaned_data.get('last_name', '')
    user.save(update_fields=['first_name', 'last_name'])
    return user


class UserApprovalForm(forms.ModelForm):
  class Meta:
    model = User
    fields = ['role', 'approval_status', 'is_active', 'first_name', 'last_name', 'email', 'phone', 'telegram', 'gmail', 'bio']
    labels = {
      'role': 'Роль',
      'approval_status': 'Статус',
      'is_active': 'Активен',
      'first_name': 'Имя',
      'last_name': 'Фамилия',
      'email': 'Email',
      'phone': 'Телефон',
      'telegram': 'Telegram',
      'gmail': 'Gmail',
      'bio': 'Краткая информация',
    }

  def clean(self):
    cleaned = super().clean()
    if cleaned.get('approval_status') == 'approved' and not cleaned.get('role'):
      self.add_error('role', 'Укажите роль для одобренного пользователя.')
    return cleaned


class ProfileForm(forms.ModelForm):
  class Meta:
    model = User
    fields = ['first_name', 'last_name', 'email', 'avatar_file', 'phone', 'telegram', 'gmail', 'bio']
    labels = {
      'first_name': 'Имя', 'last_name': 'Фамилия', 'email': 'E-mail',
      'avatar_file': 'Фото профиля', 'phone': 'Телефон',
      'telegram': 'Telegram', 'gmail': 'Gmail', 'bio': 'Краткая информация',
    }
    widgets = {
      'avatar_file': forms.FileInput(attrs={'class': 'profile-avatar-file', 'accept': 'image/jpeg,image/png,image/webp'}),
      'bio': forms.Textarea(attrs={'rows': 4}),
    }
