from django.db import models
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class ProjectStatus(models.TextChoices):
  DRAFT = 'draft', _('Черновик')
  ACTIVE = 'active', _('В работе')
  ON_HOLD = 'on_hold', _('Приостановлен')
  COMPLETED = 'completed', _('Завершён')
  CANCELLED = 'cancelled', _('Отменён')


class Project(TimeStampedModel):
  name = models.CharField(_('Название'), max_length=200)
  description = models.TextField(_('Описание'), blank=True)
  status = models.CharField(
    _('Статус'),
    max_length=20,
    choices=ProjectStatus.choices,
    default=ProjectStatus.DRAFT,
  )
  start_date = models.DateField(_('Дата начала'), null=True, blank=True)
  end_date = models.DateField(_('Дата окончания'), null=True, blank=True)
  budget = models.DecimalField(_('Бюджет'), max_digits=12, decimal_places=2, default=0)
  members = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    blank=True,
    related_name='projects',
    verbose_name=_('Участники'),
  )
  color = models.CharField(_('Цвет'), max_length=7, default='#3b82f6')

  class Meta:
    verbose_name = _('Проект')
    verbose_name_plural = _('Проекты')
    ordering = ['-updated_at']

  def __str__(self):
    return self.name

  def get_absolute_url(self):
    return reverse_lazy('projects:detail', kwargs={'pk': self.pk})

  @property
  def task_count(self):
    return self.tasks.count()

  @property
  def completed_task_count(self):
    return self.tasks.filter(status='done').count()
