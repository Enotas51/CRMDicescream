from django.core.management.base import BaseCommand

from finance.models import FinanceCategory, TransactionType


DEFAULT_CATEGORIES = [
  ('Зарплата', TransactionType.INCOME, '#22c55e'),
  ('Продажи', TransactionType.INCOME, '#16a34a'),
  ('Прочий доход', TransactionType.INCOME, '#4ade80'),
  ('Аренда', TransactionType.EXPENSE, '#ef4444'),
  ('Закупки', TransactionType.EXPENSE, '#f97316'),
  ('Зарплаты', TransactionType.EXPENSE, '#dc2626'),
  ('Маркетинг', TransactionType.EXPENSE, '#8b5cf6'),
  ('Прочие расходы', TransactionType.EXPENSE, '#64748b'),
]


class Command(BaseCommand):
  help = 'Создаёт стандартные категории финансов'

  def handle(self, *args, **options):
    created = 0
    for name, ttype, color in DEFAULT_CATEGORIES:
      _, was_created = FinanceCategory.objects.get_or_create(
        name=name,
        transaction_type=ttype,
        defaults={'color': color},
      )
      if was_created:
        created += 1
    self.stdout.write(self.style.SUCCESS(f'Готово. Создано категорий: {created}'))
