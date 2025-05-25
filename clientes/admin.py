# clientes/admin.py
from django.contrib import admin
from .models import Cliente

# 1. Define la clase Admin personalizada
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('codigo_cliente', 'razon_social', 'nit', 'is_active') # Ejemplo de list_display, ajusta como necesites
    search_fields = ['razon_social', 'nit', 'codigo_cliente'] # <-- ¡AÑADE ESTO! Especifica en qué campos buscar
    list_filter = ('is_active', 'ciudad') # Ejemplo de filtros, ajusta
    # Puedes añadir otras configuraciones aquí (fieldsets, readonly_fields, etc.) si quieres personalizar más

# 2. Registra el modelo USANDO la clase Admin personalizada
admin.site.register(Cliente, ClienteAdmin)