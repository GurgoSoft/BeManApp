from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

def _merge(a, b):
    a = (a or '').strip()
    b = (b or '').strip()
    return ('%s %s' % (a, b)).strip() if a and b else (a or b)

@register.filter(name='add_class')
def add_class(value, css):
    # Caso 1: BoundField -> usar as_widget y preservar clases existentes del widget
    if hasattr(value, 'as_widget'):
        current = value.field.widget.attrs.get('class', '')
        return value.as_widget(attrs={'class': _merge(current, css)})

    # Caso 2: ya es HTML (SafeString). Insertar/mergear class en la primera etiqueta
    html = str(value)

    if 'class="' in html:
        # Añade las clases a la primera ocurrencia de class
        html = re.sub(
            r'class="([^"]*)"',
            lambda m: f'class="{_merge(m.group(1), css)}"',
            html,
            count=1
        )
    else:
        # Inserta atributo class en la primera etiqueta
        html = re.sub(
            r'(<\w+)(\s|>)',
            lambda m: f'{m.group(1)} class="{css}"{m.group(2)}',
            html,
            count=1
        )
    return mark_safe(html)