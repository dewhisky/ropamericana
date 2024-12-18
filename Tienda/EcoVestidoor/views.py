from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponseRedirect
from io import BytesIO
from reportlab.pdfgen import canvas
from pathlib import Path
from datetime import datetime
import pytz
from .models import ProductoBodega, ProductoTienda, Venta, VentaProducto, CustomUser, LogUsuario
from .forms import ProductoBodegaForm, MoverProductoForm, ActualizarStockForm, CustomUserForm
import os
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.sessions.models import Session
from django.utils.timezone import now



def banner_view(request):
    return render(request, 'banner.html')



# Decorador para verificar si el usuario es administrador
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

@user_passes_test(lambda u: u.role == 'admin')  # Solo para administradores
def listar_usuarios(request):
    usuarios = CustomUser.objects.all()  # Obtiene todos los usuarios
    return render(request, 'listar_usuarios.html', {'usuarios': usuarios})

# Autenticación y dashboard
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard') 
        else:
            return render(request, 'banner.html', {
                'error_message': "Credenciales inválidas. Intente nuevamente.",
                'show_modal': True  
            })

    return render(request, 'banner.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    if request.user.role == 'admin':
        return redirect('listar_usuarios')
    elif request.user.role == 'vendor':
        return redirect('listar_productos')
    else:
        messages.error(request, "Rol de usuario no reconocido.")
        return redirect('logout')

def home(request):
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('listar_usuarios')
        elif request.user.role == 'vendor':
            return redirect('listar_productos')
    return redirect('login')

@login_required
def listar_productos(request):
    # Filtro para productos en Bodega
    buscar_bodega = request.GET.get('buscar_bodega', '')
    productos_bodega = ProductoBodega.objects.all()
    if buscar_bodega:
        productos_bodega = productos_bodega.filter(nombre__icontains=buscar_bodega)

    # Filtro para productos en Tienda
    buscar_tienda = request.GET.get('buscar_tienda', '')
    productos_tienda = ProductoTienda.objects.all()
    if buscar_tienda:
        productos_tienda = productos_tienda.filter(nombre__icontains=buscar_tienda)

    return render(request, 'listar_productos.html', {
        'productos_bodega': productos_bodega,
        'productos_tienda': productos_tienda,
    })

@login_required
def agregar_producto_bodega(request):
    if request.method == 'POST':
        form = ProductoBodegaForm(request.POST)
        if form.is_valid():
            producto = form.save()
            # Registrar la acción en la auditoría
            LogUsuario.objects.create(
                usuario=request.user,
                accion=f"Agregó el producto '{producto.nombre}' a la bodega."
            )
            messages.success(request, "Producto agregado correctamente.")
            return redirect('listar_productos')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = ProductoBodegaForm()
    return render(request, 'agregar_producto.html', {'form': form})


@login_required
def actualizar_stock(request, pk):
    producto_bodega = get_object_or_404(ProductoBodega, pk=pk)
    if request.method == 'POST':
        form = ActualizarStockForm(request.POST)
        if form.is_valid():
            cantidad = form.cleaned_data['cantidad']
            producto_bodega.stock += cantidad
            producto_bodega.save()
            # Registrar la acción en la auditoría
            LogUsuario.objects.create(
                usuario=request.user,
                accion=f"Actualizó el stock del producto '{producto_bodega.nombre}' en {cantidad} unidades."
            )
            messages.success(request, "Stock actualizado correctamente.")
            return redirect('listar_productos')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = ActualizarStockForm()
    return render(request, 'actualizar_stock.html', {'form': form, 'producto': producto_bodega})


@login_required
def mover_a_tienda(request, pk):
    producto_bodega = get_object_or_404(ProductoBodega, pk=pk)
    
    if producto_bodega.stock == 0:
        return render(request, 'mover_a_tienda.html', {
            'error': 'No hay stock disponible en la bodega para este producto.', 
            'producto': producto_bodega
        })

    if request.method == 'POST':
        form = MoverProductoForm(request.POST)
        if form.is_valid():
            cantidad = form.cleaned_data['cantidad']
            if cantidad > producto_bodega.stock:
                form.add_error('cantidad', 'La cantidad a mover excede el stock disponible')
            else:
                # Mover producto
                producto_tienda, created = ProductoTienda.objects.get_or_create(
                    codigo_barras=producto_bodega.codigo_barras,
                    defaults={
                        'nombre': producto_bodega.nombre,
                        'precio': producto_bodega.precio,
                        'stock': 0
                    }
                )
                producto_tienda.stock += cantidad
                producto_tienda.save()
                producto_bodega.stock -= cantidad
                producto_bodega.save()

                # Registrar la acción en la auditoría
                LogUsuario.objects.create(
                    usuario=request.user,
                    accion=f"Movió {cantidad} unidades del producto '{producto_bodega.nombre}' (ID {producto_bodega.id}) de la bodega a la tienda."
                )

                messages.success(request, f"Producto '{producto_bodega.nombre}' movido a la tienda correctamente.")
                return redirect('listar_productos')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = MoverProductoForm()

    return render(request, 'mover_a_tienda.html', {'form': form, 'producto': producto_bodega})

@login_required
def mover_a_bodega(request, pk):
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 0))
        producto = get_object_or_404(ProductoTienda, pk=pk)

        # Verificar si el producto está en el carrito
        carrito = request.session.get('carrito', [])
        for item in carrito:
            if item['codigo_barras'] == producto.codigo_barras:
                messages.error(request, f"El producto '{producto.nombre}' está en el carrito y no puede ser movido.")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        # Verificar si la cantidad es válida
        if cantidad > producto.stock:
            messages.error(request, f"No se puede mover más del stock disponible ({producto.stock}).")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if cantidad <= 0:
            messages.error(request, "La cantidad debe ser mayor a 0.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        # Mover la cantidad especificada
        try:
            bodega_producto, created = ProductoBodega.objects.get_or_create(
                codigo_barras=producto.codigo_barras,
                defaults={
                    'nombre': producto.nombre,
                    'precio': producto.precio,
                    'stock': 0
                }
            )
            bodega_producto.stock += cantidad
            bodega_producto.save()

            producto.stock -= cantidad
            if producto.stock == 0:
                producto.delete()  # Eliminar producto si el stock llega a 0
            else:
                producto.save()

            messages.success(request, f"Se movieron {cantidad} unidades de '{producto.nombre}' a la bodega.")
        except Exception as e:
            messages.error(request, f"Hubo un error al mover el producto: {str(e)}")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def eliminar_producto(request, pk):
    # Obtener el producto de bodega
    producto_bodega = get_object_or_404(ProductoBodega, pk=pk)
    
    # Verificar si el producto está en la tienda
    producto_en_tienda = ProductoTienda.objects.filter(codigo_barras=producto_bodega.codigo_barras).exists()

    # Verificar si el producto está asociado a una venta en proceso
    producto_en_venta = VentaProducto.objects.filter(producto__codigo_barras=producto_bodega.codigo_barras).exists()

    if producto_en_tienda or producto_en_venta:
        messages.error(
            request, 
            f"No se puede eliminar el producto '{producto_bodega.nombre}' porque está en la tienda o asociado a una venta."
        )
        return redirect('listar_productos')
    
    # Registrar la acción en el log de auditoría
    LogUsuario.objects.create(
        usuario=request.user,
        accion=f"Eliminó el producto '{producto_bodega.nombre}' con código de barras '{producto_bodega.codigo_barras}'."
    )
    
    # Eliminar producto si no hay restricciones
    producto_bodega.delete()
    messages.success(request, f"El producto '{producto_bodega.nombre}' fue eliminado correctamente.")
    return redirect('listar_productos')



# Gestión de ventas
@login_required
def agregar_venta(request):
    carrito = request.session.get('carrito', [])
    total = 0
    for item in carrito:
        if 'precio' in item and 'cantidad' in item:
            item['subtotal'] = item['precio'] * item['cantidad']
        else:
            item['subtotal'] = 0
        total += item['subtotal']
    return render(request, 'agregar_venta.html', {'carrito': carrito, 'total': total})


@login_required
def historial_ventas(request):
    # Obtenemos las fechas de inicio y fin del formulario
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    # Si ambas fechas están presentes, filtramos por rango
    if fecha_inicio and fecha_fin:
        # Convertimos las fechas a objetos datetime
        try:
            inicio = parse_datetime(fecha_inicio + " 00:00:00")
            fin = parse_datetime(fecha_fin + " 23:59:59")
        except ValueError:
            inicio, fin = None, None

        if inicio and fin:
            ventas = Venta.objects.filter(fecha__range=(inicio, fin))
        else:
            ventas = Venta.objects.all()
    else:
        # Si no se envía rango, mostramos todas las ventas
        ventas = Venta.objects.all()

    # Ordenamos manualmente por fecha descendente en Python
    ventas = sorted(ventas, key=lambda v: v.fecha, reverse=True)

    return render(request, 'historial_ventas.html', {'ventas': ventas})


@login_required
def eliminar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    productos_vendidos = VentaProducto.objects.filter(venta=venta)

    if request.method == 'POST':
        # Restablecer el stock
        for item in productos_vendidos:
            producto = item.producto
            producto.stock += item.cantidad
            producto.save()

        # Registrar la acción en la auditoría
        LogUsuario.objects.create(
            usuario=request.user,
            accion=f"Eliminó la venta con ID {venta.id}."
        )

        # Eliminar la venta y sus relaciones
        venta.delete()
        messages.success(request, "Venta eliminada correctamente.")
        return redirect('historial_ventas')
    return render(request, 'historial_ventas.html', {'ventas': Venta.objects.all().order_by('-fecha')})

@login_required
def detalle_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    productos = VentaProducto.objects.filter(venta=venta)  # Obtener productos relacionados

    # Verificar si el usuario existe o fue eliminado
    usuario = venta.usuario.name if venta.usuario else "Este usuario ya no existe"

    return render(request, 'detalle_venta.html', {
        'venta': venta,
        'productos': productos,
        'usuario': usuario,
    })


@login_required
def registrar_venta(request):
    carrito = request.session.get('carrito', [])
    if not carrito:
        messages.error(request, 'El carrito está vacío.')
        return redirect('agregar_venta')

    total = sum(item['precio'] * item['cantidad'] for item in carrito)

    try:
        with transaction.atomic():
            venta = Venta.objects.create(total=total, usuario=request.user)
            for item in carrito:
                producto = ProductoTienda.objects.get(codigo_barras=item['codigo_barras'])
                VentaProducto.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=item['cantidad'],
                    subtotal=item['precio'] * item['cantidad']
                )
                producto.stock -= item['cantidad']
                producto.save()

            # Registrar la acción en la auditoría
            LogUsuario.objects.create(
                usuario=request.user,
                accion=f"Registró una venta con ID {venta.id} por un total de ${venta.total}."
            )
            request.session['carrito'] = []
            messages.success(request, "Venta registrada correctamente.")
            return redirect('imprimir_boleta', venta_id=venta.id)
    except Exception as e:
        print(f"Error al registrar la venta: {e}")
        messages.error(request, 'Error al registrar la venta.')
        return redirect('agregar_venta')


