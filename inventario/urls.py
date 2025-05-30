# inventario/urls.py
from django.urls import path
from .views import (
    StockActualAPIView, 
    MateriaPrimaListView, MateriaPrimaCreateView, MateriaPrimaUpdateView,
    MateriaPrimaDetailView, LoteCreateView,
    LoteListView, MovimientoListView
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
    
    # Movimientos de inventario
    path('movimientos/', MovimientoListView.as_view(), name='movimiento-list'),
]