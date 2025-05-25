from .models import Notificacion

def notifications(request):
    """Context processor that adds notifications to the template context."""
    if request.user.is_authenticated:
        # Primero filtramos las notificaciones no leídas para el contador
        notificaciones_no_leidas = Notificacion.objects.filter(
            usuario=request.user,
            leida=False
        ).count()
        
        # Luego obtenemos las últimas 5 notificaciones
        notificaciones = Notificacion.objects.filter(
            usuario=request.user
        ).order_by('-fecha_creacion')[:5]
        
        return {
            'notificaciones': notificaciones,
            'notificaciones_no_leidas': notificaciones_no_leidas
        }
    return {
        'notificaciones': [],
        'notificaciones_no_leidas': 0
    }