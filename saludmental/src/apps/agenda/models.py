from django.db import models
from django.conf import settings

class Evento(models.Model):
    nombre = models.CharField(max_length=200)
    # Campos nuevos para administración y visualización
    titulo = models.CharField(max_length=200, blank=True, default="")
    descripcion_corta = models.CharField(max_length=280, blank=True, default="")
    lugar = models.CharField(max_length=200, blank=True, default="")
    imagen = models.ImageField(upload_to="eventos/", null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateTimeField()
    publicado = models.BooleanField(default=False)
    fecha_publicacion = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.titulo or self.nombre

class Inscripcion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("usuario", "evento")
