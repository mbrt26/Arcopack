# productos/admin.py
from django.contrib import admin
from .models import ProductoTerminado # Importa el modelo principal de esta app

# --- Importaciones para django-import-export ---
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, BooleanWidget

# --- Importar TODOS los modelos referenciados por ForeignKey desde configuracion ---
# Necesitamos estos para configurar los ForeignKeyWidget en el Resource
from configuracion.models import (
    CategoriaProducto, SubcategoriaProducto, EstadoProducto, UnidadMedida,
    TipoMateriaPrima, TipoMaterial, Lamina, Tratamiento, TipoTinta,
    ProgramaLamina, TipoSellado, TipoTroquel, TipoZipper, TipoValvula,
    TipoImpresion, RodilloAnilox, CuentaContable, Servicio
    # Asegúrate de que todos los modelos FK existan en configuracion.models
)

# --- Resource para Import/Export ---
# Define cómo mapear el archivo a los campos del modelo ProductoTerminado
class ProductoTerminadoResource(resources.ModelResource):

    # --- Mapeo de ForeignKeys usando Widgets ---
    # Permite importar usando el nombre o código del objeto relacionado, en lugar del ID interno.
    # Asegúrate que el segundo argumento ('nombre', 'codigo') sea un campo ÚNICO en el modelo relacionado.

    categoria = fields.Field(column_name='categoria_nombre', attribute='categoria', widget=ForeignKeyWidget(CategoriaProducto, 'nombre'))
    subcategoria = fields.Field(column_name='subcategoria_nombre', attribute='subcategoria', widget=ForeignKeyWidget(SubcategoriaProducto, 'nombre')) # Asume 'nombre' es único dentro de su categoría padre, puede necesitar lógica más compleja si no lo es.
    estado = fields.Field(column_name='estado_nombre', attribute='estado', widget=ForeignKeyWidget(EstadoProducto, 'nombre'))
    unidad_medida = fields.Field(column_name='unidad_medida_codigo', attribute='unidad_medida', widget=ForeignKeyWidget(UnidadMedida, 'codigo'))
    tipo_materia_prima = fields.Field(column_name='tipo_materia_prima_nombre', attribute='tipo_materia_prima', widget=ForeignKeyWidget(TipoMateriaPrima, 'nombre'))
    tipo_material = fields.Field(column_name='tipo_material_nombre', attribute='tipo_material', widget=ForeignKeyWidget(TipoMaterial, 'nombre'))
    cuenta_contable = fields.Field(column_name='cuenta_contable_codigo', attribute='cuenta_contable', widget=ForeignKeyWidget(CuentaContable, 'codigo'))
    servicio = fields.Field(column_name='servicio_nombre', attribute='servicio', widget=ForeignKeyWidget(Servicio, 'nombre'))
    lamina = fields.Field(column_name='lamina_nombre', attribute='lamina', widget=ForeignKeyWidget(Lamina, 'nombre'))
    tratamiento = fields.Field(column_name='tratamiento_nombre', attribute='tratamiento', widget=ForeignKeyWidget(Tratamiento, 'nombre'))
    tipo_tinta = fields.Field(column_name='tipo_tinta_nombre', attribute='tipo_tinta', widget=ForeignKeyWidget(TipoTinta, 'nombre'))
    programa_lamina = fields.Field(column_name='programa_lamina_nombre', attribute='programa_lamina', widget=ForeignKeyWidget(ProgramaLamina, 'nombre'))
    sellado_tipo = fields.Field(column_name='sellado_tipo_nombre', attribute='sellado_tipo', widget=ForeignKeyWidget(TipoSellado, 'nombre'))
    sellado_troquel_tipo = fields.Field(column_name='sellado_troquel_tipo_nombre', attribute='sellado_troquel_tipo', widget=ForeignKeyWidget(TipoTroquel, 'nombre'))
    sellado_zipper_tipo = fields.Field(column_name='sellado_zipper_tipo_nombre', attribute='sellado_zipper_tipo', widget=ForeignKeyWidget(TipoZipper, 'nombre'))
    sellado_valvula_tipo = fields.Field(column_name='sellado_valvula_tipo_nombre', attribute='sellado_valvula_tipo', widget=ForeignKeyWidget(TipoValvula, 'nombre'))
    imp_tipo_impresion = fields.Field(column_name='imp_tipo_impresion_nombre', attribute='imp_tipo_impresion', widget=ForeignKeyWidget(TipoImpresion, 'nombre'))
    imp_rodillo = fields.Field(column_name='imp_rodillo_codigo', attribute='imp_rodillo', widget=ForeignKeyWidget(RodilloAnilox, 'codigo'))

    # --- Mapeo de Booleanos (Opcional, para claridad en CSV/Excel) ---
    # Permite usar 'Sí'/'No', 'True'/'False', '1'/'0' en el archivo de importación
    # comercializable = fields.Field(column_name='comercializable', attribute='comercializable', widget=BooleanWidget())
    # extrusion_doble = fields.Field(column_name='extrusion_doble', attribute='extrusion_doble', widget=BooleanWidget())
    # sellado_ultrasonido = fields.Field(column_name='sellado_ultrasonido', attribute='sellado_ultrasonido', widget=BooleanWidget())
    # sellado_precorte = fields.Field(column_name='sellado_precorte', attribute='sellado_precorte', widget=BooleanWidget())
    # is_active = fields.Field(column_name='activo', attribute='is_active', widget=BooleanWidget()) # Mapear a columna 'activo'

    class Meta:
        model = ProductoTerminado
        skip_unchanged = True # No procesar filas si no cambian respecto a la BD
        report_skipped = True # Informar filas omitidas
        import_id_fields = ('codigo',) # Clave para identificar productos existentes y actualizarlos
        # Define los campos a incluir y su orden en import/export.
        # ¡Asegúrate de que los nombres aquí coincidan con los definidos arriba (para FKs) o en el modelo!
        fields = (
            'id', 'codigo', 'nombre', 'categoria', 'subcategoria', 'estado', 'unidad_medida',
            'comercializable', 'tipo_materia_prima', 'tipo_material', 'calibre_um', 'color',
            'medida_en', 'largo', 'ancho', 'factor_decimal', 'ancho_rollo', 'metros_lineales',
            'lamina', 'extrusion_doble', 'cantidad_xml', 'largo_material', 'tratamiento',
            'tipo_tinta', 'pistas', 'programa_lamina',
            'sellado_peso_millar', 'sellado_tipo', 'sellado_fuelle_lateral', 'sellado_fuelle_superior',
            'sellado_fuelle_fondo', 'sellado_solapa_cm', 'sellado_troquel_tipo', 'sellado_troquel_medida',
            'sellado_zipper_tipo', 'sellado_zipper_medida', 'sellado_valvula_tipo', 'sellado_valvula_medida',
            'sellado_ultrasonido', 'sellado_ultrasonido_pos', 'sellado_precorte', 'sellado_precorte_medida',
            'imp_tipo_impresion', 'imp_rodillo', 'imp_repeticiones',
            'cuenta_contable', 'servicio',
            'is_active', # Puedes mapearlo a una columna 'activo' como se vio en el widget booleano
        )
        # Excluir campos de auditoría que no se importan/exportan directamente
        exclude = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',)

