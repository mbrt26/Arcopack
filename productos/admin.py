# productos/admin.py
from django.contrib import admin
from .models import ProductoTerminado

# --- Importaciones para django-import-export ---
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, BooleanWidget

# --- Importar TODOS los modelos referenciados por ForeignKey desde configuracion ---
from configuracion.models import (
    CategoriaProducto, SubLinea, EstadoProducto, UnidadMedida,
    TipoMateriaPrima, TipoMaterial, Tratamiento, TipoTinta,
    TipoSellado, TipoTroquel, TipoZipper, TipoValvula,
    TipoImpresion, CuentaContable, Servicio
)

# Importar modelo Cliente
from clientes.models import Cliente
from inventario.models import LoteProductoTerminado

# --- Resource para Import/Export ---
class ProductoTerminadoResource(resources.ModelResource):

    # --- Mapeo de ForeignKeys usando Widgets ---
    linea = fields.Field(column_name='linea_nombre', attribute='linea', widget=ForeignKeyWidget(CategoriaProducto, 'nombre'))
    sublinea = fields.Field(column_name='sublinea_nombre', attribute='sublinea', widget=ForeignKeyWidget(SubLinea, 'nombre'))
    estado = fields.Field(column_name='estado_nombre', attribute='estado', widget=ForeignKeyWidget(EstadoProducto, 'nombre'))
    unidad_medida = fields.Field(column_name='unidad_medida_codigo', attribute='unidad_medida', widget=ForeignKeyWidget(UnidadMedida, 'codigo'))
    tipo_materia_prima = fields.Field(column_name='tipo_materia_prima_nombre', attribute='tipo_materia_prima', widget=ForeignKeyWidget(TipoMateriaPrima, 'nombre'))
    tipo_material = fields.Field(column_name='tipo_material_nombre', attribute='tipo_material', widget=ForeignKeyWidget(TipoMaterial, 'nombre'))
    cuenta_contable = fields.Field(column_name='cuenta_contable_codigo', attribute='cuenta_contable', widget=ForeignKeyWidget(CuentaContable, 'codigo'))
    servicio = fields.Field(column_name='servicio_nombre', attribute='servicio', widget=ForeignKeyWidget(Servicio, 'nombre'))
    tratamiento = fields.Field(column_name='tratamiento_nombre', attribute='tratamiento', widget=ForeignKeyWidget(Tratamiento, 'nombre'))
    tipo_tinta = fields.Field(column_name='tipo_tinta_nombre', attribute='tipo_tinta', widget=ForeignKeyWidget(TipoTinta, 'nombre'))
    sellado_tipo = fields.Field(column_name='sellado_tipo_nombre', attribute='sellado_tipo', widget=ForeignKeyWidget(TipoSellado, 'nombre'))
    sellado_troquel_tipo = fields.Field(column_name='sellado_troquel_tipo_nombre', attribute='sellado_troquel_tipo', widget=ForeignKeyWidget(TipoTroquel, 'nombre'))
    sellado_zipper_tipo = fields.Field(column_name='sellado_zipper_tipo_nombre', attribute='sellado_zipper_tipo', widget=ForeignKeyWidget(TipoZipper, 'nombre'))
    sellado_valvula_tipo = fields.Field(column_name='sellado_valvula_tipo_nombre', attribute='sellado_valvula_tipo', widget=ForeignKeyWidget(TipoValvula, 'nombre'))
    imp_tipo_impresion = fields.Field(column_name='imp_tipo_impresion_nombre', attribute='imp_tipo_impresion', widget=ForeignKeyWidget(TipoImpresion, 'nombre'))
    cliente = fields.Field(column_name='cliente_nit', attribute='cliente', widget=ForeignKeyWidget(Cliente, 'nit'))

    class Meta:
        model = ProductoTerminado
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('codigo',)
        fields = (
            'id', 'codigo', 'nombre', 'cliente', 'linea', 'sublinea', 'estado', 'unidad_medida',
            'tipo_materia_prima', 'tipo_material', 'calibre_um', 'color',
            'medida_en', 'largo', 'ancho', 'factor_decimal', 'ancho_rollo', 'metros_lineales',
            'cantidad_xml', 'largo_material', 'tratamiento',
            'tipo_tinta', 'pistas', 'dob_medida_cm',
            'sellado_peso_millar', 'sellado_tipo', 'sellado_fuelle_lateral', 'sellado_fuelle_superior',
            'sellado_fuelle_fondo', 'sellado_solapa_cm', 'sellado_troquel_tipo', 'sellado_troquel_medida',
            'sellado_zipper_tipo', 'sellado_zipper_medida', 'sellado_valvula_tipo', 'sellado_valvula_medida',
            'sellado_ultrasonido', 'sellado_ultrasonido_pos', 'sellado_precorte', 'sellado_precorte_medida',
            'imp_tipo_impresion', 'imp_repeticiones',
            'cuenta_contable', 'servicio', 'archivo_adjunto',
            'is_active',
        )
        exclude = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',)

