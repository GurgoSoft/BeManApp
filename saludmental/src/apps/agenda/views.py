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
import hashlib
from django.http import HttpResponseForbidden
import requests
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
            'tipo_evento', 'lugar', 'latitud', 'longitud',
            'link_virtual', 'plataforma_virtual', 'fecha', 'precio'
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
            'tipo_evento': forms.Select(attrs={
                'class': 'form-select'
            }),
            'lugar': forms.TextInput(attrs={
                'placeholder': _('Dirección exacta o enlace de Zoom/Meet'),
                'maxlength': 120,
                'class': 'form-control',
                'id': 'id_lugar'
            }),
            'latitud': forms.HiddenInput(attrs={'id': 'id_latitud'}),
            'longitud': forms.HiddenInput(attrs={'id': 'id_longitud'}),
            'link_virtual': forms.URLInput(attrs={
                'placeholder': _('https://zoom.us/j/123456789 o https://meet.google.com/abc-defg-hij'),
                'class': 'form-control'
            }),
            'plataforma_virtual': forms.Select(attrs={
                'class': 'form-select'
            }, choices=[
                ('', _('Seleccionar plataforma')),
                ('Zoom', 'Zoom'),
                ('Google Meet', 'Google Meet'),
                ('Microsoft Teams', 'Microsoft Teams'),
                ('Discord', 'Discord'),
                ('Otro', _('Otro'))
            ]),
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
        
        # Formatear fecha para datetime-local cuando se edita
        if self.instance and self.instance.pk and self.instance.fecha:
            # Formato: YYYY-MM-DDTHH:MM (sin segundos ni zona horaria)
            self.initial['fecha'] = self.instance.fecha.strftime('%Y-%m-%dT%H:%M')

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
    from apps.foro.models import Historia, Comentario as ForoComentario
    from django.db.models import Avg, Sum
    
    ahora = timezone.now()
    
    # Estadísticas generales
    usuarios_count = request.user.__class__.objects.count()
    inscripciones_count = Inscripcion.objects.count()
    eventos_count = Evento.objects.count()
    historias_count = Historia.objects.count()
    comentarios_foro = ForoComentario.objects.count()
    comentarios_eventos = EventoComentario.objects.count()
    notificaciones_pendientes = Notificacion.objects.filter(leida=False).count()
    
    # Eventos próximos (futuros) ordenados por fecha ascendente (más cercanos primero)
    proximos = Evento.objects.filter(fecha__gte=ahora).annotate(inscritos=Count('inscripcion')).order_by('fecha')[:5]
    
    # Eventos pasados (recientes) ordenados por fecha descendente (más recientes primero)
    pasados = Evento.objects.filter(fecha__lt=ahora).annotate(inscritos=Count('inscripcion')).order_by('-fecha')[:5]
    
    # Calificaciones promedio
    rating_promedio = EventoCalificacion.objects.aggregate(promedio=Avg('estrellas'))['promedio'] or 0
    
    # Eventos más populares (por inscripciones)
    mas_populares = Evento.objects.annotate(inscritos=Count('inscripcion')).order_by('-inscritos')[:3]
    
    # Actividad reciente
    historias_recientes = Historia.objects.select_related('usuario').order_by('-fecha')[:5]
    
    return render(request, 'agenda/admin_dashboard.html', {
        'usuarios_count': usuarios_count,
        'inscripciones_count': inscripciones_count,
        'eventos_count': eventos_count,
        'historias_count': historias_count,
        'comentarios_total': comentarios_foro + comentarios_eventos,
        'notificaciones_pendientes': notificaciones_pendientes,
        'rating_promedio': round(rating_promedio, 1),
        'proximos': proximos,
        'pasados': pasados,
        'mas_populares': mas_populares,
        'historias_recientes': historias_recientes,
    })


@user_passes_test(_is_staff)
def admin_evento_list(request):
    eventos = Evento.objects.order_by('-fecha').prefetch_related('inscripcion_set__usuario')
    return render(request, 'agenda/admin_evento_list.html', {
        'eventos': eventos,
        'now': timezone.now()
    })


@user_passes_test(_is_staff)
def admin_evento_create(request):
    if request.method == 'POST':
        form = EventoForm(request.POST, request.FILES)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.publicado = True
            evento.fecha_publicacion = timezone.now()
            evento.save()
            
            # Las coordenadas vienen del Google Places Autocomplete en el formulario
            # Ya no necesitamos buscarlas con Nominatim
            
            lang_code = get_language_from_request(request)
            _notificar_publicacion(evento, lang_code, publisher=request.user)
            messages.success(request, _("Evento creado y publicado."))
            return redirect('admin_evento_list')
    else:
        form = EventoForm()
    return render(request, 'agenda/admin_evento_form.html', {'form': form, 'modo': 'crear'})


