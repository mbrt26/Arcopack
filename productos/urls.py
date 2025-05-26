from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProductoTerminadoViewSet,
    ProductoListView, ProductoDetailView,
    ProductoCreateView, ProductoUpdateView,
    ProductoDuplicateView,
)

router = DefaultRouter()
router.register(r'productos', ProductoTerminadoViewSet, basename='producto')

api_urlpatterns = [
    path('', include(router.urls)),
]

app_name = 'productos_web'

urlpatterns = [
    path('', ProductoListView.as_view(), name='producto-list'),
    path('nuevo/', ProductoCreateView.as_view(), name='producto-create'),
    path('<int:pk>/', ProductoDetailView.as_view(), name='producto-detail'),
    path('<int:pk>/editar/', ProductoUpdateView.as_view(), name='producto-update'),
    path('<int:pk>/duplicar/', ProductoDuplicateView.as_view(), name='producto-duplicate'),
]
