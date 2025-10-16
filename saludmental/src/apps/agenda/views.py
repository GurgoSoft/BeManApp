from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Evento, Inscripcion
from django import forms

def index(request):
    ahora = timezone.now()
    eventos = Evento.objects.order_by('fecha')
    proximos = eventos.filter(fecha__gte=ahora)
    pasados = eventos.filter(fecha__lt=ahora).order_by('-fecha')[:10]
    return render(request, 'agenda/index.html', {
        'proximos': proximos,
        'pasados': pasados,
    })


# ============ ADMIN ============
def _is_staff(u):
    return u.is_authenticated and u.is_staff


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = [
            'imagen', 'titulo', 'nombre', 'descripcion_corta',
            'lugar', 'fecha', 'precio'
        ]
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


@user_passes_test(_is_staff)
def admin_dashboard(request):
    ahora = timezone.now()
    eventos = Evento.objects.order_by('-fecha')
    usuarios_count = request.user.__class__.objects.count()
    inscripciones_count = Inscripcion.objects.count()
    proximos = eventos.filter(fecha__gte=ahora)[:6]
    pasados = eventos.filter(fecha__lt=ahora)[:6]
    return render(request, 'agenda/admin_dashboard.html', {
        'eventos': eventos[:10],
        'usuarios_count': usuarios_count,
        'inscripciones_count': inscripciones_count,
        'proximos': proximos,
        'pasados': pasados,
    })


@user_passes_test(_is_staff)
def admin_evento_list(request):
    eventos = Evento.objects.order_by('-fecha')
    return render(request, 'agenda/admin_evento_list.html', {'eventos': eventos})


@user_passes_test(_is_staff)
def admin_evento_create(request):
    if request.method == 'POST':
        form = EventoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Evento creado."))
            return redirect('admin_evento_list')
    else:
        form = EventoForm()
    return render(request, 'agenda/admin_evento_form.html', {'form': form, 'modo': 'crear'})


@user_passes_test(_is_staff)
def admin_evento_edit(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.method == 'POST':
        form = EventoForm(request.POST, request.FILES, instance=evento)
        if form.is_valid():
            form.save()
            messages.success(request, _("Evento actualizado."))
            return redirect('admin_evento_list')
    else:
        form = EventoForm(instance=evento)
    return render(request, 'agenda/admin_evento_form.html', {'form': form, 'modo': 'editar', 'evento': evento})


@user_passes_test(_is_staff)
def admin_evento_delete(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.method == 'POST':
        evento.delete()
        messages.success(request, _("Evento eliminado."))
        return redirect('admin_evento_list')
    return render(request, 'agenda/admin_evento_delete.html', {'evento': evento})


# ============ INSCRIPCIONES ============
@login_required
def inscribirme(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    Inscripcion.objects.get_or_create(usuario=request.user, evento=evento)
    messages.success(request, _("Inscripción confirmada."))
    return redirect('agenda_index')
