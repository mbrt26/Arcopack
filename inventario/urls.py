# inventario/urls.py
from django.urls import path
from .views import (
    StockActualAPIView, StockListView,
    MateriaPrimaListView, MateriaPrimaCreateView, MateriaPrimaUpdateView, MateriaPrimaDetailView,
    LoteListView, LoteDetailView, MovimientoListView
)

# This should match the namespace used in erp_config/urls.py
app_name = 'inventario_web'

urlpatterns = [
    path('stock/', StockListView.as_view(), name='stock-list'),
    path('api/stock/', StockActualAPIView.as_view(), name='stock-actual'),
    
    # Materias Primas URLs
    path('materias-primas/', MateriaPrimaListView.as_view(), name='materia-prima-list'),
    path('materias-primas/crear/', MateriaPrimaCreateView.as_view(), name='materia-prima-create'),
    path('materias-primas/editar/<int:pk>/', MateriaPrimaUpdateView.as_view(), name='materia-prima-edit'),
    path('materias-primas/<int:pk>/', MateriaPrimaDetailView.as_view(), name='materia-prima-detail'),
    
    # Lotes
    path('lotes/', LoteListView.as_view(), name='lote-list'),
    path('lotes/<int:pk>/', LoteDetailView.as_view(), name='lote-detail'),
    
    # Movimientos de inventario
    path('movimientos/', MovimientoListView.as_view(), name='movimiento-list'),
]