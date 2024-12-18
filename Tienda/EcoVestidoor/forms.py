from django import forms
from .models import ProductoBodega, ProductoTienda
from .models import CustomUser
from django.contrib.auth.hashers import make_password

class CustomUserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Ingrese la nueva contraseña (opcional)'}),
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'name', 'role']  # Excluir "password"

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')

        if password:
            user.set_password(password)  # Usa `set_password` solo si hay contraseña nueva

        if commit:
            user.save()
        return user

class ProductoBodegaForm(forms.ModelForm):
    class Meta:
        model = ProductoBodega
        fields = ['nombre', 'codigo_barras', 'precio', 'stock']

class ProductoTiendaForm(forms.ModelForm):
    class Meta:
        model = ProductoTienda
        fields = ['nombre', 'codigo_barras', 'precio', 'stock']

class MoverProductoForm(forms.Form):
    cantidad = forms.IntegerField(min_value=1, label='Cantidad a Mover')

class ActualizarStockForm(forms.Form):
    cantidad = forms.IntegerField(min_value=1, label='Cantidad a Agregar')

