from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.utils import translation
from django.utils.translation import get_language, gettext as _
from django.conf import settings
from django.contrib import messages
import re

def home(request):
    return render(request, "home.html")

def handler404(request, exception=None):
    """
    Handler personalizado para errores 404.
    Redirige a la página principal con un mensaje amigable.
    """
    messages.warning(request, _("La página que buscas no está disponible o no existe."))
    return redirect('home')

def handler500(request):
    """
    Handler personalizado para errores 500.
    Redirige a la página principal con un mensaje de error.
    """
    messages.error(request, _("Ha ocurrido un error en el servidor. Por favor, intenta de nuevo más tarde."))
    return redirect('home')

def set_language(request):
    """
    Vista personalizada para cambiar el idioma.
    Redirige correctamente con los i18n_patterns.
    """
    if request.method == 'POST':
        lang_code = request.POST.get('language', None)
        next_url = request.POST.get('next', '/')
        
        # Validar que el idioma sea válido
        if lang_code and lang_code in dict(settings.LANGUAGES):
            # Activar el idioma
            translation.activate(lang_code)
            
            # Guardar en la sesión
            request.session['django_language'] = lang_code
            
            # Construir la URL con el nuevo idioma
            # Remover el prefijo de idioma actual de la URL
            current_lang = get_language()
            lang_pattern = r'^/(' + '|'.join([lang[0] for lang in settings.LANGUAGES]) + r')/'
            
            # Si la URL actual tiene prefijo de idioma, reemplazarlo
            if re.match(lang_pattern, next_url):
                # Reemplazar el prefijo de idioma
                next_url = re.sub(lang_pattern, f'/{lang_code}/', next_url)
            else:
                # Agregar el prefijo de idioma
                next_url = f'/{lang_code}{next_url}'
            
            response = HttpResponseRedirect(next_url)
            # También guardar en cookie
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
            return response
    
    # Si no es POST o algo falla, redirigir a home
    return HttpResponseRedirect('/')
