from django.contrib import admin
from .models import Evento, Inscripcion
from .models import EventoFoto, EventoCalificacion, EventoComentario

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha')
    search_fields = ('nombre',)

@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'evento', 'fecha_inscripcion')
    search_fields = ('usuario__email', 'evento__nombre')
    list_filter = ('evento',)
@admin.register(EventoFoto)
class EventoFotoAdmin(admin.ModelAdmin):
    list_display = ("id", "evento", "fecha_subida")
    list_filter = ("evento",)

@admin.register(EventoCalificacion)
class EventoCalificacionAdmin(admin.ModelAdmin):
    list_display = ("evento", "usuario", "estrellas", "fecha")
    list_filter = ("estrellas", "evento")

@admin.register(EventoComentario)
class EventoComentarioAdmin(admin.ModelAdmin):
    list_display = ("evento", "usuario", "fecha")
    search_fields = ("texto",)
