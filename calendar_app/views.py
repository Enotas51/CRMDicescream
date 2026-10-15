import calendar as cal_module
from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import ApprovedUserMixin, CanEditMixin, user_can_edit_object
from tasks.models import Task
from .event_copy import create_event_copies, parse_copy_dates, weekly_dates
from .forms import EventForm
from .holidays import get_russian_holidays
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

    cal = cal_module.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)
    visible_start = weeks[0][0]
    visible_end = weeks[-1][-1]

    events = Event.objects.filter(
      start__date__gte=visible_start,
      start__date__lte=visible_end,
    )
    upcoming_events = Event.objects.filter(
      start__date__gte=today,
      start__date__lte=today + timedelta(days=6),
    ).select_related('project').prefetch_related('participants').order_by('start')
    upcoming_tasks = Task.objects.filter(
      due_date__gte=today,
      due_date__lte=today + timedelta(days=6),
    ).exclude(status='done').select_related('project', 'assignee').order_by('due_date', 'created_at')
    tasks = Task.objects.filter(
      due_date__gte=visible_start,
      due_date__lte=visible_end,
    ).exclude(status='done')

    events_by_date = {}
    for event in events:
      event.can_edit = user_can_edit_object(self.request.user, event)
      day_key = event.start.date()
      events_by_date.setdefault(day_key, []).append(event)

    for event in upcoming_events:
      event.can_edit = user_can_edit_object(self.request.user, event)

    tasks_by_date = {}
    for task in tasks:
      if task.due_date:
        tasks_by_date.setdefault(task.due_date, []).append(task)

    holidays_by_date = get_russian_holidays(year)

    calendar_weeks = []
    for week in weeks:
      week_data = []
      for day in week:
        week_data.append({
          'date': day,
          'in_month': day.month == month,
          'is_weekend': day.weekday() >= 5,
          'events': events_by_date.get(day, []),
          'tasks': tasks_by_date.get(day, []),
          'holidays': ([{'name': holidays_by_date[day]}]
                       if day in holidays_by_date else []),
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
      'upcoming_events': upcoming_events,
      'upcoming_tasks': upcoming_tasks,
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

  def get_initial(self):
    initial = super().get_initial()
    requested_date = self.request.GET.get('date')
    if not requested_date:
      return initial
    try:
      event_date = date.fromisoformat(requested_date)
    except ValueError:
      return initial
    initial['start'] = timezone.make_aware(datetime.combine(event_date, time(hour=9)))
    initial['end'] = timezone.make_aware(datetime.combine(event_date, time(hour=18)))
    return initial

  def form_valid(self, form):
    recurrence_type = self.request.POST.get('recurrence_type', 'none')
    weekly_until = None
    if recurrence_type == 'weekly':
      try:
        weekly_until = date.fromisoformat(self.request.POST.get('recurrence_until', ''))
      except ValueError:
        form.add_error(None, 'Для еженедельного повторения укажи дату окончания.')
        return self.form_invalid(form)
      if weekly_until <= timezone.localtime(form.instance.start).date():
        form.add_error(None, 'Дата окончания должна быть позже даты первого события.')
        return self.form_invalid(form)

    form.instance.created_by = self.request.user
    response = super().form_valid(form)
    if recurrence_type == 'weekly':
      from uuid import uuid4
      recurrence_key = uuid4()
      self.object.recurrence_key = recurrence_key
      self.object.recurrence_until = weekly_until
      self.object.save(update_fields=['recurrence_key', 'recurrence_until'])
      create_event_copies(
        self.object,
        weekly_dates(timezone.localtime(self.object.start).date(), weekly_until),
        self.request.user,
        recurrence_key=recurrence_key,
        recurrence_until=weekly_until,
      )
    elif recurrence_type == 'dates':
      create_event_copies(
        self.object,
        parse_copy_dates(self.request.POST.getlist('copy_date')),
        self.request.user,
      )
    return response

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
    response = super().form_valid(form)
    create_event_copies(
      self.object,
      parse_copy_dates(self.request.POST.getlist('copy_date')),
      self.request.user,
    )
    return response

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
