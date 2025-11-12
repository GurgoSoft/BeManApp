from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='agenda_index'),
    path('evento/<int:pk>/', views.evento_detalle, name='agenda_evento_detalle'),
    path('evento/<int:pk>/calificar/', views.calificar_evento, name='agenda_calificar_evento'),
    path('evento/<int:pk>/comentar/', views.comentar_evento, name='agenda_comentar_evento'),
    path('comentarios/<int:pk>/like/', views.like_evento_comentario, name='agenda_like_comentario'),
    path('comentarios/<int:pk>/responder/', views.responder_evento_comentario, name='agenda_responder_comentario'),
    path('comentarios/<int:pk>/editar/', views.editar_evento_comentario, name='agenda_editar_comentario'),
    path('comentarios/<int:pk>/eliminar/', views.eliminar_evento_comentario, name='agenda_eliminar_comentario'),
    # Admin
    path('admin/', views.admin_dashboard, name='agenda_admin_dashboard'),
    path('admin/eventos/', views.admin_evento_list, name='admin_evento_list'),
    path('admin/eventos/nuevo/', views.admin_evento_create, name='admin_evento_create'),
    path('admin/eventos/<int:pk>/editar/', views.admin_evento_edit, name='admin_evento_edit'),
    path('admin/eventos/<int:pk>/eliminar/', views.admin_evento_delete, name='admin_evento_delete'),
    path('admin/eventos/<int:pk>/fotos/', views.admin_evento_fotos, name='admin_evento_fotos'),
    path('foto/<int:pk>/eliminar/', views.eliminar_evento_foto, name='eliminar_evento_foto'),
    # Admin - Gestión de datos
    path('admin/usuarios/', views.admin_usuarios_list, name='admin_usuarios_list'),
    path('admin/inscripciones/', views.admin_inscripciones_list, name='admin_inscripciones_list'),
    path('admin/historias/', views.admin_historias_list, name='admin_historias_list'),
    path('admin/comentarios/', views.admin_comentarios_list, name='admin_comentarios_list'),
    path('admin/notificaciones/', views.admin_notificaciones_list, name='admin_notificaciones_list'),
    path('admin/calificaciones/', views.admin_calificaciones_list, name='admin_calificaciones_list'),
    # Inscripciones
    path('inscribirme/<int:pk>/', views.inscribirme, name='agenda_inscribirme'),
]
