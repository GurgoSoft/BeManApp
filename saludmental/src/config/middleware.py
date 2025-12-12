from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import Http404


class Custom404Middleware:
    """
    Middleware para capturar errores 404 y redirigir a home con mensaje.
    Funciona incluso en modo DEBUG.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Si es un 404, redirigir a home con mensaje
        if response.status_code == 404:
            messages.warning(request, _("La página que buscas no está disponible o no existe."))
            return redirect('home')
        
        return response

    def process_exception(self, request, exception):
        """
        Capturar excepciones Http404 antes de que lleguen a la respuesta.
        """
        if isinstance(exception, Http404):
            messages.warning(request, _("La página que buscas no está disponible o no existe."))
            return redirect('home')
        return None
