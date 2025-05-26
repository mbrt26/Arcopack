# productos/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductoTerminadoViewSet,
    ProductoListView,
    ProductoDetailView,
    ProductoCreateView,
    ProductoUpdateView,
)

# Crear un router de DRF
# DefaultRouter crea automáticamente las URLs para las acciones estándar del ViewSet (list, create, retrieve, update, destroy)
api_router = DefaultRouter()

# Registrar el ViewSet con el router
# 'productos' será el prefijo de la URL (ej: /api/v1/productos/)
# 'ProductoTerminadoViewSet' es la clase que maneja las peticiones
# 'basename' se usa para generar los nombres de las URLs internas de Django
api_router.register(r'productos', ProductoTerminadoViewSet, basename='producto')

# Nombre de la aplicación para namespacing (debe coincidir con el namespace en erp_config/urls.py)
app_name = 'productos_web'

urlpatterns = [
    path('', ProductoListView.as_view(), name='producto-list'),
    path('nuevo/', ProductoCreateView.as_view(), name='producto-create'),
    path('<int:pk>/', ProductoDetailView.as_view(), name='producto-detail'),
    path('<int:pk>/editar/', ProductoUpdateView.as_view(), name='producto-update'),
]

# API urls for local inclusion
api_urlpatterns = [
    path('api/', include(api_router.urls)),
]

# Expose API endpoints when this file is included directly
urlpatterns += api_urlpatterns

