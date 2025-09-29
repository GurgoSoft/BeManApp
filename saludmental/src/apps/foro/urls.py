from django.urls import path
from . import views

urlpatterns = [
    path('historias/', views.historias_list, name='historias_list'),
    path('historias/crear/', views.crear_historia, name='crear_historia'),
    path('historias/<int:pk>/', views.historia_detalle, name='historia_detalle'),
    path('historias/<int:pk>/like/', views.like_historia, name='like_historia'),
    path('historias/<int:pk>/favorito/', views.favorito_historia, name='favorito_historia'),
    path('historias/<int:pk>/comentar/', views.comentar_historia, name='comentar_historia'),
    path('historias/<int:pk>/ocultar/', views.ocultar_historia, name='ocultar_historia'),
    path('historias/<int:pk>/eliminar/', views.eliminar_historia, name='eliminar_historia'),
    path('historias/<int:pk>/editar/', views.editar_historia, name='editar_historia'),
    path('comentarios/<int:pk>/like/', views.like_comentario, name='like_comentario'),
    path('comentarios/<int:pk>/responder/', views.responder_comentario, name='responder_comentario'),
    path('comentarios/<int:pk>/editar/', views.editar_comentario, name='editar_comentario'),
    path('comentarios/<int:pk>/eliminar/', views.eliminar_comentario, name='eliminar_comentario'),
]