@login_required
def agregar_producto_a_venta(request):
    if request.method == 'POST':
        codigo_barras = request.POST.get('codigo_barras')
        cantidad = int(request.POST.get('cantidad', 1))

        try:
            producto = ProductoTienda.objects.get(codigo_barras=codigo_barras)
        except ProductoTienda.DoesNotExist:
            messages.error(request, f"No se encontró ningún producto con el código de barras: {codigo_barras}")
            return redirect('agregar_venta')

        # Verificar si la cantidad solicitada supera el stock disponible
        if cantidad > producto.stock:
            messages.error(request, f"No hay suficiente stock disponible para {producto.nombre}. Stock actual: {producto.stock}")
            return redirect('agregar_venta')

        # Obtener el carrito de la sesión
        carrito = request.session.get('carrito', [])

        # Verificar si el producto ya está en el carrito
        for item in carrito:
            if item['codigo_barras'] == codigo_barras:
                # Verificar si la nueva cantidad excederá el stock disponible
                nueva_cantidad = item['cantidad'] + cantidad
                if nueva_cantidad > producto.stock:
                    messages.error(request, f"No hay suficiente stock para agregar más {producto.nombre}. Stock actual: {producto.stock}")
                    return redirect('agregar_venta')

                # Incrementar la cantidad y subtotal si la cantidad es válida
                item['cantidad'] = nueva_cantidad
                item['subtotal'] = item['precio'] * item['cantidad']
                break
        else:
            # Si el producto no está en el carrito, agregarlo como nuevo
            carrito.append({
                'codigo_barras': producto.codigo_barras,
                'nombre': producto.nombre,
                'precio': producto.precio,
                'cantidad': cantidad,
                'subtotal': producto.precio * cantidad,
            })

        # Guardar el carrito actualizado en la sesión
        request.session['carrito'] = carrito
        messages.success(request, "Producto agregado al carrito.")
        return redirect('agregar_venta')

    return redirect('agregar_venta')



