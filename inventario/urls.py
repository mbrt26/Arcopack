# inventario/urls.py
from django.urls import path
from .views import StockActualAPIView # Importa la vista

app_name = 'inventario'

urlpatterns = [
    path('stock/', StockActualAPIView.as_view(), name='stock-actual'),
    # Aquí podríamos añadir URLs para Lotes, Movimientos si tuvieran ViewSets
]