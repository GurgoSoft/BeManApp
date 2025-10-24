from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.utils.translation import gettext as _, get_language_from_request
from django.utils import translation
from django.conf import settings
from django.urls import reverse
from django.utils.formats import date_format
from .models import Evento, Inscripcion, EventoFoto, EventoCalificacion, EventoComentario, EventoLikeComentario
from apps.usuarios.models import Notificacion, CustomUser
from django import forms
from django.db.models import Count
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal, InvalidOperation
from datetime import timedelta
from django.db.models import Avg
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
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
            'imagen': forms.ClearableFileInput(attrs={
                'accept': 'image/jpeg,image/png,image/webp',
                'class': 'form-control'
            }),
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

def _notificar_publicacion(evento: Evento, lang_code: str | None = None, publisher=None) -> int:
    """Envía notificaciones: a usuarios (no staff) anuncio; al publicador (staff) mensaje de confirmación."""
    # Construir URLs
    if lang_code:
        with translation.override(lang_code):
            user_url = reverse('agenda_evento_detalle', kwargs={'pk': evento.pk})
            admin_url = reverse('admin_evento_edit', kwargs={'pk': evento.pk})
    else:
        with translation.override(getattr(settings, 'LANGUAGE_CODE', 'es')):
            user_url = reverse('agenda_evento_detalle', kwargs={'pk': evento.pk})
            admin_url = reverse('admin_evento_edit', kwargs={'pk': evento.pk})

    # Usuarios finales (excluir staff)
    usuarios = CustomUser.objects.filter(is_active=True, is_staff=False)
    msg_user = f"Nuevo evento publicado: {evento.titulo or evento.nombre}"
    objs = [Notificacion(usuario=u, mensaje=msg_user, url=user_url) for u in usuarios]

    # Publicador (si está autenticado)
    if publisher is not None and getattr(publisher, 'is_authenticated', False):
        with translation.override(lang_code or getattr(settings, 'LANGUAGE_CODE', 'es')):
            fecha_fmt = date_format(evento.fecha, 'D d M Y, H:i')
        msg_admin = f"Publicaste el evento: {evento.titulo or evento.nombre} para {fecha_fmt}"
        objs.append(Notificacion(usuario=publisher, mensaje=msg_admin, url=admin_url))

    if not objs:
        return 0
    Notificacion.objects.bulk_create(objs, ignore_conflicts=True)
    return len(objs)

def _notificar_inscripcion(evento: Evento, usuario, lang_code: str | None = None) -> int:
    """Notifica a todo el staff que un usuario se inscribió a un evento."""
    if lang_code:
        with translation.override(lang_code):
            admin_url = reverse('admin_evento_edit', kwargs={'pk': evento.pk})
    else:
        with translation.override(getattr(settings, 'LANGUAGE_CODE', 'es')):
            admin_url = reverse('admin_evento_edit', kwargs={'pk': evento.pk})
    staff = CustomUser.objects.filter(is_active=True, is_staff=True)
    display = ''
    try:
        display = usuario.get_full_name().strip()
    except Exception:
        display = ''
    if not display:
        display = getattr(usuario, 'username', None) or getattr(usuario, 'email', 'usuario')
    msg = f"{display} se inscribió a: {evento.titulo or evento.nombre}"
    objs = [Notificacion(usuario=adm, mensaje=msg, url=admin_url) for adm in staff if getattr(adm, 'pk', None) != getattr(usuario, 'pk', None)]
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
            creadas = _notificar_publicacion(evento, lang_code, publisher=request.user)
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
                _ = _notificar_publicacion(evento, lang_code, publisher=request.user)
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
    ins, created = Inscripcion.objects.get_or_create(usuario=request.user, evento=evento)
    messages.success(request, _("Inscripción confirmada."))
    if created:
        lang_code = get_language_from_request(request)
        _notificar_inscripcion(evento, request.user, lang_code)
    return redirect('agenda_index')


