from django import forms
from .models import CustomUser

class PerfilForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'foto_perfil']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')
        if foto:
            ext = foto.name.split('.')[-1].lower()
            if ext not in ['png', 'jpg', 'jpeg']:
                raise forms.ValidationError("Solo se permiten imágenes PNG, JPG o JPEG.")
        return foto