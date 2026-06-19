from django.apps import AppConfig


class DebtsConfig(AppConfig):
  default_auto_field = 'django.db.models.BigAutoField'
  name = 'debts'
  verbose_name = 'Задолженности'

  def ready(self):
    import debts.signals  # noqa: F401