# ============ DETALLE PÚBLICO ============
def evento_detalle(request, pk):
    # Si el evento no existe o no está publicado, no 404: redirige al home con aviso
    evento = Evento.objects.filter(pk=pk).first()
    if not evento or not evento.publicado:
        messages.info(request, _("El evento no está disponible."))
        return redirect('home')
    # Si el evento ya pasó, redirige al home con mensaje
    if evento.fecha < timezone.now():
        messages.info(request, _("Este evento ya pasó."))
        return redirect('home')
    inscrito = False
    if request.user.is_authenticated:
        inscrito = Inscripcion.objects.filter(usuario=request.user, evento=evento).exists()
        try:
            user_rating = EventoCalificacion.objects.filter(evento=evento, usuario=request.user).values_list('estrellas', flat=True).first()
        except Exception:
            user_rating = None
    else:
        user_rating = None
    # Datos de rating y comentarios
    avg_rating = evento.calificaciones.aggregate(avg=Avg('estrellas'))['avg'] or 0
    comentarios = (
        evento.comentarios.filter(parent__isnull=True)
        .annotate(
            likes_count=Count('eventolikecomentario', distinct=True),
            replies_count=Count('respuestas', distinct=True),
        )
        .select_related('usuario')
        .prefetch_related('respuestas__usuario')
        .order_by('-likes_count', '-replies_count', '-fecha')
    )
    fotos = evento.fotos.order_by('-fecha_subida')[:12]
    inscritos_count = Inscripcion.objects.filter(evento=evento).count()
    user_likes = set()
    if request.user.is_authenticated:
        user_likes = set(
            EventoLikeComentario.objects.filter(usuario=request.user, comentario__evento=evento)
            .values_list('comentario_id', flat=True)
        )
    return render(request, 'agenda/evento_detalle.html', {
        'evento': evento,
        'inscrito': inscrito,
        'avg_rating': round(float(avg_rating), 2),
        'user_rating': user_rating or 0,
        'comentarios': comentarios,
        'user_likes': user_likes,
        'fotos': fotos,
        'inscritos_count': inscritos_count,
    })


@login_required
def calificar_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    try:
        estrellas = int(request.POST.get('estrellas', '0'))
    except ValueError:
        estrellas = 0
    if estrellas < 1 or estrellas > 5:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': _('Calificación inválida (1 a 5).')}, status=400)
        messages.error(request, _("Calificación inválida (1 a 5)."))
        return redirect('agenda_evento_detalle', pk=pk)
    obj, _ = EventoCalificacion.objects.update_or_create(
        evento=evento, usuario=request.user, defaults={'estrellas': estrellas}
    )
    # Responder AJAX con promedio actualizado
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        avg = evento.calificaciones.aggregate(avg=Avg('estrellas'))['avg'] or 0
        return JsonResponse({'ok': True, 'avg_rating': round(float(avg), 2), 'estrellas': estrellas})
    messages.success(request, _("¡Gracias por calificar!"))
    return redirect('agenda_evento_detalle', pk=pk)


@login_required
def comentar_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    texto = (request.POST.get('texto') or '').strip()
    if not texto or len(texto) < 2:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': _('El comentario es muy corto.')}, status=400)
        messages.error(request, _("El comentario es muy corto."))
        return redirect('agenda_evento_detalle', pk=pk)
    # Moderación básica reutilizando detector local
    try:
        from apps.foro.moderation import moderate_text
        res = moderate_text(texto)
        if not res.allowed:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': _('Tu comentario contiene contenido no permitido.')}, status=400)
            messages.error(request, _("Tu comentario contiene contenido no permitido."))
            return redirect('agenda_evento_detalle', pk=pk)
    except Exception:
        try:
            if contains_banned_words(texto):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': _('Tu comentario contiene palabras no permitidas.')}, status=400)
                messages.error(request, _("Tu comentario contiene palabras no permitidas."))
                return redirect('agenda_evento_detalle', pk=pk)
        except Exception:
            pass
    comentario = EventoComentario.objects.create(evento=evento, usuario=request.user, texto=texto)
    # Responder AJAX con el HTML del comentario para prepend en el feed
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('agenda/_comentario_item.html', {'c': comentario, 'user_likes': set()}, request=request)
        return JsonResponse({'ok': True, 'html': html})
    messages.success(request, _("Comentario publicado."))
    return redirect('agenda_evento_detalle', pk=pk)


