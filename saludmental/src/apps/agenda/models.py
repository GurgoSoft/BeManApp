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


class EventoFoto(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='fotos')
    imagen = models.ImageField(upload_to="eventos/fotos/")
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto {self.pk} de {self.evento}"


class EventoCalificacion(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='calificaciones')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    estrellas = models.PositiveSmallIntegerField(default=5)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("evento", "usuario")

    def __str__(self):
        return f"{self.estrellas}★ por {self.usuario} en {self.evento}"


class EventoComentario(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='respuestas', on_delete=models.CASCADE)

    def __str__(self):
        return f"Comentario de {self.usuario} en {self.evento}: {self.texto[:30]}..."


class EventoLikeComentario(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comentario = models.ForeignKey(EventoComentario, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("usuario", "comentario")
