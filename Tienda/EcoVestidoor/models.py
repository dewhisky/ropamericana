from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# tablas de usuario 

class CustomUser(AbstractUser):
    ROLES = [
        ('admin', 'Administrador'),
        ('vendor', 'Vendedor'),
    ]
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLES, default='vendor')
    is_logged_in = models.BooleanField(default=False)  # Nuevo campo


    def __str__(self):
        return f"{self.username} ({self.role})"

class LogUsuario(models.Model):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    accion = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.accion} - {self.fecha}"





# tablas de venta y inventario


class ProductoBodega(models.Model):
    nombre = models.CharField(max_length=200)
    precio = models.IntegerField()
    stock = models.IntegerField()
    codigo_barras = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class ProductoTienda(models.Model):
    nombre = models.CharField(max_length=200)
    precio = models.IntegerField()
    stock = models.IntegerField()
    codigo_barras = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre
    
class Venta(models.Model):
    # Relación con usuario (quién realiza la venta)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas'
    )
    
    # Fecha de creación de la venta
    fecha = models.DateTimeField(auto_now_add=True)
    
    # Total de la venta
    total = models.IntegerField()
    
    # Método de pago
    metodo_pago = models.CharField(
        max_length=20,
        choices=[('Efectivo', 'Efectivo'), ('Transferencia', 'Transferencia')],
        default='Efectivo'
    )
    
    # Campo para almacenar el archivo PDF de la boleta (si es necesario)
    boleta_pdf = models.FileField(upload_to='boletas/', null=True, blank=True)

    def __str__(self):
        return f"Venta {self.id} - {self.usuario.name if self.usuario else 'Sin Usuario'} - Total: ${self.total}"
    
class VentaProducto(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    producto = models.ForeignKey(ProductoTienda, on_delete=models.SET_NULL, null=True, blank=True)  # Cambiar a SET_NULL
    cantidad = models.IntegerField()
    subtotal = models.IntegerField()

    def __str__(self):
        return f"{self.producto.nombre if self.producto else 'Producto eliminado'} - {self.cantidad} x {self.subtotal}"

