# notificaciones/urls.py

from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('', views.NotificacionListView.as_view(), name='list'),
]