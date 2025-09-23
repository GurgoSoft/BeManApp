from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Historia, Comentario, LikeComentario, Like
from .forms import HistoriaForm, ComentarioForm
from apps.usuarios.models import Notificacion
from django.urls import reverse

def historias_list(request):
    if request.user.is_authenticated:
        historias = Historia.objects.filter(oculto=False)
    else:
        historias = Historia.objects.filter(oculto=False)
    return render(request, "foro/historias_list.html", {"historias": historias})

@login_required
def crear_historia(request):
    if request.method == "POST":
        form = HistoriaForm(request.POST)
        if form.is_valid():
            historia = form.save(commit=False)
            historia.usuario = request.user
            historia.save()
            return redirect('historias_list')
    else:
        form = HistoriaForm()
    return render(request, "foro/crear_historia.html", {"form": form})

def historia_detalle(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    comentarios = Comentario.objects.filter(historia=historia, parent__isnull=True).order_by('-fecha').prefetch_related('respuestas')
    form = ComentarioForm()
    respuesta_forms = {c.pk: ComentarioForm() for c in comentarios}
    user_likes = set()
    if request.user.is_authenticated:
        user_likes = set(
            LikeComentario.objects.filter(usuario=request.user, comentario__historia=historia)
            .values_list('comentario_id', flat=True)
        )
    return render(request, "foro/historia_detalle.html", {
        "historia": historia,
        "comentarios": comentarios,
        "form": form,
        "respuesta_forms": respuesta_forms,
        "user_likes": user_likes,
        "user": request.user,
    })

@login_required
def like_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    like = Like.objects.filter(usuario=request.user, historia=historia)
    if like.exists():
        like.delete()  # Solo quita el like del usuario actual
    else:
        Like.objects.create(usuario=request.user, historia=historia)
    return redirect('historia_detalle', pk=pk)

@login_required
def favorito_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    Favorito.objects.get_or_create(usuario=request.user, historia=historia)
    return redirect('historia_detalle', pk=pk)

@login_required
def comentar_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    if request.method == "POST":
        texto = request.POST.get("texto")
        comentario = Comentario.objects.create(
            historia=historia,
            usuario=request.user,
            texto=texto
        )
        # Aquí creas la notificación para el dueño de la historia
        if historia.usuario != request.user:
            Notificacion.objects.create(
                usuario=historia.usuario,
                mensaje=f"{request.user.username} comentó en tu historia.",
                url=reverse('historia_detalle', args=[historia.pk])
            )
        return redirect('historia_detalle', pk=pk)
    return redirect('historia_detalle', pk=pk)

@login_required
def ocultar_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    Oculto.objects.get_or_create(usuario=request.user, historia=historia)
    return redirect('historias_list')

@login_required
def eliminar_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk, usuario=request.user)
    if request.method == "POST":
        historia.delete()
        messages.success(request, "Historia eliminada correctamente.")
        return redirect('historias_list')
    return redirect('historia_detalle', pk=pk)

@login_required
def like_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    like = LikeComentario.objects.filter(usuario=request.user, comentario=comentario)
    if like.exists():
        like.delete()  # Solo quita el like del usuario actual
    else:
        LikeComentario.objects.create(usuario=request.user, comentario=comentario)
    return redirect('historia_detalle', pk=comentario.historia.pk)

@login_required
def responder_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    historia = comentario.historia
    if request.method == "POST":
        form = ComentarioForm(request.POST)
        if form.is_valid():
            respuesta = form.save(commit=False)
            respuesta.usuario = request.user
            respuesta.historia = historia
            respuesta.parent = comentario
            respuesta.save()
    return redirect('historia_detalle', pk=historia.pk)

@login_required
def eliminar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    historia_pk = comentario.historia.pk
    if comentario.usuario == request.user:
        comentario.delete()
        messages.success(request, "Comentario eliminado correctamente.")
    else:
        messages.error(request, "No puedes eliminar este comentario.")
    return redirect('historia_detalle', pk=historia_pk)

@login_required
def toggle_like_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    like = LikeComentario.objects.filter(usuario=request.user, comentario=comentario)
    if like.exists():
        like.delete()
    else:
        LikeComentario.objects.create(usuario=request.user, comentario=comentario)
    return redirect('historia_detalle', pk=comentario.historia.pk)