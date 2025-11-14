"""
Comando de Django para probar el sistema de notificaciones por email
Usar: python manage.py test_notificaciones
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.usuarios.email_utils import enviar_email_notificacion

User = get_user_model()


class Command(BaseCommand):
    help = 'Prueba el sistema de notificaciones por email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email del destinatario (por defecto usa el primer usuario staff)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('PRUEBA DE NOTIFICACIONES POR EMAIL'))
        self.stdout.write(self.style.WARNING('=' * 60))
        
        # Obtener email destinatario
        email_destino = options.get('email')
        
        if not email_destino:
            # Buscar primer usuario staff
            user = User.objects.filter(is_staff=True).first()
            if not user:
                self.stdout.write(self.style.ERROR('\n❌ No se encontró ningún usuario staff'))
                self.stdout.write(self.style.ERROR('   Crea un superusuario con: python manage.py createsuperuser'))
                return
            
            email_destino = user.email
            if not email_destino:
                self.stdout.write(self.style.ERROR(f'\n❌ El usuario {user.username} no tiene email configurado'))
                return
        
        self.stdout.write(f'\n📧 Enviando email de prueba a: {email_destino}')
        
        # Enviar email de prueba
        exito = enviar_email_notificacion(
            destinatario_email=email_destino,
            asunto='Prueba de Notificaciones - Iterum',
            mensaje_texto='Este es un email de prueba del sistema de notificaciones de Iterum.',
            url_accion='http://localhost:8000'
        )
        
        if exito:
            self.stdout.write(self.style.SUCCESS('\n✅ Email enviado exitosamente!'))
            self.stdout.write(self.style.SUCCESS(f'   Revisa la bandeja de entrada de: {email_destino}'))
            self.stdout.write('\n📋 Verifica que:')
            self.stdout.write('   1. El email llegó a la bandeja de entrada (no spam)')
            self.stdout.write('   2. El formato HTML se ve correctamente')
            self.stdout.write('   3. El botón "Ver más" funciona')
        else:
            self.stdout.write(self.style.ERROR('\n❌ Error al enviar email'))
            self.stdout.write(self.style.ERROR('   Revisa la configuración en config/settings.py'))
            self.stdout.write('\n📋 Verifica que:')
            self.stdout.write('   1. Las credenciales de Gmail sean correctas')
            self.stdout.write('   2. La verificación en dos pasos esté activada')
            self.stdout.write('   3. La contraseña de aplicación sea válida')
        
        self.stdout.write(self.style.WARNING('\n' + '=' * 60))
        self.stdout.write(self.style.WARNING('FIN DE LA PRUEBA'))
        self.stdout.write(self.style.WARNING('=' * 60 + '\n'))
