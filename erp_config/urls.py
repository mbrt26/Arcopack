# erp_config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views

def redirect_to_production(request):
    return redirect('produccion:produccion_orden_list')

urlpatterns = [
    # Ruta raíz redirige a la lista de órdenes de producción
    path('', redirect_to_production, name='root'),

    # Ruta para el Admin de Django
    path('admin/', admin.site.urls),

    # Rutas principales de la aplicación
    path('produccion/', include(('produccion.urls', 'produccion'))),
    path('inventario/', include(('inventario.urls', 'inventario'))),
    path('productos/', include(('productos.urls', 'productos'))),
    path('configuracion/', include(('configuracion.urls', 'configuracion'))),
    path('notificaciones/', include(('notificaciones.urls', 'notificaciones'))),

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
    path('api/v1/', include(('productos.urls', 'api_productos'))),
    path('api/v1/produccion/', include(('produccion.urls', 'api_produccion'))),
    path('api/v1/inventario/', include(('inventario.urls', 'api_inventario'))),
]