@login_required
def eliminar_producto_carrito(request, indice):
    carrito = request.session.get('carrito', [])
    if 0 <= indice < len(carrito):
        del carrito[indice]
        request.session['carrito'] = carrito
        messages.success(request, 'Producto eliminado del carrito.')
    else:
        messages.error(request, 'Índice de producto inválido.')
    return redirect('agregar_venta')

@login_required
def imprimir_boleta(request, venta_id):
    # Detectar carpeta Descargas del usuario en Windows
    downloads_folder = str(Path.home() / "Downloads")

    # Obtener la venta y los productos relacionados
    venta = get_object_or_404(Venta, id=venta_id)
    productos = VentaProducto.objects.filter(venta=venta)

    # Crear un buffer en memoria para el PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    # Generar contenido del PDF
    pdf.drawString(100, 800, f"Boleta de Venta #{venta.id}")
    pdf.drawString(100, 780, f"Fecha: {venta.fecha}")
    pdf.drawString(100, 760, f"Usuario: {venta.usuario.name if venta.usuario else 'Sin Usuario'}")

    y = 720
    pdf.drawString(100, y, "Productos:")
    for producto in productos:
        y -= 20
        pdf.drawString(
            100, y, f"- {producto.producto.nombre}: {producto.cantidad} x ${producto.producto.precio} = ${producto.subtotal}"
        )

    y -= 40
    pdf.drawString(100, y, f"Total: ${venta.total}")

    pdf.save()

    # Guardar el archivo PDF en la carpeta Descargas
    file_name = f"boleta_{venta.id}.pdf"
    file_path = os.path.join(downloads_folder, file_name)

    try:
        with open(file_path, "wb") as f:
            f.write(buffer.getvalue())

        # Mensaje de éxito
        messages.success(request, f"La boleta se guardó en Descargas como {file_name}.")
    except Exception as e:
        # Manejo de errores al guardar el archivo
        messages.error(request, f"Error al guardar la boleta: {e}")

    return redirect('historial_ventas')

