from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
  list_display = ('username', 'email', 'role', 'approval_status', 'is_active', 'date_joined')
  list_filter = ('role', 'approval_status', 'is_active')
  search_fields = ('username', 'email', 'first_name', 'last_name', 'yandex_id')
  fieldsets = BaseUserAdmin.fieldsets + (
    (_('CRM'), {'fields': ('role', 'approval_status', 'yandex_id', 'avatar_url', 'phone')}),
  )
  add_fieldsets = BaseUserAdmin.add_fieldsets + (
    (_('CRM'), {'fields': ('role', 'approval_status')}),
  )
