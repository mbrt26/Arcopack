from django.urls import path
from . import views

app_name = 'clientes_web'

urlpatterns = [
    # Lista de clientes
    path('', views.ClienteListView.as_view(), name='cliente_list'),
    # Detalle de cliente
    path('<int:pk>/', views.ClienteDetailView.as_view(), name='cliente_detail'),
    # Crear nuevo cliente
    path('nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    # Editar cliente existente
    path('<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    # Eliminar cliente
    path('<int:pk>/eliminar/', views.ClienteDeleteView.as_view(), name='cliente_delete'),
]
