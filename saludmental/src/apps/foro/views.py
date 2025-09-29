from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.translation import gettext as _
from .forms import HistoriaForm
from .profanity import contains_banned_words
from .models import Historia, Comentario, Like, LikeComentario
from apps.usuarios.models import Notificacion
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Count
from django.urls import reverse

def historias_list(request):
    historias = Historia.objects.filter(oculto=False)
    return render(request, "foro/historias_list.html", {"historias": historias})

@login_required
def crear_historia(request):
    if request.method == "POST":
        form = HistoriaForm(request.POST, request.FILES)
        if form.is_valid():
            historia = form.save(commit=False)
            historia.usuario = request.user
            historia.save()
            messages.success(request, _("Historia creada."))
            return redirect("historia_detalle", pk=historia.pk)
    else:
        form = HistoriaForm()
    return render(request, "foro/crear_historia.html", {"form": form})

def historia_detalle(request, pk):
    historia = get_object_or_404(Historia, pk=pk)

    comentarios = (
        Comentario.objects
        .filter(historia=historia, parent__isnull=True)
        .annotate(
            likes_count=Count('likecomentario', distinct=True),
            replies_count=Count('respuestas', distinct=True),
        )
        .select_related("usuario")
        .prefetch_related("respuestas__usuario")
        .order_by('-likes_count', '-replies_count', '-fecha')
    )

    liked_story = False
    user_likes = set()
    if request.user.is_authenticated:
        liked_story = Like.objects.filter(historia=historia, usuario=request.user).exists()
        user_likes = set(
            LikeComentario.objects.filter(usuario=request.user, comentario__historia=historia)
            .values_list("comentario_id", flat=True)
        )

    # Diccionario: { comentario_id: total_likes }
    comment_like_counts = {
        row["comentario_id"]: row["total"]
        for row in (
            LikeComentario.objects
            .filter(comentario__historia=historia)
            .values("comentario_id")
            .annotate(total=Count("id"))
        )
    }

    return render(request, "foro/historia_detalle.html", {
        "historia": historia,
        "comentarios": comentarios,
        "liked_story": liked_story,
        "user_likes": user_likes,
        "comment_like_counts": comment_like_counts,
    })

@login_required
@require_POST
def like_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    like, created = Like.objects.get_or_create(historia=historia, usuario=request.user)
    liked = True
    if not created:
        like.delete()
        liked = False
    likes_count = historia.like_set.count()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"liked": liked, "likes_count": likes_count})
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("historia_detalle", kwargs={"pk": pk})
    return redirect(next_url)

@login_required
@require_POST
def like_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    like, created = LikeComentario.objects.get_or_create(comentario=comentario, usuario=request.user)
    liked = True
    if not created:
        like.delete()
        liked = False
    likes_count = comentario.likecomentario.count()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"liked": liked, "likes_count": likes_count, "comentario_id": comentario.pk})
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("historia_detalle", kwargs={"pk": comentario.historia_id})
    return redirect(next_url)

@login_required
@require_POST
def eliminar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if request.user != comentario.usuario and request.user != comentario.historia.usuario:
        return HttpResponseForbidden()
    historia_pk = comentario.historia_id
    comentario.delete()
    messages.success(request, _("Comentario eliminado."))
    return redirect("historia_detalle", pk=historia_pk)

@login_required
@require_POST
def editar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk, usuario=request.user)
    texto = (request.POST.get("texto") or "").strip()
    if not texto:
        messages.error(request, _("El texto no puede estar vacío."))
    elif contains_banned_words(texto):
        messages.error(request, _("Tu comentario contiene palabras no permitidas."))
    else:
        comentario.texto = texto
        comentario.save()
        messages.success(request, _("Comentario actualizado."))
    return redirect("historia_detalle", pk=comentario.historia_id)

@login_required
def comentar_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    if request.method == "POST":
        if request.user == historia.usuario:
            messages.error(request, _("No puedes comentar tu propia historia."))
        else:
            texto = (request.POST.get("texto") or "").strip()
            if not texto:
                messages.error(request, _("El comentario no puede estar vacío."))
            elif contains_banned_words(texto):
                messages.error(request, _("Tu comentario contiene palabras no permitidas."))
            else:
                Comentario.objects.create(historia=historia, usuario=request.user, texto=texto)
                messages.success(request, _("Comentario publicado."))
    return redirect("historia_detalle", pk=pk)

@login_required
def eliminar_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk, usuario=request.user)
    if request.method == "POST":
        historia.delete()
        messages.success(request, _("Historia eliminada."))
        return redirect("historias_list")
    return redirect("historia_detalle", pk=pk)

@login_required
@require_POST
def responder_comentario(request, pk):
    parent = get_object_or_404(Comentario, pk=pk)
    texto = (request.POST.get("texto") or "").strip()
    if not texto:
        messages.error(request, _("El texto no puede estar vacío."))
    elif contains_banned_words(texto):
        messages.error(request, _("Tu respuesta contiene palabras no permitidas."))
    else:
        Comentario.objects.create(
            historia=parent.historia,
            usuario=request.user,
            texto=texto,
            parent=parent,
        )
        messages.success(request, _("Respuesta publicada."))
    return redirect("historia_detalle", pk=parent.historia_id)

@login_required
def editar_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = HistoriaForm(request.POST, request.FILES, instance=historia)
        if form.is_valid():
            form.save()
            messages.success(request, _("Historia actualizada."))
            return redirect("historia_detalle", pk=historia.pk)
    else:
        form = HistoriaForm(instance=historia)
    return render(request, "foro/historia_form.html", {"form": form, "historia": historia, "modo": "editar"})

@login_required
@require_POST
def favorito_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    # Toggle usando el related manager 'favorito_set' (no necesitamos importar el modelo)
    qs = historia.favorito_set.filter(usuario=request.user)
    favored = False
    if qs.exists():
        qs.delete()
    else:
        historia.favorito_set.create(usuario=request.user)
        favored = True
    count = historia.favorito_set.count()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"favored": favored, "favorites_count": count})
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("historia_detalle", kwargs={"pk": pk})
    return redirect(next_url)

@login_required
@require_POST
def ocultar_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    if not (request.user == historia.usuario or request.user.is_staff):
        return HttpResponseForbidden()
    historia.oculto = not historia.oculto
    historia.save()
    messages.success(request, _("Historia ocultada.") if historia.oculto else _("Historia visible."))
    # Si se ocultó, vuelve al listado
    if historia.oculto:
        return redirect("historias_list")
    return redirect("historia_detalle", pk=pk)