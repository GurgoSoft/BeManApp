from django.conf import settings
from urllib.parse import quote

def whatsapp(request):
    """
    Inyecta variables de WhatsApp en el contexto de plantillas.
    Construye la URL de wa.me solo si hay número configurado.
    """
    number = getattr(settings, 'WHATSAPP_SUPPORT_NUMBER', '')
    enabled = getattr(settings, 'WHATSAPP_HELP_ENABLED', True)
    default_message = getattr(settings, 'WHATSAPP_DEFAULT_MESSAGE', 'Hola, necesito ayuda con Be Man Be Woman.')

    if number:
        url = f"https://wa.me/{number}?text={quote(default_message)}"
    else:
        url = ""

    return {
        'WHATSAPP_HELP_ENABLED': enabled,
        'WHATSAPP_SUPPORT_NUMBER': number,
        'WHATSAPP_DEFAULT_MESSAGE': default_message,
        'WHATSAPP_SUPPORT_URL': url,
    }
