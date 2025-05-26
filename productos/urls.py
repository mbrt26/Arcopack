# productos/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoTerminadoViewSet # Importa el ViewSet que creamos

# Crear un router de DRF
# DefaultRouter crea automáticamente las URLs para las acciones estándar del ViewSet (list, create, retrieve, update, destroy)
router = DefaultRouter()

# Registrar el ViewSet con el router
# 'productos' será el prefijo de la URL (ej: /api/v1/productos/)
# 'ProductoTerminadoViewSet' es la clase que maneja las peticiones
# 'basename' se usa para generar los nombres de las URLs internas de Django
router.register(r'productos', ProductoTerminadoViewSet, basename='producto')

# Nombre de la aplicación para namespacing (debe coincidir con el namespace en erp_config/urls.py)
app_name = 'productos_web'

# Las urlpatterns de esta app incluyen todas las URLs generadas por el router
urlpatterns = [
    path('', include(router.urls)),
]