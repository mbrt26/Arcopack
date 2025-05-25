# configuracion/urls.py

from django.urls import path
from . import views

app_name = 'configuracion'

urlpatterns = [
    path('unidades-medida/', views.UnidadMedidaListView.as_view(), name='unidad-medida-list'),
    path('categorias-mp/', views.CategoriaMPListView.as_view(), name='categoria-mp-list'),
    path('ubicaciones/', views.UbicacionListView.as_view(), name='ubicacion-list'),
    path('procesos/', views.ProcesoListView.as_view(), name='proceso-list'),
    path('maquinas/', views.MaquinaListView.as_view(), name='maquina-list'),
]