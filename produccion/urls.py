# produccion/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importar TODOS los ViewSets de esta app que se expondrán en la API
from .views import (
    OrdenProduccionViewSet,
    RegistroImpresionViewSet,
    RefiladoViewSet,
    SelladoViewSet,
    DobladoViewSet,
    LoteMPDisponibleViewSet,
    LoteWIPDisponibleViewSet,
    lote_wip_json_api,
    lote_mp_json_api,
    # Vistas HTML añadidas
    orden_produccion_list_view,
    orden_produccion_detail_view,
    anular_orden_view,
    ProcesoListView,
    ResultadosProduccionView,
    ImpresionKanbanView,
    RefiladoKanbanView,
    SelladoKanbanView,
    DobladoKanbanView,
    # Vistas de registro de procesos
    RegistroImpresionCreateView,
    RegistroRefiladoCreateView,
    RegistroSelladoCreateView,
    RegistroDobladoCreateView,
    # Vistas CRUD para orden de producción
    OrdenProduccionCreateView,
    OrdenProduccionUpdateView,
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
router.register(r'lotes-mp-disponibles', LoteMPDisponibleViewSet, basename='lotes-mp-disponibles')
router.register(r'lotes-wip-disponibles', LoteWIPDisponibleViewSet, basename='lotes-wip-disponibles')

# Nombre de la aplicación para namespacing (útil para reverse URL lookups)
# Debe coincidir con el namespace usado en erp_config/urls.py
app_name = 'produccion_web'

# Las urlpatterns de esta app incluyen todas las URLs generadas por el router
urlpatterns = [
    # Vistas HTML - usando nombres consistentes que coincidan con las plantillas
    path('ordenes/', orden_produccion_list_view, name='orden-produccion-list'),
    path('ordenes/<int:pk>/', orden_produccion_detail_view, name='produccion_orden_detail'),
    path('ordenes/<int:pk>/anular/', anular_orden_view, name='anular_orden'),
    path('procesos/', ProcesoListView.as_view(), name='proceso-list'),
    path('resultados/', ResultadosProduccionView.as_view(), name='resultados'),

    # URLs para crear y actualizar órdenes de producción
    path('ordenes/nueva/', OrdenProduccionCreateView.as_view(), name='orden-produccion-create'),
    path('ordenes/<int:pk>/detalle/', orden_produccion_detail_view, name='orden-produccion-detail'),
    path('ordenes/<int:pk>/editar/', OrdenProduccionUpdateView.as_view(), name='orden-produccion-update'),
    path('ordenes/<int:pk>/anular/', anular_orden_view, name='orden-produccion-anular'),

    # Monta todas las URLs del router (ej: /ordenes-produccion/, /refilados/{pk}/, etc.)
    # bajo la raíz definida en erp_config/urls.py (que es /api/v1/produccion/)
    path('lote-wip-json/', lote_wip_json_api, name='lote-wip-json-api'),
    path('lote-mp-json/', lote_mp_json_api, name='lote-mp-json-api'),
    path('', include(router.urls)),

    # URLs para tableros Kanban
    path('kanban/impresion/', ImpresionKanbanView.as_view(), name='impresion-kanban'),
    path('kanban/impresion/nuevo/', RegistroImpresionCreateView.as_view(), name='registro-impresion-create'),
    path('kanban/refilado/', RefiladoKanbanView.as_view(), name='refilado-kanban'),
    path('kanban/refilado/nuevo/', RegistroRefiladoCreateView.as_view(), name='registro-refilado-create'),
    path('kanban/sellado/', SelladoKanbanView.as_view(), name='sellado-kanban'),
    path('kanban/sellado/nuevo/', RegistroSelladoCreateView.as_view(), name='registro-sellado-create'),
    path('kanban/doblado/', DobladoKanbanView.as_view(), name='doblado-kanban'),
    path('kanban/doblado/nuevo/', RegistroDobladoCreateView.as_view(), name='registro-doblado-create'),
]