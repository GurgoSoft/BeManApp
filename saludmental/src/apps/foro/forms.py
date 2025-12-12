from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Historia, Comentario

class HistoriaForm(forms.ModelForm):
    class Meta:
        model = Historia
        fields = ['titulo', 'contenido']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['titulo'].widget = forms.TextInput(attrs={'class': 'form-control'})
        self.fields['contenido'].widget = forms.Textarea(attrs={'class': 'form-control'})

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['texto'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Escribe tu comentario...')
        })
