from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.models import ApprovalStatus, Role

User = get_user_model()


class Command(BaseCommand):
  help = 'Создаёт или обновляет мастер-аккаунт администратора'

  def handle(self, *args, **options):
    username = settings.MASTER_USERNAME
    password = settings.MASTER_PASSWORD
    email = settings.MASTER_EMAIL

    if not password:
      self.stderr.write(self.style.ERROR('MASTER_PASSWORD не задан в .env'))
      return

    user, created = User.objects.get_or_create(
      username=username,
      defaults={
        'email': email,
        'role': Role.ADMIN,
        'approval_status': ApprovalStatus.APPROVED,
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
      },
    )
    user.set_password(password)
    user.role = Role.ADMIN
    user.approval_status = ApprovalStatus.APPROVED
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.email = email
    user.save()

    action = 'создан' if created else 'обновлён'
    self.stdout.write(self.style.SUCCESS(f'Мастер-аккаунт «{username}» {action}.'))
