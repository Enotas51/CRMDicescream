from django.utils import timezone


def site_context(request):
  return {
    'site_name': 'DS CRM',
    'today': timezone.localdate(),
  }
