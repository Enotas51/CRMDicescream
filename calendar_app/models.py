from django.db import models
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from projects.models import Project


class Event(TimeStampedModel):
  title = models.CharField(_('Название'), max_length=255)
  description = models.TextField(_('Описание'), blank=True)
  start = models.DateTimeField(_('Начало'))
  end = models.DateTimeField(_('Окончание'), null=True, blank=True)
  all_day = models.BooleanField(_('Весь день'), default=False)
  project = models.ForeignKey(
    Project,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='events',
    verbose_name=_('Проект'),
  )
  participants = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    blank=True,
    related_name='calendar_events',
    verbose_name=_('Участники'),
  )
  color = models.CharField(_('Цвет'), max_length=7, default='#8b5cf6')
  location = models.CharField(_('Место'), max_length=255, blank=True)

  class Meta:
    verbose_name = _('Событие')
    verbose_name_plural = _('События')
    ordering = ['start']

  def __str__(self):
    return self.title

  def get_absolute_url(self):
    return reverse_lazy('calendar_app:detail', kwargs={'pk': self.pk})
