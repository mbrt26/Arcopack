# personal/admin.py
from django.contrib import admin
from .models import Colaborador # Importar el modelo de esta app

@admin.register(Colaborador) # Registrar usando decorador
class ColaboradorAdmin(admin.ModelAdmin):
    """Personalización del Admin para Colaborador."""
    list_display = ('nombre_completo', 'codigo_empleado', 'cargo', 'is_active') # Columnas útiles en la lista
    search_fields = ('nombres', 'apellidos', 'cedula', 'codigo_empleado') # Campos para buscar
    list_filter = ('is_active', 'area', 'cargo') # Filtros útiles
    # Organizar el formulario de edición/creación
    fieldsets = (
        ('Información Personal', {'fields': ('nombres', 'apellidos', 'cedula')}),
        ('Información Laboral', {'fields': ('codigo_empleado', 'cargo', 'area', 'fecha_ingreso', 'fecha_retiro', 'is_active')}),
        ('Acceso al Sistema', {'fields': ('usuario_sistema',)}), # Campo para vincular a User Django
    )
    # readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por') # Opcional

# No necesitas admin.site.register(Colaborador) si usas el decorador @admin.register