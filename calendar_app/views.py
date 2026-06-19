import calendar as cal_module
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import ApprovedUserMixin, CanEditMixin, user_can_edit_object
from tasks.models import Task
from .forms import EventForm
from .models import Event


class CalendarView(ApprovedUserMixin, ListView):
  model = Event
  template_name = 'calendar_app/calendar.html'
  context_object_name = 'events'

  def get_queryset(self):
    return Event.objects.select_related('project').prefetch_related('participants')

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    today = timezone.localdate()
    year = int(self.request.GET.get('year', today.year))
    month = int(self.request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    if month == 12:
      last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
      last_day = date(year, month + 1, 1) - timedelta(days=1)

    events = Event.objects.filter(
      start__date__gte=first_day,
      start__date__lte=last_day,
    )
    tasks = Task.objects.filter(
      due_date__gte=first_day,
      due_date__lte=last_day,
    ).exclude(status='done')

    events_by_day = {}
    for event in events:
      day = event.start.date().day
      events_by_day.setdefault(day, []).append(event)

    tasks_by_day = {}
    for task in tasks:
      if task.due_date:
        tasks_by_day.setdefault(task.due_date.day, []).append(task)

    cal = cal_module.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)

    calendar_weeks = []
    for week in weeks:
      week_data = []
      for day in week:
        if day.month == month:
          week_data.append({
            'date': day,
            'events': events_by_day.get(day.day, []),
            'tasks': tasks_by_day.get(day.day, []),
          })
        else:
          week_data.append({
            'date': day,
            'events': [],
            'tasks': [],
          })
      calendar_weeks.append(week_data)

    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year

    month_names = [
      '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
      'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
    ]

    ctx.update({
      'year': year,
      'month': month,
      'month_name': month_names[month],
      'calendar_weeks': calendar_weeks,
      'today': today,
      'prev_year': prev_year,
      'prev_month': prev_month,
      'next_year': next_year,
      'next_month': next_month,
      'can_edit': self.request.user.can_edit,
    })
    return ctx


class EventDetailView(ApprovedUserMixin, DetailView):
  model = Event
  template_name = 'calendar_app/detail.html'
  context_object_name = 'event'

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx['can_edit'] = user_can_edit_object(self.request.user, self.object)
    return ctx


class EventCreateView(CanEditMixin, CreateView):
  model = Event
  form_class = EventForm
  template_name = 'calendar_app/form.html'

  def form_valid(self, form):
    form.instance.created_by = self.request.user
    messages.success(self.request, 'Событие создано.')
    return super().form_valid(form)

  def get_success_url(self):
    return reverse_lazy('calendar_app:calendar')


class EventUpdateView(CanEditMixin, UpdateView):
  model = Event
  form_class = EventForm
  template_name = 'calendar_app/form.html'

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and not user_can_edit_object(request.user, self.object):
      messages.error(request, 'Недостаточно прав.')
      return redirect('calendar_app:detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)

  def form_valid(self, form):
    messages.success(self.request, 'Событие обновлено.')
    return super().form_valid(form)

  def get_success_url(self):
    return reverse_lazy('calendar_app:calendar')


class EventDeleteView(CanEditMixin, DeleteView):
  model = Event
  template_name = 'calendar_app/confirm_delete.html'
  success_url = reverse_lazy('calendar_app:calendar')

  def dispatch(self, request, *args, **kwargs):
    self.object = self.get_object()
    if not request.user.is_admin and self.object.created_by != request.user:
      messages.error(request, 'Недостаточно прав.')
      return redirect('calendar_app:detail', pk=self.object.pk)
    return super().dispatch(request, *args, **kwargs)
