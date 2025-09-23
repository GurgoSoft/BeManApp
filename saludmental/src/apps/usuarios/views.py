from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.urls import reverse

from apps.foro.models import Historia, Like
from .forms import PerfilForm
from .models import Notificacion

User = get_user_model()

def home(request):
    notif_count = 0
    notificaciones = []
    if request.user.is_authenticated:
        notif_count = request.user.notificaciones.filter(leida=False).count()
        notificaciones = request.user.notificaciones.order_by('-fecha')[:8]
    return render(request, "home.html", {
        "notif_count": notif_count,
        "notificaciones": notificaciones,
    })

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"¡Bienvenido {user.username}!")
            return redirect("home")
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, "login.html")

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # Validaciones básicas
        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ese usuario ya existe")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Ese correo ya está registrado")
            return redirect("register")

        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        user.save()

        login(request, user)  # Loguea al usuario automáticamente
        messages.success(request, "Cuenta creada con éxito, inicia sesión")
        return redirect("home")  # Redirige al home

    return render(request, "register.html")

def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente")
    return redirect("home")

@login_required
def editar_perfil(request):
    user = request.user
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
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


