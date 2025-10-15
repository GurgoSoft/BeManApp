from django.shortcuts import render
from django.utils import timezone
from .models import Evento

def index(request):
    ahora = timezone.now()
    eventos = Evento.objects.order_by('fecha')
    proximos = eventos.filter(fecha__gte=ahora)
    pasados = eventos.filter(fecha__lt=ahora).order_by('-fecha')[:10]
    return render(request, 'agenda/index.html', {
        'proximos': proximos,
        'pasados': pasados,
    })
