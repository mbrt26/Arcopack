# erp_config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views

def redirect_to_production(request):
    return redirect('produccion_web:orden-produccion-list')

urlpatterns = [
    # Ruta raíz redirige a la lista de órdenes de producción
    path('', redirect_to_production, name='root'),

    # Ruta para el Admin de Django
    path('admin/', admin.site.urls),

    # Rutas principales de la aplicación (solo vistas web)
    path('produccion/', include('produccion.urls', namespace='produccion_web')),
    path('inventario/', include('inventario.urls', namespace='inventario_web')),
    path('productos/', include('productos.urls', namespace='productos_web')),
    path('pedidos/', include('pedidos.urls', namespace='pedidos_web')),
    path('clientes/', include('clientes.urls', namespace='clientes_web')),
    path('personal/', include('personal.urls', namespace='personal_web')),
    path('configuracion/', include('configuracion.urls', namespace='configuracion_web')),
    path('notificaciones/', include('notificaciones.urls', namespace='notificaciones_web')),

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

    # --- Rutas para la API v1 (separadas y usando solo las rutas API) ---
    # Las rutas API están incluidas dentro de cada aplicación como 'api/' 
    # por lo que no necesitamos duplicar las inclusiones aquí
]
