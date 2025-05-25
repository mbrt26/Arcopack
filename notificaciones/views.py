from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Notificacion

class NotificacionListView(LoginRequiredMixin, ListView):
    model = Notificacion
    template_name = 'notificaciones/notificacion_list.html'
    context_object_name = 'notificaciones'
    
    def get_queryset(self):
        return Notificacion.objects.filter(
            usuario=self.request.user
        ).order_by('-fecha_creacion')