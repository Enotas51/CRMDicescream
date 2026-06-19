from django.utils import timezone


def site_context(request):
  return {
    'site_name': 'DiceScream Fin',
    'today': timezone.localdate(),
  }
