from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='agenda_index'),
    # Admin
    path('admin/', views.admin_dashboard, name='agenda_admin_dashboard'),
    path('admin/eventos/', views.admin_evento_list, name='admin_evento_list'),
    path('admin/eventos/nuevo/', views.admin_evento_create, name='admin_evento_create'),
    path('admin/eventos/<int:pk>/editar/', views.admin_evento_edit, name='admin_evento_edit'),
    path('admin/eventos/<int:pk>/eliminar/', views.admin_evento_delete, name='admin_evento_delete'),
    # Inscripciones
    path('inscribirme/<int:pk>/', views.inscribirme, name='agenda_inscribirme'),
]
