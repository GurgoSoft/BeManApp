from django import forms
from django.utils.translation import gettext_lazy as _
from .models import CustomUser

class PerfilForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'foto_perfil', 'first_name', 'last_name', 'bio', 'phone_code', 'phone_number'
        ]
        # No definir widgets aquí para configurarlos en __init__ con traducciones dinámicas
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar widgets con traducciones dinámicas
        self.fields['username'].widget = forms.TextInput(attrs={'class': 'form-control'})
        self.fields['email'].widget = forms.EmailInput(attrs={'class': 'form-control'})
        self.fields['phone_code'].widget = forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ej: +57')
        })
        self.fields['phone_number'].widget = forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ej: 3001234567')
        })

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')
        if foto:
            ext = foto.name.split('.')[-1].lower()
            if ext not in ['png', 'jpg', 'jpeg']:
                raise forms.ValidationError(_("Solo se permiten imágenes PNG, JPG o JPEG."))
        return foto

    def clean_phone_code(self):
        code = self.cleaned_data.get('phone_code', '').strip()
        if not code.isdigit() or int(code) <= 0:
            raise forms.ValidationError(_("El indicativo debe ser solo números positivos."))
        return code

    def clean_phone_number(self):
        number = self.cleaned_data.get('phone_number', '').strip()
        if not number.isdigit() or int(number) <= 0:
            raise forms.ValidationError(_("El número debe contener solo números positivos, sin espacios ni símbolos."))
        return number

    def clean_phone_number(self):
        number = self.cleaned_data.get('phone_number', '').strip()
        if not number.isdigit() or int(number) <= 0:
            raise forms.ValidationError("El número debe contener solo números positivos, sin espacios ni símbolos.")
        return number