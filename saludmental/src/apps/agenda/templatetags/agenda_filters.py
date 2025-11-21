from django import template
from django.utils import timezone
import pytz

register = template.Library()

@register.filter(name='format_cop')
def format_cop(value):
    """
    Formatea un número como precio en pesos colombianos.
    Ejemplos:
    - 1000 -> 1.000
    - 1000000 -> 1.000.000
    - 0 -> Gratis
    """
    try:
        num = float(value)
        if num == 0:
            return "Gratis"
        # Formatear con separador de miles (punto)
        return f"{int(num):,}".replace(',', '.')
    except (ValueError, TypeError):
        return value


@register.filter(name='colombia_datetime')
def colombia_datetime(value, format_string='%d %b %Y, %I:%M %p'):
    """
    Convierte una fecha/hora a zona horaria de Colombia (COT/UTC-5)
    y la formatea en español con AM/PM.
    
    Formato por defecto: "23 Nov 2025, 10:30 AM"
    """
    if not value:
        return ""
    
    try:
        # Zona horaria de Colombia (COT - Colombia Time, UTC-5)
        colombia_tz = pytz.timezone('America/Bogota')
        
        # Si el valor ya tiene zona horaria, convertir a Colombia
        if timezone.is_aware(value):
            local_time = value.astimezone(colombia_tz)
        else:
            # Si es naive, asumir UTC y convertir a Colombia
            utc_time = pytz.utc.localize(value)
            local_time = utc_time.astimezone(colombia_tz)
        
        # Formatear la fecha
        formatted = local_time.strftime(format_string)
        
        # Traducir nombres de meses al español
        meses = {
            'Jan': 'Ene', 'Feb': 'Feb', 'Mar': 'Mar', 'Apr': 'Abr',
            'May': 'May', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago',
            'Sep': 'Sep', 'Oct': 'Oct', 'Nov': 'Nov', 'Dec': 'Dic'
        }
        
        for en, es in meses.items():
            formatted = formatted.replace(en, es)
        
        return formatted
        
    except Exception as e:
        return str(value)


@register.filter(name='colombia_time')
def colombia_time(value):
    """
    Muestra solo la hora en formato 12h AM/PM para Colombia.
    Ejemplo: "10:30 AM"
    """
    return colombia_datetime(value, '%I:%M %p')


@register.filter(name='colombia_date')
def colombia_date(value):
    """
    Muestra solo la fecha para Colombia.
    Ejemplo: "Domingo 23 Nov 2025"
    """
    if not value:
        return ""
    
    try:
        colombia_tz = pytz.timezone('America/Bogota')
        
        if timezone.is_aware(value):
            local_time = value.astimezone(colombia_tz)
        else:
            utc_time = pytz.utc.localize(value)
            local_time = utc_time.astimezone(colombia_tz)
        
        # Nombres de días en español
        dias = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        
        # Nombres de meses en español
        meses = {
            'Jan': 'Ene', 'Feb': 'Feb', 'Mar': 'Mar', 'Apr': 'Abr',
            'May': 'May', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago',
            'Sep': 'Sep', 'Oct': 'Oct', 'Nov': 'Nov', 'Dec': 'Dic'
        }
        
        # Formatear
        formatted = local_time.strftime('%A %d %b %Y')
        
        # Traducir
        for en, es in {**dias, **meses}.items():
            formatted = formatted.replace(en, es)
        
        return formatted
        
    except Exception:
        return str(value)
