from django.shortcuts import redirect
from django.urls import reverse


class ApprovalRequiredMiddleware:
  ALLOWED_PREFIXES = (
    '/accounts/',
    '/admin/',
    '/static/',
    '/media/',
    '/manifest.json',
    '/sw.js',
    '/offline/',
  )

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    if request.user.is_authenticated and not request.user.is_approved:
      path = request.path
      if not any(path.startswith(p) for p in self.ALLOWED_PREFIXES):
        pending_url = reverse('accounts:pending')
        if path != pending_url:
          return redirect('accounts:pending')
    return self.get_response(request)
