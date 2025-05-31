# configuracion/urls.py

from django.urls import path
from . import views

app_name = 'configuracion_web'

urlpatterns = [
    # Unidades de medida
    path('unidades-medida/', views.UnidadMedidaListView.as_view(), name='unidad-medida-list'),
    path('unidades-medida/nueva/', views.UnidadMedidaCreateView.as_view(), name='unidad-medida-create'),
    path('unidades-medida/<int:pk>/editar/', views.UnidadMedidaUpdateView.as_view(), name='unidad-medida-update'),
    
    # Categorías de materia prima
    path('categorias-mp/', views.CategoriaMPListView.as_view(), name='categoria-mp-list'),
    path('categorias-mp/nueva/', views.CategoriaMPCreateView.as_view(), name='categoria-mp-create'),
    path('categorias-mp/<int:pk>/editar/', views.CategoriaMPUpdateView.as_view(), name='categoria-mp-update'),
    
    # Ubicaciones
    path('ubicaciones/', views.UbicacionListView.as_view(), name='ubicacion-list'),
    path('ubicaciones/nueva/', views.UbicacionCreateView.as_view(), name='ubicacion-create'),
    path('ubicaciones/<int:pk>/editar/', views.UbicacionUpdateView.as_view(), name='ubicacion-update'),
    
    # Procesos
    path('procesos/', views.ProcesoListView.as_view(), name='proceso-list'),
    path('procesos/nuevo/', views.ProcesoCreateView.as_view(), name='proceso-create'),
    path('procesos/<int:pk>/editar/', views.ProcesoUpdateView.as_view(), name='proceso-update'),
    
    # Máquinas
    path('maquinas/', views.MaquinaListView.as_view(), name='maquina-list'),
    path('maquinas/nueva/', views.MaquinaCreateView.as_view(), name='maquina-create'),
    path('maquinas/<int:pk>/editar/', views.MaquinaUpdateView.as_view(), name='maquina-update'),
]