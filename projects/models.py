from decimal import Decimal

from django.db import models
from django.conf import settings
from django.db.models import F, Sum
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

  @property
  def equipment_total(self):
    total = self.equipment.aggregate(
      total=Sum(F('price') * F('quantity')),
    )['total']
    return total or Decimal('0')


class ProjectEquipment(models.Model):
  project = models.ForeignKey(
    Project,
    on_delete=models.CASCADE,
    related_name='equipment',
    verbose_name=_('Проект'),
  )
  name = models.CharField(_('Наименование'), max_length=500)
  price = models.DecimalField(_('Цена'), max_digits=12, decimal_places=2)
  quantity = models.PositiveIntegerField(_('Количество'), default=1)
  is_ordered = models.BooleanField(_('Заказал'), default=False)
  is_received = models.BooleanField(_('Получил'), default=False)
  ozon_url = models.URLField(_('Ссылка OZON'), blank=True, max_length=1000)
  ozon_product_id = models.CharField(_('ID товара OZON'), max_length=32, blank=True)

  class Meta:
    verbose_name = _('Оборудование')
    verbose_name_plural = _('Оборудование')
    ordering = ['id']

  def __str__(self):
    return f'{self.name} × {self.quantity}'

  @property
  def total_price(self):
    return self.price * self.quantity
