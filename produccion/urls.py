# produccion/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importar TODOS los ViewSets de esta app que se expondrán en la API
from .views import (
    OrdenProduccionViewSet,
    RegistroImpresionViewSet,
    RefiladoViewSet,
    SelladoViewSet,
    DobladoViewSet
)

# Crear un router para la API de producción
# DefaultRouter crea automáticamente las URLs para las acciones estándar
# y las acciones personalizadas (@action) de los ViewSets.
router = DefaultRouter()

# Registrar todos los ViewSets en el router
router.register(r'ordenes-produccion', OrdenProduccionViewSet, basename='ordenproduccion')
router.register(r'registros-impresion', RegistroImpresionViewSet, basename='registroimpresion')
router.register(r'refilados', RefiladoViewSet, basename='refilado')
router.register(r'sellados', SelladoViewSet, basename='sellado')
router.register(r'doblados', DobladoViewSet, basename='doblado')

# Nombre de la aplicación para namespacing (útil para reverse URL lookups)
app_name = 'produccion'

# Las urlpatterns de esta app incluyen todas las URLs generadas por el router
urlpatterns = [
    # Monta todas las URLs del router (ej: /ordenes-produccion/, /refilados/{pk}/, etc.)
    # bajo la raíz definida en erp_config/urls.py (que es /api/v1/produccion/)
    path('', include(router.urls)),
]