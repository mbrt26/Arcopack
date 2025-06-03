# inventario/urls.py
from django.urls import path
from .views import (
    StockActualAPIView, 
    MateriaPrimaListView, MateriaPrimaCreateView, MateriaPrimaUpdateView,
    MateriaPrimaDetailView, LoteCreateView,
    LoteListView, MovimientoListView
)
from .views_productos import (
    ProductoEnProcesoListView, ProductoTerminadoListView,
    ProductoEnProcesoDetailView, ProductoEnProcesoHistoryView,
    TransferirWIPView, ConsumirWIPView, AjustarStockWIPView,
    ProductoTerminadoDetailView, ProductoTerminadoHistoryView,
    TransferirPTView, ConsumirPTView, AjustarStockPTView, DespacharPTView,
    DespachosListView
)

# This should match the namespace used in erp_config/urls.py
app_name = 'inventario_web'

urlpatterns = [
    path('stock/', StockActualAPIView.as_view(), name='stock-actual'),
    
    # Materias Primas URLs
    path('materias-primas/', MateriaPrimaListView.as_view(), name='materia-prima-list'),
    path('materias-primas/crear/', MateriaPrimaCreateView.as_view(), name='materia-prima-create'),
    path('materias-primas/<int:pk>/', MateriaPrimaDetailView.as_view(), name='materia-prima-detail'),
    path('materias-primas/editar/<int:pk>/', MateriaPrimaUpdateView.as_view(), name='materia-prima-edit'),
    
    # Lotes
    path('lotes/', LoteListView.as_view(), name='lote-list'),
    path('lotes/crear/', LoteCreateView.as_view(), name='lote-create'),
    
    # Productos en Proceso (WIP)
    path('wip/', ProductoEnProcesoListView.as_view(), name='wip-list'),
    path('wip/<int:pk>/', ProductoEnProcesoDetailView.as_view(), name='wip-detail'),
    path('wip/<int:pk>/history/', ProductoEnProcesoHistoryView.as_view(), name='wip-history'),
    path('wip/<int:pk>/transferir/', TransferirWIPView.as_view(), name='wip-transferir'),
    path('wip/<int:pk>/consumir/', ConsumirWIPView.as_view(), name='wip-consumir'),
    path('wip/<int:pk>/ajustar/', AjustarStockWIPView.as_view(), name='wip-ajustar'),
    
    # Productos Terminados (PT)
    path('productos-terminados/', ProductoTerminadoListView.as_view(), name='pt-list'),
    path('productos-terminados/<int:pk>/', ProductoTerminadoDetailView.as_view(), name='pt-detail'),
    path('productos-terminados/<int:pk>/history/', ProductoTerminadoHistoryView.as_view(), name='pt-history'),
    path('productos-terminados/<int:pk>/transferir/', TransferirPTView.as_view(), name='pt-transferir'),
    path('productos-terminados/<int:pk>/consumir/', ConsumirPTView.as_view(), name='pt-consumir'),
    path('productos-terminados/<int:pk>/ajustar/', AjustarStockPTView.as_view(), name='pt-ajustar'),
    path('productos-terminados/<int:pk>/despachar/', DespacharPTView.as_view(), name='pt-despachar'),
    
    # Movimientos de inventario
    path('movimientos/', MovimientoListView.as_view(), name='movimiento-list'),
    
    # Despachos
    path('despachos/', DespachosListView.as_view(), name='despachos-list'),
]