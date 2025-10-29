from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.translation import gettext as _
from .forms import HistoriaForm
from .moderation import moderate_text
from .models import Historia, Comentario, Like, LikeComentario
from apps.usuarios.models import Notificacion
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Count
from django.urls import reverse
from django.template.loader import render_to_string

def historias_list(request):
    historias = (
        Historia.objects
        .filter(oculto=False)
        .annotate(
            likes_count=Count('like_set', distinct=True),
            comentarios_count=Count('comentario', distinct=True)
        )
        .order_by('-fecha')
    )
    
    # Lista de historias con like del usuario
    user_historia_likes = []
    if request.user.is_authenticated:
        user_historia_likes = list(
            Like.objects.filter(usuario=request.user).values_list('historia_id', flat=True)
        )
    
    return render(request, "foro/historias_list.html", {
        "historias": historias,
        "user_historia_likes": user_historia_likes
    })

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

    comentarios_total = Comentario.objects.filter(historia=historia).count()

    return render(request, "foro/historia_detalle.html", {
        "historia": historia,
        "comentarios": comentarios,
        "liked_story": liked_story,
        "user_likes": user_likes,
        "comment_like_counts": comment_like_counts,
        "comentarios_total": comentarios_total,
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
    else:
        # Crear notificación si es un nuevo like y no es el autor
        if historia.usuario != request.user:
            Notificacion.objects.create(
                usuario=historia.usuario,
                mensaje=f"{request.user.username} le dio like a tu historia '{historia.titulo}'",
                tipo='like',
                url=reverse('historia_detalle', kwargs={'pk': historia.pk})
            )
    likes_count = historia.like_set.count()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"liked": liked, "likes_count": likes_count, "historia_id": historia.pk})
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
    else:
        # Crear notificación si es un nuevo like y no es el autor
        if comentario.usuario != request.user:
            Notificacion.objects.create(
                usuario=comentario.usuario,
                mensaje=f"{request.user.username} le dio like a tu comentario",
                tipo='like',
                url=reverse('historia_detalle', kwargs={'pk': comentario.historia.pk}) + f"#comment-{comentario.pk}"
            )
    # Contar nuevamente usando el related manager correcto tras posible toggle
    likes_count = LikeComentario.objects.filter(comentario=comentario).count()
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
    parent_id = comentario.parent_id
    comentario.delete()
    messages.success(request, _("Comentario eliminado."))
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        total = Comentario.objects.filter(historia_id=historia_pk).count()
        replies_count = 0
        if parent_id:
            replies_count = Comentario.objects.filter(parent_id=parent_id).count()
        return JsonResponse({"ok": True, "deleted_id": pk, "total": total, "parent_id": parent_id, "replies_count": replies_count})
    return redirect("historia_detalle", pk=historia_pk)

@login_required
@require_POST
def editar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    # Permitir editar si es autor del comentario, autor de la historia o staff
    if not (request.user == comentario.usuario or request.user == comentario.historia.usuario or request.user.is_staff):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"ok": False, "error": _("No tienes permiso para editar este comentario."), "comentario_id": comentario.pk}, status=403)
        return HttpResponseForbidden()
    texto = (request.POST.get("texto") or "").strip()
    ok = False
    error = None
    if not texto:
        error = _("El texto no puede estar vacío.")
        messages.error(request, error)
    else:
        mod = moderate_text(texto)
        if not mod.allowed:
            error = _("Tu comentario contiene contenido no permitido.")
            messages.error(request, error)
        else:
            comentario.texto = texto
            comentario.save()
            messages.success(request, _("Comentario actualizado."))
            ok = True
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"ok": ok, "comentario_id": comentario.pk, "texto": comentario.texto, "error": error})
    return redirect("historia_detalle", pk=comentario.historia_id)

@login_required
@require_POST
def comentar_historia(request, pk):
    historia = get_object_or_404(Historia, pk=pk)
    if request.method == "POST":
        if request.user == historia.usuario:
            msg = _("No puedes comentar tu propia historia.")
            messages.error(request, msg)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"ok": False, "error": msg}, status=400)
        else:
            texto = (request.POST.get("texto") or "").strip()
            if not texto:
                msg = _("El comentario no puede estar vacío.")
                messages.error(request, msg)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"ok": False, "error": msg}, status=400)
            else:
                mod = moderate_text(texto)
                if not mod.allowed:
                    msg = _("Tu comentario contiene contenido no permitido.")
                    messages.error(request, msg)
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({"ok": False, "error": msg}, status=400)
                else:
                    c = Comentario.objects.create(historia=historia, usuario=request.user, texto=texto)
                    
                    # Crear notificación para el autor de la historia
                    if historia.usuario != request.user:
                        Notificacion.objects.create(
                            usuario=historia.usuario,
                            mensaje=f"{request.user.username} comentó en tu historia '{historia.titulo}'",
                            tipo='comentario',
                            url=reverse('historia_detalle', kwargs={'pk': historia.pk}) + f"#comment-{c.pk}"
                        )
                    
                    messages.success(request, _("Comentario publicado."))
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        html = render_to_string('foro/_comentario_item.html', {
                            'c': c,
                            'user_likes': set(),
                            'comment_like_counts': {},
                        }, request=request)
                        total = Comentario.objects.filter(historia=historia).count()
                        return JsonResponse({"ok": True, "html": html, "total": total})
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
        msg = _("El texto no puede estar vacío.")
        messages.error(request, msg)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"ok": False, "error": msg}, status=400)
    else:
        mod = moderate_text(texto)
        if not mod.allowed:
            msg = _("Tu respuesta contiene contenido no permitido.")
            messages.error(request, msg)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"ok": False, "error": msg}, status=400)
        else:
            c = Comentario.objects.create(
                historia=parent.historia,
                usuario=request.user,
                texto=texto,
                parent=parent,
            )
            
            # Crear notificación para el autor del comentario padre
            if parent.usuario != request.user:
                Notificacion.objects.create(
                    usuario=parent.usuario,
                    mensaje=f"{request.user.username} respondió a tu comentario",
                    tipo='respuesta',
                    url=reverse('historia_detalle', kwargs={'pk': parent.historia.pk}) + f"#comment-{c.pk}"
                )
            
            messages.success(request, _("Respuesta publicada."))
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                html = render_to_string('foro/_comentario_item.html', {
                    'c': c,
                    'user_likes': set(),
                    'comment_like_counts': {},
                }, request=request)
                total = Comentario.objects.filter(historia=parent.historia).count()
                replies_count = Comentario.objects.filter(parent=parent).count()
                return JsonResponse({"ok": True, "html": html, "parent_id": parent.pk, "total": total, "replies_count": replies_count})
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