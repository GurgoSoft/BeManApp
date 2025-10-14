from django.conf import settings
from django.db import models

class Historia(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    oculto = models.BooleanField(default=False)

class Comentario(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    historia = models.ForeignKey(Historia, on_delete=models.CASCADE)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='respuestas', on_delete=models.CASCADE)

class LikeComentario(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comentario = models.ForeignKey(Comentario, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'comentario')

class Like(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    historia = models.ForeignKey('Historia', on_delete=models.CASCADE, related_name='like_set')
    fecha = models.DateTimeField(auto_now_add=True)

# Ejemplo de uso correcto del filtro
historias_visibles = Historia.objects.filter(oculto=False)
