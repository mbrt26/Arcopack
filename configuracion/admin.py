# configuracion/admin.py

from django.contrib import admin
# Importar todos los modelos definidos en configuracion/models.py
from .models import (
    UnidadMedida, EstadoProducto, CategoriaProducto, SubcategoriaProducto, SubLinea,
    TipoMateriaPrima, CategoriaMateriaPrima, TipoMaterial, Maquina, RodilloAnilox,
    CausaParo, TipoDesperdicio, Proveedor, Proceso, Ubicacion, Lamina,
    Tratamiento, TipoTinta, ProgramaLamina, TipoSellado, TipoTroquel,
    TipoZipper, TipoValvula, TipoImpresion, CuentaContable, Servicio
)

# Usaremos el decorador @admin.register para cada modelo con su configuración personalizada

@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('codigo', 'nombre') # Necesario para autocomplete_fields

@admin.register(EstadoProducto)
class EstadoProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(SubcategoriaProducto)
class SubcategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'descripcion')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'categoria__nombre')
    list_select_related = ('categoria',)

@admin.register(TipoMateriaPrima)
class TipoMateriaPrimaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(CategoriaMateriaPrima)
class CategoriaMateriaPrimaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(TipoMaterial)
class TipoMaterialAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_base', 'descripcion')
    list_filter = ('tipo_base',)
    search_fields = ('nombre', 'tipo_base__nombre')
    list_select_related = ('tipo_base',)

@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'marca', 'modelo', 'is_active')
    list_filter = ('tipo', 'is_active', 'marca')
    search_fields = ('codigo', 'nombre', 'marca', 'modelo', 'ubicacion_planta')

@admin.register(RodilloAnilox)
class RodilloAniloxAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'lineatura', 'volumen', 'estado', 'is_active')
    list_filter = ('estado', 'is_active')
    search_fields = ('codigo', 'descripcion', 'lineatura', 'volumen')

@admin.register(CausaParo)
class CausaParoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'tipo', 'requiere_observacion')
    list_filter = ('tipo', 'requiere_observacion')
    search_fields = ('codigo', 'descripcion')

@admin.register(TipoDesperdicio)
class TipoDesperdicioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'es_recuperable', 'is_active')
    list_filter = ('es_recuperable', 'is_active')
    search_fields = ('codigo', 'descripcion')

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nit', 'razon_social', 'nombre_comercial', 'ciudad', 'telefono', 'is_active')
    list_filter = ('is_active', 'ciudad')
    search_fields = ('nit', 'razon_social', 'nombre_comercial', 'ciudad')
    readonly_fields = ('creado_en', 'actualizado_en')

@admin.register(Proceso)
class ProcesoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden_flujo', 'descripcion')
    search_fields = ('nombre', 'descripcion')
    ordering = ('orden_flujo', 'nombre')

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'is_active')
    list_filter = ('tipo', 'is_active')
    search_fields = ('codigo', 'nombre', 'descripcion') # Necesario para autocomplete_fields
    readonly_fields = ('creado_en', 'actualizado_en')

@admin.register(Lamina)
class LaminaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Tratamiento)
class TratamientoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(TipoTinta)
class TipoTintaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(ProgramaLamina)
class ProgramaLaminaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(TipoSellado)
class TipoSelladoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(TipoTroquel)
class TipoTroquelAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(TipoZipper)
class TipoZipperAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(TipoValvula)
class TipoValvulaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(TipoImpresion)
class TipoImpresionAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'naturaleza')
    list_filter = ('naturaleza',)
    search_fields = ('codigo', 'nombre')

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(SubLinea)
class SubLineaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)
    ordering = ('nombre',)

# Nota: No se necesita admin.site.register() adicional si se usa el decorador @admin.register