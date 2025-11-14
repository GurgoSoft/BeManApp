"""
Utilidades para envío de notificaciones por correo electrónico
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def enviar_email_notificacion(destinatario_email, asunto, mensaje_texto, mensaje_html=None, url_accion=None):
    """
    Envía un correo electrónico de notificación a un usuario.
    
    Args:
        destinatario_email: Email del destinatario
        asunto: Asunto del correo
        mensaje_texto: Mensaje en texto plano
        mensaje_html: Mensaje en HTML (opcional)
        url_accion: URL para acción relacionada (opcional)
    
    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    try:
        # Si no hay mensaje HTML, generar uno básico desde el texto
        if not mensaje_html:
            if url_accion:
                mensaje_html = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                            <h2 style="color: #2c3e50;">Iterum - Comunidad de Hombres</h2>
                            <p>{mensaje_texto}</p>
                            <div style="margin: 30px 0;">
                                <a href="{url_accion}" 
                                   style="background-color: #3498db; color: white; padding: 12px 24px; 
                                          text-decoration: none; border-radius: 5px; display: inline-block;">
                                    Ver más
                                </a>
                            </div>
                            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                            <p style="color: #7f8c8d; font-size: 12px;">
                                Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                            </p>
                        </div>
                    </body>
                </html>
                """
            else:
                mensaje_html = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                            <h2 style="color: #2c3e50;">Iterum - Comunidad de Hombres</h2>
                            <p>{mensaje_texto}</p>
                            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                            <p style="color: #7f8c8d; font-size: 12px;">
                                Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                            </p>
                        </div>
                    </body>
                </html>
                """
        
        # Enviar el correo
        send_mail(
            subject=asunto,
            message=mensaje_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario_email],
            html_message=mensaje_html,
            fail_silently=False,
        )
        
        logger.info(f"Email enviado exitosamente a {destinatario_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar email a {destinatario_email}: {str(e)}")
        return False


def enviar_notificacion_like_historia(usuario_destinatario, usuario_origen, historia_titulo, url_historia):
    """Envía notificación por email cuando alguien da like a una historia"""
    asunto = f"A {usuario_origen} le gustó tu historia"
    mensaje = f"{usuario_origen} le dio like a tu historia '{historia_titulo}'"
    
    mensaje_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">💙 Nueva interacción en tu historia</h2>
                <p><strong>{usuario_origen}</strong> le dio like a tu historia <strong>"{historia_titulo}"</strong></p>
                <div style="margin: 30px 0;">
                    <a href="{url_historia}" 
                       style="background-color: #3498db; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver historia
                    </a>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
    </html>
    """
    
    return enviar_email_notificacion(
        destinatario_email=usuario_destinatario.email,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        url_accion=url_historia
    )


def enviar_notificacion_comentario_historia(usuario_destinatario, usuario_origen, historia_titulo, url_comentario):
    """Envía notificación por email cuando alguien comenta una historia"""
    asunto = f"{usuario_origen} comentó tu historia"
    mensaje = f"{usuario_origen} comentó en tu historia '{historia_titulo}'"
    
    mensaje_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">💬 Nuevo comentario en tu historia</h2>
                <p><strong>{usuario_origen}</strong> comentó en tu historia <strong>"{historia_titulo}"</strong></p>
                <div style="margin: 30px 0;">
                    <a href="{url_comentario}" 
                       style="background-color: #27ae60; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver comentario
                    </a>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
    </html>
    """
    
    return enviar_email_notificacion(
        destinatario_email=usuario_destinatario.email,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        url_accion=url_comentario
    )


def enviar_notificacion_respuesta_comentario(usuario_destinatario, usuario_origen, url_respuesta):
    """Envía notificación por email cuando alguien responde a un comentario"""
    asunto = f"{usuario_origen} respondió a tu comentario"
    mensaje = f"{usuario_origen} respondió a tu comentario"
    
    mensaje_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">💬 Nueva respuesta a tu comentario</h2>
                <p><strong>{usuario_origen}</strong> respondió a tu comentario</p>
                <div style="margin: 30px 0;">
                    <a href="{url_respuesta}" 
                       style="background-color: #9b59b6; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver respuesta
                    </a>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
    </html>
    """
    
    return enviar_email_notificacion(
        destinatario_email=usuario_destinatario.email,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        url_accion=url_respuesta
    )


def enviar_notificacion_like_comentario(usuario_destinatario, usuario_origen, url_comentario):
    """Envía notificación por email cuando alguien da like a un comentario"""
    asunto = f"A {usuario_origen} le gustó tu comentario"
    mensaje = f"{usuario_origen} le dio like a tu comentario"
    
    mensaje_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">👍 Le gustó tu comentario</h2>
                <p><strong>{usuario_origen}</strong> le dio like a tu comentario</p>
                <div style="margin: 30px 0;">
                    <a href="{url_comentario}" 
                       style="background-color: #e67e22; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver comentario
                    </a>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
    </html>
    """
    
    return enviar_email_notificacion(
        destinatario_email=usuario_destinatario.email,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        url_accion=url_comentario
    )


