from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.utils.translation import gettext as _, get_language_from_request
from django.utils import translation
from django.conf import settings
from django.urls import reverse
from .models import Evento, Inscripcion
from apps.usuarios.models import Notificacion, CustomUser
from django import forms
from django.db.models import Count
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal, InvalidOperation
from datetime import timedelta
try:
    # Reusar detección de lenguaje inapropiado si existe
    from apps.foro.profanity import contains_banned_words
except Exception:  # pragma: no cover - fallback si no existe
    def contains_banned_words(_text: str) -> bool:
        return False

def index(request):
    ahora = timezone.now()
    eventos = Evento.objects.filter(publicado=True).order_by('fecha').annotate(inscritos=Count('inscripcion'))
    proximos = eventos.filter(fecha__gte=ahora)
    pasados = eventos.filter(fecha__lt=ahora).order_by('-fecha')
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
            'titulo': forms.TextInput(attrs={
                'placeholder': _('Ej: Círculo de Hombres — Medellín'),
                'maxlength': 120,
                'class': 'form-control'
            }),
            'nombre': forms.TextInput(attrs={
                'placeholder': _('slug interno único, p. ej. circulo-hombres-medellin-oct-2025'),
                'maxlength': 140,
                'class': 'form-control'
            }),
            'descripcion_corta': forms.Textarea(attrs={
                'rows': 4,
                'maxlength': 500,
                'placeholder': _('Qué aprenderán, a quién va dirigido y beneficios (máx. 500).'),
                'class': 'form-control'
            }),
            'lugar': forms.TextInput(attrs={
                'placeholder': _('Dirección exacta o enlace de Zoom/Meet'),
                'maxlength': 120,
                'class': 'form-control'
            }),
            'fecha': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }),
            'precio': forms.NumberInput(attrs={
                'min': '0',
                'step': '1',
                'placeholder': '0',
                'inputmode': 'numeric',
                'pattern': '[0-9]*',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Precio por defecto 0 (COP)
        if not getattr(self.instance, 'pk', None) or self.instance.precio is None:
            self.fields['precio'].initial = 0

    def clean_titulo(self):
        titulo = (self.cleaned_data.get('titulo') or '').strip()
        if len(titulo) < 5:
            raise ValidationError(_('El título es muy corto.'))
        if contains_banned_words(titulo):
            raise ValidationError(_('El título contiene palabras no permitidas.'))
        return titulo

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        titulo = (self.cleaned_data.get('titulo') or '').strip()
        base = nombre or titulo
        slug = slugify(base)[:140]
        if len(slug) < 3:
            raise ValidationError(_('El nombre interno (slug) es demasiado corto.'))
        # Unicidad suave
        qs = Evento.objects.filter(nombre=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_('Ya existe un evento con ese nombre interno.'))
        return slug

    def clean_descripcion_corta(self):
        desc = (self.cleaned_data.get('descripcion_corta') or '').strip()
        if len(desc) < 10:
            raise ValidationError(_('La descripción es muy corta (mín. 10).'))
        if len(desc) > 600:
            raise ValidationError(_('La descripción es muy larga (máx. 600).'))
        if contains_banned_words(desc):
            raise ValidationError(_('La descripción contiene palabras no permitidas.'))
        return desc

    def clean_lugar(self):
        lugar = (self.cleaned_data.get('lugar') or '').strip()
        if len(lugar) < 2:
            raise ValidationError(_('El lugar es muy corto.'))
        if len(lugar) > 120:
            raise ValidationError(_('El lugar es muy largo.'))
        return lugar

    def clean_precio(self):
        raw = self.cleaned_data.get('precio')
        # Acepta sólo dígitos (COP enteros)
        digits = ''.join(ch for ch in str(raw) if ch.isdigit()) if raw is not None else '0'
        if digits == '':
            digits = '0'
        try:
            valor = int(digits)
        except ValueError:
            raise ValidationError(_('Precio inválido. Usa solo números en COP.'))
        if valor < 0:
            raise ValidationError(_('El precio no puede ser negativo.'))
        if valor > 1000000:
            raise ValidationError(_('El precio es demasiado alto.'))
        return Decimal(valor)

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if not fecha:
            raise ValidationError(_('Debes indicar fecha y hora.'))
        ahora = timezone.now()
        # Regla: mismo día requiere 2 horas mín; otros días 5 minutos
        if fecha.date() == ahora.date():
            minimo = timedelta(hours=2)
        else:
            minimo = timedelta(minutes=5)
        if fecha < ahora + minimo:
            raise ValidationError(_('Para hoy, mínimo 2 horas de anticipación; para otros días, al menos 5 minutos.'))
        if fecha > ahora + timedelta(days=365*2):
            raise ValidationError(_('La fecha no puede superar 2 años desde hoy.'))
        return fecha

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if not imagen:
            return imagen
        # Validar tamaño y tipo
        max_mb = 3
        if hasattr(imagen, 'size') and imagen.size > max_mb * 1024 * 1024:
            raise ValidationError(_('La imagen supera el tamaño máximo de %(mb)sMB.'), params={'mb': max_mb})
        ctype = getattr(imagen, 'content_type', '') or ''
        allowed = {'image/jpeg', 'image/png', 'image/webp'}
        if ctype and ctype not in allowed:
            raise ValidationError(_('Formato de imagen no soportado. Usa JPG, PNG o WEBP.'))
        return imagen

    def clean(self):
        cleaned = super().clean()
        fecha = cleaned.get('fecha')
        lugar = (cleaned.get('lugar') or '').strip()
        if fecha and lugar:
            ventana = timedelta(hours=1)
            qs = Evento.objects.filter(
                lugar__iexact=lugar,
                fecha__range=(fecha - ventana, fecha + ventana)
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_('Ya existe un evento en el mismo lugar y horario cercano (±1h).'))
        return cleaned

def _notificar_publicacion(evento: Evento, lang_code: str | None = None) -> int:
    # Construye URL al detalle del evento respetando i18n_patterns
    if lang_code:
        with translation.override(lang_code):
            url = reverse('agenda_evento_detalle', kwargs={'pk': evento.pk})
    else:
        # Fallback al idioma por defecto
        with translation.override(getattr(settings, 'LANGUAGE_CODE', 'es')):
            url = reverse('agenda_evento_detalle', kwargs={'pk': evento.pk})
    usuarios = CustomUser.objects.filter(is_active=True)
    objs = [
        Notificacion(usuario=u, mensaje=f"Nuevo evento publicado: {evento.titulo or evento.nombre}", url=url)
        for u in usuarios
    ]
    if not objs:
        return 0
    Notificacion.objects.bulk_create(objs, ignore_conflicts=True)
    return len(objs)


@user_passes_test(_is_staff)
def admin_dashboard(request):
    ahora = timezone.now()
    eventos = Evento.objects.order_by('-fecha').annotate(inscritos=Count('inscripcion'))
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
            evento = form.save(commit=False)
            evento.publicado = True
            evento.fecha_publicacion = timezone.now()
            evento.save()
            lang_code = get_language_from_request(request)
            creadas = _notificar_publicacion(evento, lang_code)
            messages.success(request, _("Evento publicado correctamente. Notificaciones enviadas: %d") % creadas)
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
            antes_publicado = bool(evento.publicado)
            evento = form.save(commit=False)
            # Siempre mantener publicado
            evento.publicado = True
            # Publicación transicional: si antes no estaba publicado y ahora sí
            if not antes_publicado and evento.publicado:
                evento.fecha_publicacion = timezone.now()
                evento.save()
                lang_code = get_language_from_request(request)
                _ = _notificar_publicacion(evento, lang_code)
            else:
                evento.save()
            messages.success(request, _("Evento actualizado y publicado."))
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


# ============ DETALLE PÚBLICO ============
def evento_detalle(request, pk):
    evento = get_object_or_404(Evento, pk=pk, publicado=True)
    inscrito = False
    if request.user.is_authenticated:
        inscrito = Inscripcion.objects.filter(usuario=request.user, evento=evento).exists()
    return render(request, 'agenda/evento_detalle.html', {
        'evento': evento,
        'inscrito': inscrito,
    })
