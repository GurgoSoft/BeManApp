from django.db import models
from django.conf import settings

class Evento(models.Model):
    nombre = models.CharField(max_length=200)
    fecha = models.DateTimeField()

class Inscripcion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
