from django import forms
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    foto_perfil = models.ImageField(upload_to='perfil/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone_code = models.CharField(max_length=6, blank=True, null=True)  # Indicativo internacional
    phone_number = models.CharField(max_length=20, blank=True, null=True)  # Solo el número

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class Favorito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    historia = models.ForeignKey('foro.Historia', on_delete=models.CASCADE, related_name='favorito_set')
    # ...


class Notificacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    mensaje = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

