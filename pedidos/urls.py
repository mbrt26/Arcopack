# pedidos/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api_views import PedidoViewSet, LineaPedidoViewSet, ProductoInfoAPIView

app_name = 'pedidos_web'

# Router para API REST
router = DefaultRouter()
router.register(r'pedidos', PedidoViewSet, basename='pedido')
router.register(r'lineas', LineaPedidoViewSet, basename='lineapedido')

urlpatterns = [
    # URLs de vistas tradicionales (HTML)
    path('', views.PedidoListView.as_view(), name='pedido_list'),
    path('crear/', views.PedidoCreateView.as_view(), name='pedido_create'),
    path('<int:pk>/', views.PedidoDetailView.as_view(), name='pedido_detail'),
    path('<int:pk>/editar/', views.PedidoUpdateView.as_view(), name='pedido_update'),
    path('<int:pk>/eliminar/', views.eliminar_pedido, name='pedido_delete'),
    path('<int:pk>/cambiar-estado/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('<int:pk>/crear-orden-produccion/', views.crear_orden_produccion, name='crear_orden_produccion'),
    
    # URLs de estadísticas y reportes
    path('dashboard/', views.dashboard_pedidos, name='dashboard_pedidos'),
    path('reportes/', views.reporte_pedidos, name='reporte_pedidos'),
    
    # API para obtener información de productos
    path('get-producto-info/', views.get_producto_info, name='get_producto_info'),
    
    # URLs de API REST
    path('api/', include(router.urls)),
    path('api/producto-info/', ProductoInfoAPIView.as_view(), name='api_producto_info'),
]