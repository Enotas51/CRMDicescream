from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    ADMIN = 'admin', _('Администратор')
    EDITOR = 'editor', _('Редактор')
    OBSERVER = 'observer', _('Наблюдатель')


class ApprovalStatus(models.TextChoices):
    PENDING = 'pending', _('Ожидает одобрения')
    APPROVED = 'approved', _('Одобрен')
    REJECTED = 'rejected', _('Отклонён')


class User(AbstractUser):
    role = models.CharField(
        _('Роль'),
        max_length=20,
        choices=Role.choices,
        default=Role.OBSERVER,
        blank=True,
    )
    approval_status = models.CharField(
        _('Статус одобрения'),
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    yandex_id = models.CharField(_('ID Яндекс'), max_length=64, blank=True, unique=True, null=True)
    avatar_url = models.URLField(_('Аватар'), blank=True)
    phone = models.CharField(_('Телефон'), max_length=20, blank=True)

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['username']

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_editor(self):
        return self.role == Role.EDITOR

    @property
    def is_observer(self):
        return self.role == Role.OBSERVER

    @property
    def is_approved(self):
        return self.approval_status == ApprovalStatus.APPROVED

    @property
    def can_edit(self):
        return self.is_approved and self.role in (Role.ADMIN, Role.EDITOR)

    @property
    def can_view(self):
        return self.is_approved

    def approve(self, role):
        self.approval_status = ApprovalStatus.APPROVED
        self.role = role
        self.is_active = True
        self.save(update_fields=['approval_status', 'role', 'is_active'])

    def reject(self):
        self.approval_status = ApprovalStatus.REJECTED
        self.is_active = False
        self.save(update_fields=['approval_status', 'is_active'])
