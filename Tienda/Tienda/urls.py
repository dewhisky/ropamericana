from django.contrib import admin
from django.urls import path
from EcoVestidoor.views import (
    home, 
    listar_productos, 
    agregar_producto_bodega, 
    actualizar_stock, 
    mover_a_tienda, 
    agregar_venta, 
    historial_ventas, 
    eliminar_venta, 
    detalle_venta, 
    registrar_venta, 
    agregar_producto_a_venta, 
    eliminar_producto_carrito, 
    imprimir_boleta,
    listar_usuarios, 
    agregar_usuario, 
    eliminar_usuario, 
    ver_auditoria,
    editar_usuario,
    login_view,
    logout_view,
    dashboard,
    banner_view,
    eliminar_producto,
    mover_a_bodega
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', banner_view, name='banner'),  # Ruta principal al banner
    path('home/', home, name='home'),  # Ruta al dashboard/home
    path('productos/', listar_productos, name='listar_productos'),
    path('productos/agregar/', agregar_producto_bodega, name='agregar_producto_bodega'),
    path('productos/actualizar/<int:pk>/', actualizar_stock, name='actualizar_stock'),
    path('productos/mover/<int:pk>/', mover_a_tienda, name='mover_a_tienda'),
    path('productos/eliminar/<int:pk>/', eliminar_producto, name='eliminar_producto'),
    path('productos/mover_a_bodega/<int:pk>/', mover_a_bodega, name='mover_a_bodega'),



   
    path('ventas/agregar/', agregar_venta, name='agregar_venta'),
    path('ventas/', historial_ventas, name='historial_ventas'),
    path('ventas/eliminar/<int:pk>/', eliminar_venta, name='eliminar_venta'),
    path('ventas/detalle/<int:pk>/', detalle_venta, name='detalle_venta'),
    path('ventas/registrar/', registrar_venta, name='registrar_venta'),
    path('ventas/agregar_producto/', agregar_producto_a_venta, name='agregar_producto_a_venta'),
    path('ventas/eliminar_producto/<int:indice>/', eliminar_producto_carrito, name='eliminar_producto_carrito'),
    path('ventas/imprimir_boleta/<int:venta_id>/', imprimir_boleta, name='imprimir_boleta'),
    
    path('usuarios/', listar_usuarios, name='listar_usuarios'),
    path('usuarios/agregar/', agregar_usuario, name='agregar_usuario'),
    path('usuarios/eliminar/<int:pk>/', eliminar_usuario, name='eliminar_usuario'),
    path('auditoria/', ver_auditoria, name='ver_auditoria'),
    path('usuarios/editar/<int:pk>/', editar_usuario, name='editar_usuario'),

    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