class LoteProductoTerminadoInline(admin.TabularInline):
    model = LoteProductoTerminado
    fk_name = 'producto_terminado'
    fields = ('lote_id', 'cantidad_producida', 'cantidad_actual', 'fecha_produccion', 'estado')
    readonly_fields = ('cantidad_actual',)
    extra = 1

# --- Admin Personalizado ---
class ProductoTerminadoAdmin(ImportExportModelAdmin):
    """Personalización del Admin para ProductoTerminado con Import/Export."""

    resource_class = ProductoTerminadoResource

    # --- Configuraciones de visualización actualizadas ---
    list_display = (
        'codigo', 'nombre', 'cliente', 'linea', 'estado', 'unidad_medida', 'is_active', 'actualizado_en'
    )
    list_filter = (
        'estado', 'linea', 'sublinea', 'tipo_material', 'is_active', 'tipo_materia_prima', 'cliente'
    )
    search_fields = ('codigo', 'nombre', 'cliente__razon_social', 'cliente__nit')
    fieldsets = (
        ('Información Principal', {
            'fields': ('codigo', 'nombre', 'cliente', 'linea', 'sublinea', 'estado', 'unidad_medida', 'is_active', 'archivo_adjunto')
        }),
        ('Material Base y Dimensiones', {
            'fields': ('tipo_materia_prima', 'tipo_material', 'calibre_um', 'color', 'medida_en', 'largo', 'ancho', 'ancho_rollo', 'metros_lineales', 'largo_material', 'factor_decimal')
        }),
        ('Especificaciones Adicionales', {
            'fields': ('tratamiento', 'cantidad_xml')
        }),
        ('Doblado', {
            'fields': ('dob_medida_cm',)
        }),
        ('Impresión', {
            'fields': ('imp_tipo_impresion', 'imp_repeticiones', 'tipo_tinta', 'pistas')
        }),
        ('Sellado: General y Fuelles', {
            'fields': ('sellado_tipo', 'sellado_peso_millar', 'sellado_fuelle_fondo', 'sellado_fuelle_lateral', 'sellado_fuelle_superior', 'sellado_solapa_cm')
        }),
        ('Sellado: Features Adicionales', {
            'fields': ('sellado_troquel_tipo', 'sellado_troquel_medida', 'sellado_zipper_tipo', 'sellado_zipper_medida', 'sellado_valvula_tipo', 'sellado_valvula_medida', 'sellado_ultrasonido', 'sellado_ultrasonido_pos', 'sellado_precorte', 'sellado_precorte_medida')
        }),
        ('Otros / Contabilidad', {
            'fields': ('cuenta_contable', 'servicio')
        }),
    )
    inlines = [
        LoteProductoTerminadoInline,
    ]

# --- Registrar el modelo con la clase Admin personalizada ---
admin.site.register(ProductoTerminado, ProductoTerminadoAdmin)