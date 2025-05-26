from django.urls import path
from . import views

app_name = 'personal_web'

urlpatterns = [
    # Lista de colaboradores
    path('', views.ColaboradorListView.as_view(), name='colaborador_list'),
    # Detalle de colaborador
    path('<int:pk>/', views.ColaboradorDetailView.as_view(), name='colaborador_detail'),
    # Crear nuevo colaborador
    path('nuevo/', views.ColaboradorCreateView.as_view(), name='colaborador_create'),
    # Editar colaborador existente
    path('<int:pk>/editar/', views.ColaboradorUpdateView.as_view(), name='colaborador_update'),
    # Eliminar colaborador
    path('<int:pk>/eliminar/', views.ColaboradorDeleteView.as_view(), name='colaborador_delete'),
]
