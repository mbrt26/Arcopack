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
    RegistroImpresionListView,
    RegistroRefiladoListView,
    RegistroSelladoListView,
    RegistroDobladoListView,
    # Vistas CRUD para orden de producción
    OrdenProduccionCreateView,
    OrdenProduccionUpdateView,
    # Nuevas vistas de detalle por proceso
    RegistroImpresionDetailView,
    RegistroRefiladoDetailView,
    RegistroSelladoDetailView,
    RegistroDobladoDetailView,
    # Nuevas vistas de actualización por proceso
    RegistroImpresionUpdateView,
    RegistroRefiladoUpdateView,
    RegistroSelladoUpdateView,
    RegistroDobladoUpdateView,
    # Vistas para gestión de paros
    iniciar_paro_view,
    finalizar_paro_view,
    # Vista de resumen
    ResumenProduccionView,
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
    path('resumen/', ResumenProduccionView.as_view(), name='resumen-produccion'),

    # URLs para crear y actualizar órdenes de producción
    path('ordenes/nueva/', OrdenProduccionCreateView.as_view(), name='orden-produccion-create'),
    path('ordenes/<int:pk>/detalle/', orden_produccion_detail_view, name='orden-produccion-detail'),
    path('ordenes/<int:pk>/editar/', OrdenProduccionUpdateView.as_view(), name='orden-produccion-update'),
    path('ordenes/<int:pk>/anular/', anular_orden_view, name='orden-produccion-anular'),

    # URLs para listas de registros por proceso (tableros Kanban)
    path('impresion/', ImpresionKanbanView.as_view(), name='impresion-kanban'),
    path('refilado/', RefiladoKanbanView.as_view(), name='refilado-kanban'),
    path('sellado/', SelladoKanbanView.as_view(), name='sellado-kanban'),
    path('doblado/', DobladoKanbanView.as_view(), name='doblado-kanban'),

    # URLs para crear nuevos registros por proceso
    path('impresion/nuevo/', RegistroImpresionCreateView.as_view(), name='impresion-create'),
    path('refilado/nuevo/', RegistroRefiladoCreateView.as_view(), name='refilado-create'),
    path('sellado/nuevo/', RegistroSelladoCreateView.as_view(), name='sellado-create'),
    path('doblado/nuevo/', RegistroDobladoCreateView.as_view(), name='doblado-create'),

    # URLs para registros de impresión
    path('registros/impresion/', RegistroImpresionListView.as_view(), name='registro-impresion-list'),
    path('registros/impresion/<int:pk>/', RegistroImpresionDetailView.as_view(), name='registro-impresion-detail'),
    path('registros/impresion/<int:pk>/editar/', RegistroImpresionUpdateView.as_view(), name='registro-impresion-update'),
    
    # URLs para registros de refilado
    path('registros/refilado/', RegistroRefiladoListView.as_view(), name='registro-refilado-list'),
    path('registros/refilado/<int:pk>/', RegistroRefiladoDetailView.as_view(), name='registro-refilado-detail'),
    path('registros/refilado/<int:pk>/editar/', RegistroRefiladoUpdateView.as_view(), name='registro-refilado-update'),
    
    # URLs para registros de sellado
    path('registros/sellado/', RegistroSelladoListView.as_view(), name='registro-sellado-list'),
    path('registros/sellado/<int:pk>/', RegistroSelladoDetailView.as_view(), name='registro-sellado-detail'),
    path('registros/sellado/<int:pk>/editar/', RegistroSelladoUpdateView.as_view(), name='registro-sellado-update'),
    
    # URLs para registros de doblado
    path('registros/doblado/', RegistroDobladoListView.as_view(), name='registro-doblado-list'),
    path('registros/doblado/<int:pk>/', RegistroDobladoDetailView.as_view(), name='registro-doblado-detail'),
    path('registros/doblado/<int:pk>/editar/', RegistroDobladoUpdateView.as_view(), name='registro-doblado-update'),

    # URLs para gestión de paros
    path('paros/<str:proceso_tipo>/<int:registro_id>/iniciar/', iniciar_paro_view, name='iniciar-paro'),
    path('paros/<str:proceso_tipo>/<int:paro_id>/finalizar/', finalizar_paro_view, name='finalizar-paro'),

    # APIs JSON
    path('lote-wip-json/', lote_wip_json_api, name='lote-wip-json-api'),
    path('lote-mp-json/', lote_mp_json_api, name='lote-mp-json-api'),
    
    # Monta todas las URLs del router (ej: /ordenes-produccion/, /refilados/{pk}/, etc.)
    path('', include(router.urls)),
]