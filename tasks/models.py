from django.db import models
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from projects.models import Project


class TaskStatus(models.TextChoices):
  TODO = 'todo', _('К выполнению')
  IN_PROGRESS = 'in_progress', _('В работе')
  REVIEW = 'review', _('На проверке')
  DONE = 'done', _('Готово')


class TaskPriority(models.TextChoices):
  LOW = 'low', _('Низкий')
  MEDIUM = 'medium', _('Средний')
  HIGH = 'high', _('Высокий')
  URGENT = 'urgent', _('Срочный')


class Task(TimeStampedModel):
  title = models.CharField(_('Заголовок'), max_length=255)
  description = models.TextField(_('Описание'), blank=True)
  project = models.ForeignKey(
    Project,
    on_delete=models.CASCADE,
    related_name='tasks',
    verbose_name=_('Проект'),
    null=True,
    blank=True,
  )
  status = models.CharField(
    _('Статус'),
    max_length=20,
    choices=TaskStatus.choices,
    default=TaskStatus.TODO,
  )
  priority = models.CharField(
    _('Приоритет'),
    max_length=20,
    choices=TaskPriority.choices,
    default=TaskPriority.MEDIUM,
  )
  assignee = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='assigned_tasks',
    verbose_name=_('Исполнитель'),
  )
  due_date = models.DateField(_('Срок'), null=True, blank=True)
  order = models.PositiveIntegerField(_('Порядок'), default=0)

  class Meta:
    verbose_name = _('Задача')
    verbose_name_plural = _('Задачи')
    ordering = ['order', '-priority', 'due_date']

  def __str__(self):
    return self.title

  def get_absolute_url(self):
    return reverse_lazy('tasks:detail', kwargs={'pk': self.pk})
