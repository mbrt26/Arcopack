# erp_config/urls.py

from django.contrib import admin
from django.urls import path, include # Asegúrate que 'include' esté importado

urlpatterns = [
    # Ruta para el Admin de Django
    path('admin/', admin.site.urls),

    # --- Rutas para la API v1 ---
    # Incluir URLs de la API de Productos bajo /api/v1/
    path('api/v1/', include('productos.urls')),

    # Incluir URLs de la API de Producción bajo /api/v1/produccion/
    path('api/v1/produccion/', include('produccion.urls')),
    path('api/v1/inventario/', include('inventario.urls')),

    # Incluir URLs de otras apps aquí cuando las tengas
    # path('api/v1/inventario/', include('inventario.urls')),
    # path('api/v1/clientes/', include('clientes.urls')),
    # path('api/v1/personal/', include('personal.urls')),

]
