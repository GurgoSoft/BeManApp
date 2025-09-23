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
]