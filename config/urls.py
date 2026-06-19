from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
  path('admin/', admin.site.urls),
  path('accounts/', include('allauth.urls')),
  path('accounts/', include('accounts.urls')),
  path('projects/', include('projects.urls')),
  path('tasks/', include('tasks.urls')),
  path('calendar/', include('calendar_app.urls')),
  path('debts/', include('debts.urls')),
  path('finance/', include('finance.urls')),
  path('manifest.json', TemplateView.as_view(
    template_name='manifest.json',
    content_type='application/manifest+json',
  )),
  path('sw.js', TemplateView.as_view(
    template_name='sw.js',
    content_type='application/javascript',
  )),
  path('', include('core.urls')),
]

if settings.DEBUG:
  urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'DiceScream CRM'
admin.site.site_title = 'DiceScream CRM'
admin.site.index_title = 'Администрирование'