# --- Admin Personalizado ---
# Hereda de ImportExportModelAdmin para añadir los botones y funcionalidad
class ProductoTerminadoAdmin(ImportExportModelAdmin):
    """Personalización del Admin para ProductoTerminado con Import/Export."""

    # Asociar el Resource definido arriba
    resource_class = ProductoTerminadoResource

    # --- Configuraciones de visualización (las que ya tenías) ---
    list_display = (
        'codigo', 'nombre', 'categoria', 'estado', 'unidad_medida', 'is_active', 'actualizado_en'
    )
    list_filter = (
        'estado', 'categoria', 'tipo_material', 'is_active', 'comercializable', 'tipo_materia_prima'
    )
    search_fields = ('codigo', 'nombre',)
    fieldsets = (
        ('Información Principal', {'fields': ('codigo', 'nombre', 'categoria', 'subcategoria', 'estado', 'unidad_medida', 'comercializable', 'is_active')}),
        ('Material Base y Dimensiones', {'fields': ('tipo_materia_prima', 'tipo_material', 'calibre_um', 'color', 'medida_en', 'largo', 'ancho', 'ancho_rollo', 'metros_lineales', 'largo_material', 'factor_decimal')}),
        ('Especificaciones Adicionales', {'fields': ('lamina', 'extrusion_doble', 'tratamiento', 'pistas', 'programa_lamina', 'cantidad_xml')}),
        ('Impresión', {'fields': ('imp_tipo_impresion', 'imp_rodillo', 'imp_repeticiones', 'tipo_tinta')}),
        ('Sellado: General y Fuelles', {'fields': ('sellado_tipo', 'sellado_peso_millar', 'sellado_fuelle_fondo', 'sellado_fuelle_lateral', 'sellado_fuelle_superior', 'sellado_solapa_cm')}),
        ('Sellado: Features Adicionales', {'fields': ('sellado_troquel_tipo', 'sellado_troquel_medida', 'sellado_zipper_tipo', 'sellado_zipper_medida', 'sellado_valvula_tipo', 'sellado_valvula_medida', 'sellado_ultrasonido', 'sellado_ultrasonido_pos', 'sellado_precorte', 'sellado_precorte_medida')}),
        ('Otros / Contabilidad', {'fields': ('cuenta_contable', 'servicio')}),
    )
    # Opcional: Hacer campos de auditoría de solo lectura en el admin
    # readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por')

# --- Registrar el modelo con la clase Admin personalizada ---
admin.site.register(ProductoTerminado, ProductoTerminadoAdmin)