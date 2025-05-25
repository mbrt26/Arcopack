from django.contrib import admin
from .models import Notificacion

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mensaje', 'leida', 'fecha_creacion')
    list_filter = ('leida', 'fecha_creacion')
    search_fields = ('mensaje', 'usuario__username')
    ordering = ('-fecha_creacion',)