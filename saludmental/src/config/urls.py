from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.shortcuts import redirect
from django.utils import translation
from django.conf import settings
from django.conf.urls.static import static

def redirect_to_language(request):
    lang = translation.get_language_from_request(request)
    return redirect(f'/{lang}/')

urlpatterns = [
    path('', redirect_to_language),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('', include('apps.usuarios.urls')),
    path('foro/', include('apps.foro.urls')),
    path('podcast/', include('apps.podcast.urls')),
    path('agenda/', include('apps.agenda.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