def enviar_notificacion_evento_publicado(usuario_destinatario, evento_titulo, url_evento):
    """Envía notificación por email cuando se publica un nuevo evento"""
    asunto = f"Nuevo evento: {evento_titulo}"
    mensaje = f"Nuevo evento publicado: {evento_titulo}"
    
    mensaje_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">🎉 Nuevo evento disponible</h2>
                <p>Se ha publicado un nuevo evento: <strong>{evento_titulo}</strong></p>
                <p>¡No te lo pierdas! Inscríbete ahora.</p>
                <div style="margin: 30px 0;">
                    <a href="{url_evento}" 
                       style="background-color: #e74c3c; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver evento e inscribirme
                    </a>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
    </html>
    """
    
    return enviar_email_notificacion(
        destinatario_email=usuario_destinatario.email,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        url_accion=url_evento
    )


def enviar_notificacion_inscripcion_evento(usuario_staff, usuario_inscrito, evento_titulo, url_evento):
    """Envía notificación por email al staff cuando alguien se inscribe a un evento"""
    display_name = usuario_inscrito.get_full_name() or usuario_inscrito.username
    asunto = f"Nueva inscripción: {display_name} - {evento_titulo}"
    mensaje = f"{display_name} se inscribió a: {evento_titulo}"
    
    mensaje_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">📝 Nueva inscripción</h2>
                <p><strong>{display_name}</strong> se inscribió al evento <strong>"{evento_titulo}"</strong></p>
                <div style="margin: 30px 0;">
                    <a href="{url_evento}" 
                       style="background-color: #16a085; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver detalles del evento
                    </a>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
    </html>
    """
    
    return enviar_email_notificacion(
        destinatario_email=usuario_staff.email,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        url_accion=url_evento
    )


def enviar_notificacion_comentario_evento(usuario_destinatario, usuario_origen, evento_titulo, url_comentario):
    """Envía notificación por email cuando alguien comenta en un evento"""
    asunto = f"{usuario_origen} comentó en {evento_titulo}"
    mensaje = f"{usuario_origen} comentó en el evento '{evento_titulo}'"
    
    mensaje_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">💬 Nuevo comentario en evento</h2>
                <p><strong>{usuario_origen}</strong> comentó en el evento <strong>"{evento_titulo}"</strong></p>
                <div style="margin: 30px 0;">
                    <a href="{url_comentario}" 
                       style="background-color: #27ae60; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver comentario
                    </a>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
    </html>
    """
    
    return enviar_email_notificacion(
        destinatario_email=usuario_destinatario.email,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        url_accion=url_comentario
    )


def enviar_email_bienvenida(usuario, url_home):
    """Envía email de bienvenida cuando un usuario se registra"""
    display_name = usuario.get_full_name() or usuario.username
    asunto = "¡Bienvenido a Iterum - Comunidad de Hombres!"
    mensaje = f"Hola {display_name}, bienvenido a nuestra comunidad. ¡Nos alegra que estés aquí!"
    
    mensaje_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background-color: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h1 style="color: #2c3e50; text-align: center; margin-bottom: 30px;">
                        🎉 ¡Bienvenido a Iterum!
                    </h1>
                    
                    <p style="font-size: 16px; color: #34495e;">
                        Hola <strong>{display_name}</strong>,
                    </p>
                    
                    <p style="font-size: 16px; color: #34495e;">
                        ¡Nos alegra mucho que te hayas unido a nuestra comunidad! Iterum es un espacio 
                        creado para hombres que buscan compartir experiencias, aprender y crecer juntos.
                    </p>
                    
                    <div style="background-color: #ecf0f1; padding: 20px; border-radius: 5px; margin: 30px 0;">
                        <h3 style="color: #2c3e50; margin-top: 0;">¿Qué puedes hacer aquí?</h3>
                        <ul style="color: #34495e; line-height: 2;">
                            <li>📖 <strong>Compartir tu historia</strong> y conectar con otros</li>
                            <li>💬 <strong>Participar en el foro</strong> de discusión</li>
                            <li>🎯 <strong>Inscribirte a eventos</strong> y actividades</li>
                            <li>🎙️ <strong>Escuchar podcasts</strong> inspiradores</li>
                            <li>🤝 <strong>Apoyar y ser apoyado</strong> por la comunidad</li>
                        </ul>
                    </div>
                    
                    <p style="font-size: 16px; color: #34495e;">
                        Explora la plataforma, participa y no dudes en compartir tus experiencias. 
                        ¡Esta es tu comunidad!
                    </p>
                    
                    <div style="text-align: center; margin: 40px 0;">
                        <a href="{url_home}" 
                           style="background-color: #3498db; color: white; padding: 15px 40px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;
                                  font-size: 16px; font-weight: bold;">
                            Explorar Iterum
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #7f8c8d; text-align: center; margin-top: 30px;">
                        Si tienes alguna pregunta, no dudes en contactarnos.
                    </p>
                </div>
                
                <p style="color: #95a5a6; font-size: 12px; text-align: center; margin-top: 20px;">
                    Este es un correo automático de Iterum. Por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
    </html>
    """
    
    return enviar_email_notificacion(
        destinatario_email=usuario.email,
        asunto=asunto,
        mensaje_texto=mensaje,
        mensaje_html=mensaje_html,
        url_accion=url_home
    )

