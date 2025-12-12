from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.editar_perfil, name='editar_perfil'),
    path('notificaciones/', views.notificaciones, name='notificaciones'),
    path('notificacion/leida/<int:pk>/', views.marcar_notificacion_leida, name='notificacion_leida'),
    path('notificaciones/marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),
    # APIs para sidebar móvil
    path('api/user-stats/', views.user_stats_api, name='user_stats_api'),
    path('api/notificaciones-recientes/', views.notificaciones_recientes_api, name='notificaciones_recientes_api'),
]