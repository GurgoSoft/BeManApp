from django.contrib import admin
from .models import Evento, Inscripcion

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha')
    search_fields = ('nombre',)

@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'evento', 'fecha_inscripcion')
    search_fields = ('usuario__email', 'evento__nombre')
    list_filter = ('evento',)