@user_passes_test(_is_staff)
def admin_evento_edit(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    
    # Bloquear edición de eventos pasados
    if evento.fecha < timezone.now():
        messages.error(request, _("No se pueden editar eventos que ya finalizaron."))
        return redirect('admin_evento_list')
    
    if request.method == 'POST':
        form = EventoForm(request.POST, request.FILES, instance=evento)
        if form.is_valid():
            antes_publicado = bool(evento.publicado)
            evento = form.save(commit=False)
            evento.publicado = True
            
            # Publicación transicional
            if not antes_publicado and evento.publicado:
                evento.fecha_publicacion = timezone.now()
            
            evento.save()
            
            # Las coordenadas vienen del Google Places Autocomplete en el formulario
            # Ya no necesitamos buscarlas con Nominatim
            
            # Notificar si es necesario
            if not antes_publicado and evento.publicado:
                lang_code = get_language_from_request(request)
                _notificar_publicacion(evento, lang_code, publisher=request.user)
            
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


@user_passes_test(_is_staff)
def admin_evento_fotos(request, pk):
    """Vista para que el admin suba fotos desde el modal del detalle del evento"""
    evento = get_object_or_404(Evento, pk=pk)
    
    # Solo acepta POST para subir fotos
    if request.method == 'POST':
        fotos = request.FILES.getlist('fotos')
        
        # Si es AJAX, devolver JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if not fotos:
                return JsonResponse({
                    'success': False,
                    'message': _("No seleccionaste ninguna foto.")
                })
            else:
                count = 0
                duplicadas = []
                
                for foto in fotos:
                    # Calcular hash MD5 del archivo
                    foto.seek(0)  # Asegurar que estamos al inicio del archivo
                    md5_hash = hashlib.md5()
                    for chunk in foto.chunks():
                        md5_hash.update(chunk)
                    file_hash = md5_hash.hexdigest()
                    
                    # Verificar si ya existe una foto con el mismo hash en este evento
                    if EventoFoto.objects.filter(evento=evento, hash_md5=file_hash).exists():
                        duplicadas.append(foto.name)
                        continue
                    
                    # Crear la foto con el hash
                    EventoFoto.objects.create(
                        evento=evento,
                        imagen=foto,
                        subido_por=request.user,
                        hash_md5=file_hash
                    )
                    count += 1
                
                # Preparar mensaje
                if count > 0 and len(duplicadas) > 0:
                    mensaje = _(f"{count} foto(s) agregada(s). {len(duplicadas)} foto(s) duplicada(s) omitida(s).")
                elif count > 0:
                    mensaje = _(f"{count} foto(s) agregada(s) exitosamente.")
                elif len(duplicadas) > 0:
                    mensaje = _("Todas las fotos ya existen en este evento.")
                else:
                    mensaje = _("No se agregaron fotos.")
                
                return JsonResponse({
                    'success': count > 0,
                    'message': mensaje,
                    'count': count,
                    'duplicadas': duplicadas
                })
        else:
            # Fallback para requests normales
            if not fotos:
                messages.warning(request, _("No seleccionaste ninguna foto."))
            else:
                count = 0
                duplicadas = []
                
                for foto in fotos:
                    # Calcular hash MD5
                    foto.seek(0)
                    md5_hash = hashlib.md5()
                    for chunk in foto.chunks():
                        md5_hash.update(chunk)
                    file_hash = md5_hash.hexdigest()
                    
                    # Verificar duplicados
                    if EventoFoto.objects.filter(evento=evento, hash_md5=file_hash).exists():
                        duplicadas.append(foto.name)
                        continue
                    
                    EventoFoto.objects.create(
                        evento=evento,
                        imagen=foto,
                        subido_por=request.user,
                        hash_md5=file_hash
                    )
                    count += 1
                
                if count > 0 and len(duplicadas) > 0:
                    messages.success(request, _(f"{count} foto(s) agregada(s). {len(duplicadas)} duplicada(s) omitida(s)."))
                elif count > 0:
                    messages.success(request, _(f"{count} foto(s) agregada(s) exitosamente."))
                elif len(duplicadas) > 0:
                    messages.warning(request, _("Todas las fotos ya existen en este evento."))
    
    # Siempre redirigir al detalle del evento (no hay página de fotos)
    return redirect('agenda_evento_detalle', pk=pk)


@user_passes_test(_is_staff)
def eliminar_evento_foto(request, pk):
    """
    Elimina una foto de un evento.
    Solo accesible para administradores.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _("Método no permitido")}, status=405)
    
    # Verificar que sea una solicitud AJAX
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        messages.error(request, _("Solicitud inválida"))
        return redirect('admin_dashboard')
    
    try:
        foto = get_object_or_404(EventoFoto, pk=pk)
        evento = foto.evento
        
        # Validar que no sea la última foto
        total_fotos = evento.fotos.count()
        tiene_portada = bool(evento.imagen)
        
        # Si solo hay 1 foto y no hay portada, no se puede eliminar
        if total_fotos == 1 and not tiene_portada:
            return JsonResponse({
                'success': False,
                'message': _("No puedes eliminar la única foto del evento. Debe haber al menos una imagen.")
            }, status=400)
        
        # Eliminar la foto
        foto.delete()
        
        return JsonResponse({
            'success': True,
            'message': _("Foto eliminada exitosamente")
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': _("Error al eliminar la foto: ") + str(e)
        }, status=500)


# ============ INSCRIPCIONES ============
class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ['nombre_completo', 'telefono', 'notas']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nombre completo'),
                'required': True
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Teléfono de contacto (opcional)'),
                'type': 'tel'
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('¿Algo que quieras comentarnos? (opcional)'),
                'rows': 3
            }),
        }

@login_required
def inscribirme(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    
    # Verificar si ya está inscrito
    if Inscripcion.objects.filter(usuario=request.user, evento=evento).exists():
        messages.info(request, _("Ya estás inscrito en este evento."))
        return redirect('agenda_evento_detalle', pk=pk)
    
    if request.method == 'POST':
        form = InscripcionForm(request.POST)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.usuario = request.user
            inscripcion.evento = evento
            inscripcion.save()
            messages.success(request, _("¡Inscripción confirmada! Ahora puedes ver toda la información del evento."))
            lang_code = get_language_from_request(request)
            _notificar_inscripcion(evento, request.user, lang_code)
            return redirect('agenda_evento_detalle', pk=pk)
    else:
        # Pre-llenar con datos del usuario
        initial_data = {
            'nombre_completo': request.user.get_full_name() or request.user.username,
            'telefono': getattr(request.user, 'phone_number', '')
        }
        form = InscripcionForm(initial=initial_data)
    
    return render(request, 'agenda/inscripcion_form.html', {
        'form': form,
        'evento': evento
    })


# ============ DETALLE PÚBLICO ============
def evento_detalle(request, pk):
    # Si el evento no existe o no está publicado, no 404: redirige al home con aviso
    evento = Evento.objects.filter(pk=pk).first()
    if not evento or not evento.publicado:
        messages.info(request, _("El evento no está disponible."))
        return redirect('home')
    # Si el evento ya pasó, redirige al home con mensaje (EXCEPTO para admin)
    if evento.fecha < timezone.now() and not (request.user.is_authenticated and request.user.is_staff):
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
    # Total de comentarios incluyendo respuestas
    comentarios_total = EventoComentario.objects.filter(evento=evento).count()
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
        'comentarios_total': comentarios_total,
        'user_likes': user_likes,
        'fotos': fotos,
        'inscritos_count': inscritos_count,
        'now': timezone.now(),
    })


@login_required
def calificar_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    try:
        estrellas = int(request.POST.get('estrellas', '0'))
    except ValueError:
        estrellas = 0
    
    # Si estrellas = 0, eliminar calificación (descalificar)
    if estrellas == 0:
        EventoCalificacion.objects.filter(evento=evento, usuario=request.user).delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            avg = evento.calificaciones.aggregate(avg=Avg('estrellas'))['avg'] or 0
            return JsonResponse({'ok': True, 'avg_rating': round(float(avg), 2), 'estrellas': 0})
        messages.info(request, _("Calificación eliminada."))
        return redirect('agenda_evento_detalle', pk=pk)
    
    # Validar rango 1-5
    if estrellas < 1 or estrellas > 5:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': _('Calificación inválida (1 a 5).')}, status=400)
        messages.error(request, _("Calificación inválida (1 a 5)."))
        return redirect('agenda_evento_detalle', pk=pk)
    
    # Guardar o actualizar calificación
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
        total = EventoComentario.objects.filter(evento=evento).count()
        return JsonResponse({'ok': True, 'html': html, 'total': total})
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
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': _("El texto no puede estar vacío.")}, status=400)
        messages.error(request, _("El texto no puede estar vacío."))
    else:
        try:
            from apps.foro.moderation import moderate_text
            res = moderate_text(texto)
            if not res.allowed:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': _("Tu respuesta contiene contenido no permitido.")}, status=400)
                messages.error(request, _("Tu respuesta contiene contenido no permitido."))
                return redirect('agenda_evento_detalle', pk=parent.evento_id)
        except Exception:
            try:
                if contains_banned_words(texto):
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'ok': False, 'error': _("Tu respuesta contiene palabras no permitidas.")}, status=400)
                    messages.error(request, _("Tu respuesta contiene palabras no permitidas."))
                    return redirect('agenda_evento_detalle', pk=parent.evento_id)
            except Exception:
                pass
        reply = EventoComentario.objects.create(evento=parent.evento, usuario=request.user, texto=texto, parent=parent)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string('agenda/_comentario_item.html', {'c': reply, 'user_likes': set()}, request=request)
            total = EventoComentario.objects.filter(evento=parent.evento).count()
            return JsonResponse({'ok': True, 'html': html, 'parent_id': parent.pk, 'total': total})
        messages.success(request, _("Respuesta publicada."))
    return redirect('agenda_evento_detalle', pk=parent.evento_id)


@login_required
@require_POST
def editar_evento_comentario(request, pk):
    comentario = get_object_or_404(EventoComentario, pk=pk, usuario=request.user)
    texto = (request.POST.get('texto') or '').strip()
    if not texto:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': _("El texto no puede estar vacío.")}, status=400)
        messages.error(request, _("El texto no puede estar vacío."))
    else:
        try:
            from apps.foro.moderation import moderate_text
            res = moderate_text(texto)
            if not res.allowed:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': _("Tu comentario contiene contenido no permitido.")}, status=400)
                messages.error(request, _("Tu comentario contiene contenido no permitido."))
                return redirect('agenda_evento_detalle', pk=comentario.evento_id)
        except Exception:
            try:
                if contains_banned_words(texto):
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'ok': False, 'error': _("Tu comentario contiene palabras no permitidas.")}, status=400)
                    messages.error(request, _("Tu comentario contiene palabras no permitidas."))
                    return redirect('agenda_evento_detalle', pk=comentario.evento_id)
            except Exception:
                pass
        comentario.texto = texto
        comentario.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'comentario_id': comentario.pk, 'texto': comentario.texto})
        messages.success(request, _("Comentario actualizado."))
    return redirect('agenda_evento_detalle', pk=comentario.evento_id)


@login_required
@require_POST
def eliminar_evento_comentario(request, pk):
    comentario = get_object_or_404(EventoComentario, pk=pk)
    if request.user != comentario.usuario and not request.user.is_staff:
        return HttpResponseForbidden()
    evento_pk = comentario.evento_id
    parent_id = getattr(comentario.parent, 'pk', None)
    comentario.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        total = EventoComentario.objects.filter(evento_id=evento_pk).count()
        # Si es respuesta, recalcular cantidad de respuestas del padre
        replies_count = None
        if parent_id:
            replies_count = EventoComentario.objects.filter(parent_id=parent_id).count()
        return JsonResponse({'ok': True, 'deleted_id': pk, 'total': total, 'parent_id': parent_id, 'replies_count': replies_count})
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


# ============ VISTAS ADMIN PERSONALIZADAS ============
@user_passes_test(_is_staff)
def admin_usuarios_list(request):
    usuarios = CustomUser.objects.order_by('-date_joined')
    return render(request, 'agenda/admin_usuarios_list.html', {'usuarios': usuarios})


@user_passes_test(_is_staff)
def admin_inscripciones_list(request):
    inscripciones = Inscripcion.objects.select_related('usuario', 'evento').order_by('-fecha_inscripcion')
    return render(request, 'agenda/admin_inscripciones_list.html', {'inscripciones': inscripciones})


@user_passes_test(_is_staff)
def admin_historias_list(request):
    from apps.foro.models import Historia
    historias = Historia.objects.select_related('usuario').order_by('-fecha')
    return render(request, 'agenda/admin_historias_list.html', {'historias': historias})


@user_passes_test(_is_staff)
def admin_comentarios_list(request):
    from apps.foro.models import Comentario as ForoComentario
    comentarios_foro = ForoComentario.objects.select_related('usuario', 'historia').order_by('-fecha')
    comentarios_eventos = EventoComentario.objects.select_related('usuario', 'evento').order_by('-fecha')
    return render(request, 'agenda/admin_comentarios_list.html', {
        'comentarios_foro': comentarios_foro,
        'comentarios_eventos': comentarios_eventos,
    })


@user_passes_test(_is_staff)
def admin_notificaciones_list(request):
    # Solo notificaciones del admin actual
    notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'agenda/admin_notificaciones_list.html', {'notificaciones': notificaciones})


@user_passes_test(_is_staff)
def admin_calificaciones_list(request):
    calificaciones = EventoCalificacion.objects.select_related('usuario', 'evento').order_by('-fecha')
    return render(request, 'agenda/admin_calificaciones_list.html', {'calificaciones': calificaciones})
