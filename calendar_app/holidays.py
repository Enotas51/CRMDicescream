"""Russian public holidays used as read-only calendar entries.

Fixed dates come from Article 112 of the Labour Code.  Days moved by the
Government are deliberately kept separately, as they change from year to year.
"""

from datetime import date


FIXED_HOLIDAYS = {
  (1, 1): 'Новогодние каникулы',
  (1, 2): 'Новогодние каникулы',
  (1, 3): 'Новогодние каникулы',
  (1, 4): 'Новогодние каникулы',
  (1, 5): 'Новогодние каникулы',
  (1, 6): 'Новогодние каникулы',
  (1, 7): 'Рождество Христово',
  (1, 8): 'Новогодние каникулы',
  (2, 23): 'День защитника Отечества',
  (3, 8): 'Международный женский день',
  (5, 1): 'Праздник Весны и Труда',
  (5, 9): 'День Победы',
  (6, 12): 'День России',
  (11, 4): 'День народного единства',
}

# Officially moved days off.  Add a new year once its Government decree is out.
MOVED_DAYS_OFF = {
  2026: {
    date(2026, 3, 9): 'Перенесённый выходной',
    date(2026, 5, 11): 'Перенесённый выходной',
    date(2026, 12, 31): 'Перенесённый выходной',
  },
}


def get_russian_holidays(year):
  """Return a date-to-name mapping for federal holidays in a given year."""
  holidays = {
    date(year, month, day): name
    for (month, day), name in FIXED_HOLIDAYS.items()
  }
  holidays.update(MOVED_DAYS_OFF.get(year, {}))
  return holidays