@user_passes_test(lambda u: u.role == 'admin')
def agregar_usuario(request):
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.set_password(form.cleaned_data['password'])
            usuario.save()
            LogUsuario.objects.create(usuario=request.user, accion=f"Creó el usuario {usuario.username}")
            return redirect('listar_usuarios')
    else:
        form = CustomUserForm()
    return render(request, 'agregar_usuario.html', {'form': form})

@user_passes_test(lambda u: u.role == 'admin')
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)
    
    # Verificar si el usuario tiene una sesión activa
    sesiones = Session.objects.filter(expire_date__gte=now())
    usuario_activo = False

    for sesion in sesiones:
        data = sesion.get_decoded()
        if str(usuario.id) == str(data.get('_auth_user_id')):
            usuario_activo = True
            break

    if usuario_activo:
        return render(request, 'eliminar_usuario.html', {
            'usuario': usuario,
            'error': 'No puedes eliminar un usuario que está actualmente en sesión activa.',
        })

    if request.method == 'POST':
        LogUsuario.objects.create(usuario=request.user, accion=f"Eliminó el usuario {usuario.username}")
        usuario.delete()
        return redirect('listar_usuarios')
    
    return render(request, 'eliminar_usuario.html', {'usuario': usuario})

@user_passes_test(lambda u: u.role == 'admin')
def ver_auditoria(request):
    tipo = request.GET.get('tipo', None)
    if tipo == 'movimientos':
        logs = LogUsuario.objects.filter(accion__icontains='Movió').order_by('-fecha')
    else:
        logs = LogUsuario.objects.all().order_by('-fecha')
    return render(request, 'auditoria.html', {'logs': logs})



@user_passes_test(lambda u: u.role == 'admin')
def editar_usuario(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)

    if request.method == 'POST':
        form = CustomUserForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()

            # Si el usuario editado es el mismo que está autenticado
            if usuario == request.user:
                messages.success(request, "Has editado tu propio usuario. La sesión se cerrará por seguridad.")
                logout(request)
                return redirect('login')
            else:
                messages.success(request, "Usuario editado exitosamente.")
                return redirect('listar_usuarios')
        else:
            messages.error(request, "Por favor, corrige los errores del formulario.")
    else:
        form = CustomUserForm(instance=usuario)

    return render(request, 'editar_usuario.html', {'form': form, 'usuario': usuario})


