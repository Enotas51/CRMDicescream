from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
  created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
  updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
  created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='%(class)s_created',
    verbose_name=_('Автор'),
  )

  class Meta:
    abstract = True
