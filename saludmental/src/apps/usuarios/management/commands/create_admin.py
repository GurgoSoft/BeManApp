from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = "Crea un usuario admin/staff si no existe"

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "Admin123!@#")

        user, created = User.objects.get_or_create(email=email, defaults={
            "username": username,
        })
        if created:
            user.set_password(password)
            self.stdout.write(self.style.SUCCESS(f"Usuario creado: {email}"))
        else:
            self.stdout.write("Usuario ya existía, actualizando contraseña y flags…")
            user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(self.style.SUCCESS(
            f"Admin listo: email={email} password={password}"
        ))
