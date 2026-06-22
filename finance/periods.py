from calendar import monthrange
from datetime import date

from django.utils import timezone

MONTH_NAMES = [
  '',
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
]


def parse_finance_period(request):
  """Return (year, month, start_date, end_date, all_time)."""
  all_time = request.GET.get('all') == '1'
  if all_time:
    return None, None, None, None, True

  today = timezone.localdate()
  try:
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
  except (TypeError, ValueError):
    year, month = today.year, today.month

  if month < 1 or month > 12:
    month = today.month
  if year < 2000 or year > 2100:
    year = today.year

  start = date(year, month, 1)
  end = date(year, month, monthrange(year, month)[1])
  return year, month, start, end, False


def filter_queryset_by_period(qs, start, end, all_time, date_field='date'):
  if all_time or not start or not end:
    return qs
  return qs.filter(**{f'{date_field}__gte': start, f'{date_field}__lte': end})


def build_month_choices(count=24):
  today = timezone.localdate()
  choices = []
  year, month = today.year, today.month
  for _ in range(count):
    choices.append({
      'year': year,
      'month': month,
      'label': f'{MONTH_NAMES[month]} {year}',
    })
    month -= 1
    if month < 1:
      month = 12
      year -= 1
  return choices


def period_label(year, month, all_time):
  if all_time:
    return 'За всё время'
  if year and month:
    return f'{MONTH_NAMES[month]} {year}'
  return '—'


def period_query_string(year, month, all_time, extra=None):
  if all_time:
    parts = ['all=1']
  else:
    parts = [f'year={year}', f'month={month}']
  if extra:
    parts.extend(extra)
  return '&'.join(parts)
