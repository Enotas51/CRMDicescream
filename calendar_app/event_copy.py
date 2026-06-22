import re
from datetime import date, datetime

from django.utils import timezone

from .models import Event


def parse_copy_dates(raw_values):
  """Parse date strings from form inputs (YYYY-MM-DD, DD.MM.YYYY)."""
  dates = []
  seen = set()
  if not raw_values:
    return dates

  for raw in raw_values:
    if not raw:
      continue
    for chunk in re.split(r'[\s,;]+', str(raw).strip()):
      chunk = chunk.strip()
      if not chunk:
        continue
      parsed = _parse_single_date(chunk)
      if parsed and parsed not in seen:
        seen.add(parsed)
        dates.append(parsed)
  return sorted(dates)


def _parse_single_date(value):
  for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d.%m.%y'):
    try:
      return datetime.strptime(value, fmt).date()
    except ValueError:
      continue
  return None


def shift_to_date(dt, target_date):
  if dt is None:
    return None
  local_dt = timezone.localtime(dt)
  return local_dt.replace(
    year=target_date.year,
    month=target_date.month,
    day=target_date.day,
  )


def create_event_copies(source_event, target_dates, created_by):
  if not target_dates:
    return []

  participant_ids = list(source_event.participants.values_list('pk', flat=True))
  duration = None
  if source_event.start and source_event.end:
    duration = source_event.end - source_event.start

  source_date = timezone.localtime(source_event.start).date() if source_event.start else None
  copies = []

  for target_date in target_dates:
    if source_date and target_date == source_date:
      continue

    new_start = shift_to_date(source_event.start, target_date)
    new_end = None
    if source_event.end:
      new_end = shift_to_date(source_event.end, target_date)
    elif duration and new_start:
      new_end = new_start + duration

    copy = Event.objects.create(
      title=source_event.title,
      description=source_event.description,
      start=new_start,
      end=new_end,
      all_day=source_event.all_day,
      project=source_event.project,
      color=source_event.color,
      location=source_event.location,
      created_by=created_by,
    )
    if participant_ids:
      copy.participants.set(participant_ids)
    copies.append(copy)

  return copies
