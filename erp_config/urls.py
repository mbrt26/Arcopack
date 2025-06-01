# erp_config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from productos.urls import api_urlpatterns as productos_api_urls

def redirect_to_production(request):
    return redirect('produccion_web:orden-produccion-list')

urlpatterns = [
    # Ruta raíz redirige a la lista de órdenes de producción
    path('', redirect_to_production, name='root'),

    # Ruta para el Admin de Django
    path('admin/', admin.site.urls),

    # Rutas principales de la aplicación
    path('produccion/', include(('produccion.urls', 'produccion_web'), namespace='produccion_web')),
    path('inventario/', include(('inventario.urls', 'inventario_web'), namespace='inventario_web')),
    path('productos/', include(('productos.urls', 'productos_web'), namespace='productos_web')),
    path('pedidos/', include(('pedidos.urls', 'pedidos_web'), namespace='pedidos_web')),
    path('clientes/', include(('clientes.urls', 'clientes_web'), namespace='clientes_web')),
    path('personal/', include(('personal.urls', 'personal_web'), namespace='personal_web')),
    path('configuracion/', include(('configuracion.urls', 'configuracion_web'), namespace='configuracion_web')),
    path('notificaciones/', include(('notificaciones.urls', 'notificaciones_web'), namespace='notificaciones_web')),

    # Autenticación y usuarios
    path('users/', include(([
        path('login/', auth_views.LoginView.as_view(
            template_name='users/login.html',
            next_page='root'
        ), name='login'),
        path('logout/', auth_views.LogoutView.as_view(
            next_page='root'
        ), name='logout'),
        path('profile/', auth_views.TemplateView.as_view(
            template_name='users/profile.html'
        ), name='profile'),
        path('password/change/', auth_views.PasswordChangeView.as_view(
            template_name='users/password_change.html',
            success_url='/'
        ), name='change-password'),
    ], 'users'))),

    # --- Rutas para la API v1 ---
    path('api/v1/', include((productos_api_urls, 'api_productos'))),
    path('api/v1/produccion/', include(('produccion.urls', 'api_produccion'))),
    path('api/v1/inventario/', include(('inventario.urls', 'api_inventario'))),
    path('api/v1/pedidos/', include(('pedidos.urls', 'api_pedidos'))),
]