@login_required
@require_POST
def like_evento_comentario(request, pk):
    comentario = get_object_or_404(EventoComentario, pk=pk)
    like, created = EventoLikeComentario.objects.get_or_create(comentario=comentario, usuario=request.user)
    liked = True
    if not created:
        like.delete()
        liked = False
    likes_count = EventoLikeComentario.objects.filter(comentario=comentario).count()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'liked': liked, 'likes_count': likes_count, 'comentario_id': comentario.pk})
    return redirect('agenda_evento_detalle', pk=comentario.evento_id)


@login_required
@require_POST
def responder_evento_comentario(request, pk):
    parent = get_object_or_404(EventoComentario, pk=pk)
    texto = (request.POST.get('texto') or '').strip()
    if not texto:
        messages.error(request, _("El texto no puede estar vacío."))
    else:
        try:
            from apps.foro.moderation import moderate_text
            res = moderate_text(texto)
            if not res.allowed:
                messages.error(request, _("Tu respuesta contiene contenido no permitido."))
                return redirect('agenda_evento_detalle', pk=parent.evento_id)
        except Exception:
            try:
                if contains_banned_words(texto):
                    messages.error(request, _("Tu respuesta contiene palabras no permitidas."))
                    return redirect('agenda_evento_detalle', pk=parent.evento_id)
            except Exception:
                pass
        EventoComentario.objects.create(evento=parent.evento, usuario=request.user, texto=texto, parent=parent)
        messages.success(request, _("Respuesta publicada."))
    return redirect('agenda_evento_detalle', pk=parent.evento_id)


@login_required
@require_POST
def editar_evento_comentario(request, pk):
    comentario = get_object_or_404(EventoComentario, pk=pk, usuario=request.user)
    texto = (request.POST.get('texto') or '').strip()
    if not texto:
        messages.error(request, _("El texto no puede estar vacío."))
    else:
        try:
            from apps.foro.moderation import moderate_text
            res = moderate_text(texto)
            if not res.allowed:
                messages.error(request, _("Tu comentario contiene contenido no permitido."))
                return redirect('agenda_evento_detalle', pk=comentario.evento_id)
        except Exception:
            try:
                if contains_banned_words(texto):
                    messages.error(request, _("Tu comentario contiene palabras no permitidas."))
                    return redirect('agenda_evento_detalle', pk=comentario.evento_id)
            except Exception:
                pass
        comentario.texto = texto
        comentario.save()
        messages.success(request, _("Comentario actualizado."))
    return redirect('agenda_evento_detalle', pk=comentario.evento_id)


@login_required
@require_POST
def eliminar_evento_comentario(request, pk):
    comentario = get_object_or_404(EventoComentario, pk=pk)
    if request.user != comentario.usuario and not request.user.is_staff:
        return HttpResponseForbidden()
    evento_pk = comentario.evento_id
    comentario.delete()
    messages.success(request, _("Comentario eliminado."))
    return redirect('agenda_evento_detalle', pk=evento_pk)


@user_passes_test(_is_staff)
def admin_evento_fotos(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.method == 'POST':
        # Subida de múltiples imágenes
        for f in request.FILES.getlist('fotos'):
            EventoFoto.objects.create(evento=evento, imagen=f, subido_por=request.user)
        messages.success(request, _("Fotos subidas."))
        return redirect('admin_evento_fotos', pk=pk)
    fotos = evento.fotos.order_by('-fecha_subida')
    return render(request, 'agenda/admin_evento_fotos.html', {'evento': evento, 'fotos': fotos})
