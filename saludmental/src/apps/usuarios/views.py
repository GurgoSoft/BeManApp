from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.urls import reverse
from django import forms
from django.http import JsonResponse
from django.utils.translation import gettext as _

from apps.foro.models import Historia, Like
from .email_utils import enviar_email_bienvenida
from apps.agenda.models import Evento
from django.utils import timezone
from .forms import PerfilForm
from .models import Notificacion

User = get_user_model()

def home(request):
    notif_count = 0
    notificaciones = []
    if request.user.is_authenticated:
        notif_count = request.user.notificaciones.filter(leida=False).count()
        notificaciones = request.user.notificaciones.order_by('-fecha')[:8]

    historias = Historia.objects.annotate(
        likes_count=Count('like_set', distinct=True),
        comentarios_count=Count('comentario', distinct=True),
    ).order_by('-likes_count', '-comentarios_count', '-fecha')[:6]

    eventos = Evento.objects.filter(publicado=True, fecha__gte=timezone.now()).order_by('fecha')[:6]

    return render(request, "home.html", {
        "notif_count": notif_count,
        "notificaciones": notificaciones,
        "historias": historias,
        "eventos": eventos,
    })

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, _(f"¡Bienvenid@ a Iterum, {user.username}!"))
            return redirect("home")
        else:
            messages.error(request, _("Usuario o contraseña incorrectos"))

    return render(request, "login.html")

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        # Validaciones básicas
        if not username or not email or not password1:
            messages.error(request, _("Todos los campos obligatorios deben estar llenos"))
            return redirect("register")
        
        if len(username) < 3:
            messages.error(request, _("El nombre de usuario debe tener al menos 3 caracteres"))
            return redirect("register")
        
        if not email or '@' not in email:
            messages.error(request, _("Debes ingresar un correo electrónico válido"))
            return redirect("register")
        
        if len(password1) < 6:
            messages.error(request, _("La contraseña debe tener al menos 6 caracteres"))
            return redirect("register")

        if password1 != password2:
            messages.error(request, _("Las contraseñas no coinciden"))
            return redirect("register")

        # Validar unicidad (case insensitive para email y username)
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, _("Este nombre de usuario ya está registrado"))
            return redirect("register")

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, _("Este correo electrónico ya está registrado"))
            return redirect("register")

        # Crear usuario con email como campo de autenticación principal
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            user.save()

            # Enviar email de bienvenida
            try:
                url_home = request.build_absolute_uri(reverse('home'))
                enviar_email_bienvenida(user, url_home)
            except Exception as e:
                # Log del error pero no interrumpir el registro
                print(f"Error enviando email de bienvenida: {e}")

            # Autenticar con email (que es el USERNAME_FIELD)
            user_authenticated = authenticate(request, username=email, password=password1)
            if user_authenticated:
                login(request, user_authenticated)
                messages.success(request, _(f"¡Bienvenid@ a Iterum, {user.username}!"))
                return redirect("home")
            else:
                # Si falla la autenticación automática, al menos el usuario se creó
                messages.success(request, _("Cuenta creada con éxito. Por favor inicia sesión."))
                return redirect("login")
        
        except Exception as e:
            messages.error(request, _(f"Error al crear la cuenta: {str(e)}"))
            return redirect("register")

    return render(request, "register.html")

def logout_view(request):
    logout(request)
    messages.info(request, _("Sesión cerrada correctamente"))
    return redirect("home")

@login_required
def editar_perfil(request):
    user = request.user
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Perfil actualizado."))
            return redirect('editar_perfil')
    else:
        form = PerfilForm(instance=user)
    return render(request, 'profile_edit.html', {'form': form, 'user': user})

@login_required
def notificaciones(request):
    notificaciones = request.user.notificaciones.order_by('-fecha')[:20]
    return render(request, 'notificaciones_menu.html', {'notificaciones': notificaciones})

@login_required
def marcar_notificacion_leida(request, pk):
    notif = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    notif.leida = True
    notif.save()
    return redirect(notif.url or '/')

@login_required
def marcar_todas_leidas(request):
    """Marca todas las notificaciones del usuario como leídas"""
    if request.method == 'POST':
        request.user.notificaciones.filter(leida=False).update(leida=True)
        messages.success(request, _('Todas las notificaciones han sido marcadas como leídas.'))
    return redirect(request.META.get('HTTP_REFERER', '/'))

# APIs para sidebar móvil
@login_required
def user_stats_api(request):
    """Estadísticas del usuario para sidebar móvil"""
    from apps.foro.models import Historia, Comentario, Like
    from django.db.models import Count
    
    historias_count = Historia.objects.filter(usuario=request.user).count()
    comentarios_count = Comentario.objects.filter(usuario=request.user).count()
    likes_received = Like.objects.filter(historia__usuario=request.user).count()
    
    return JsonResponse({
        'historias': historias_count,
        'comentarios': comentarios_count,
        'likes': likes_received
    })

@login_required
def notificaciones_recientes_api(request):
    """Notificaciones recientes para sidebar móvil"""
    from django.utils import timezone
    from django.utils.timesince import timesince
    
    notifs = request.user.notificaciones.order_by('-fecha')[:5]
    count = request.user.notificaciones.filter(leida=False).count()
    
    notifs_list = []
    for n in notifs:
        notifs_list.append({
            'id': n.pk,
            'mensaje': n.mensaje,
            'tipo': n.tipo if hasattr(n, 'tipo') else 'general',
            'leida': n.leida,
            'tiempo': timesince(n.fecha) + ' ago',
            'url': n.url or '#'
        })
    
    return JsonResponse({
        'count': count,
        'notificaciones': notifs_list
    })

def clean_phone_number(self):
    number = self.cleaned_data.get('phone_number', '').strip()
    if not number.startswith('+') or not number[1:].replace(' ', '').isdigit():
        raise forms.ValidationError("El número debe incluir el indicativo internacional y solo contener números.")
    return number


