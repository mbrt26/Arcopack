# produccion/admin.py
import logging
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline # Para inlines genéricos
from django.utils.html import format_html
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model # Necesario para type hints en save_formset helper

# --- Importar Modelos ---
# Modelos de esta app
from .models import (
    OrdenProduccion,
    RegistroImpresion, Refilado, Sellado, Doblado,
    ParoImpresion, DesperdicioImpresion, ConsumoTintaImpresion, ConsumoSustratoImpresion,
    ParoRefilado, DesperdicioRefilado, ConsumoWipRefilado, ConsumoMpRefilado,
    ParoSellado, DesperdicioSellado, ConsumoWipSellado, ConsumoMpSellado,
    ParoDoblado, DesperdicioDoblado, ConsumoWipDoblado, ConsumoMpDoblado
)
# Modelos de otras apps necesarios
from inventario.models import LoteProductoEnProceso, LoteProductoTerminado
from configuracion.models import Ubicacion, UnidadMedida # Para autocomplete/choices en inlines

User = get_user_model()
logger = logging.getLogger(__name__)

# =============================================
# === ADMIN PARA ORDEN DE PRODUCCIÓN ===
# =============================================
@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(admin.ModelAdmin):
    """Personalización del Admin para Orden de Producción."""
    list_display = ('op_numero', 'cliente', 'producto', 'cantidad_solicitada_kg', 'etapa_actual', 'fecha_compromiso_entrega', 'fecha_creacion', 'is_active')
    list_filter = ('etapa_actual', 'is_active', 'cliente__razon_social', 'producto__codigo', 'fecha_compromiso_entrega', 'fecha_creacion') # Usar campos relacionados para filtrar
    search_fields = ('op_numero', 'cliente__razon_social', 'producto__codigo', 'producto__nombre', 'pedido_cliente', 'id_pedido_contable')
    readonly_fields = ('fecha_creacion', 'actualizado_en', 'creado_por', 'actualizado_por', 'cantidad_producida_kg', 'fecha_real_inicio', 'fecha_real_terminacion', 'fecha_real_entrega')
    fieldsets = (
        ('Identificación y Cliente/Producto', {'fields': ('op_numero', 'cliente', 'producto', 'pedido_cliente', 'id_pedido_contable')}),
        ('Cantidades y Fechas Clave', {'fields': ('cantidad_solicitada_kg', 'cantidad_producida_kg', 'fecha_creacion', 'fecha_compromiso_entrega', 'fecha_estimada_inicio', 'fecha_real_inicio', 'fecha_real_terminacion', 'fecha_real_entrega')}),
        ('Especificaciones del Sustrato', {'fields': ('sustrato', 'ancho_sustrato_mm', 'calibre_sustrato_um', 'tratamiento_sustrato', 'color_sustrato')}),
        ('Flujo de Trabajo y Estado', {'fields': ('procesos', 'etapa_actual', 'is_active', 'codigo_barras_op')}),
        ('Observaciones', {'fields': ('observaciones_generales', 'observaciones_produccion'), 'classes': ('collapse',)}),
        ('Auditoría', {'fields': ('creado_por', 'actualizado_por', 'actualizado_en'), 'classes': ('collapse',)}), # Mostrar auditoría
    )
    filter_horizontal = ('procesos',)
    list_select_related = ('cliente', 'producto') # Optimizar lista

    def save_model(self, request, obj, form, change):
        is_new = not obj.pk
        if is_new: obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)

# =============================================
# === FUNCION HELPER PARA SAVE_FORMSET ===
# =============================================
def save_formset_with_user(self, request, form, formset, change):
    """Asigna usuario a los inlines editables y llama a su save."""
    instances = formset.save(commit=False)
    for instance in instances:
        # Verificar si el formset permite edición (no es read-only)
        can_edit = True
        # Comprobamos si el propio inline está marcado como no editable
        if hasattr(formset.form.Meta.model, '_meta') and hasattr(formset.form.Meta.model._meta, 'default_permissions'):
             if not request.user.has_perm(f"{instance._meta.app_label}.change_{instance._meta.model_name}"):
                 can_edit = False

        if can_edit:
            user_field_name = None
            is_new_inline = instance.pk is None
            if hasattr(instance, 'creado_por') and is_new_inline: user_field_name = 'creado_por'
            elif hasattr(instance, 'registrado_por') and is_new_inline: user_field_name = 'registrado_por'
            if user_field_name: setattr(instance, user_field_name, request.user)
            if hasattr(instance, 'actualizado_por'): instance.actualizado_por = request.user

            try:
                # Guardar instancia del inline, pasando user por si save() lo necesita
                instance.save(user=request.user)
            except Exception as e:
                 # Loggear o manejar el error si el save del inline falla
                 logger.error(f"Error al guardar inline {instance}: {e}")
                 # Podrías añadir un mensaje de error al admin aquí si lo deseas
                 # messages.error(request, f"Error guardando {instance}: {e}")

        # Si no es editable pero es nuevo (caso raro), guardarlo sin usuario
        elif instance.pk is None:
             instance.save()

    # Guardar relaciones ManyToMany si las hubiera en los inlines
    # (puede necesitar commit=True arriba si hay dependencias)
    formset.save_m2m()

# =============================================
# === INLINES GENÉRICOS PARA PRODUCCIÓN (LOTES) ===
# =============================================
class LoteWipProducidoInline(GenericTabularInline):
    """Inline EDITABLE para AÑADIR/VER Lotes WIP creados por un proceso."""
    model = LoteProductoEnProceso
    ct_field = "proceso_origen_content_type"
    ct_fk_field = "proceso_origen_object_id"
    # Campos EDITABLES - Asegúrate que todos los campos necesarios para crear un LoteWIP
    # (aparte de los GFK y auditoría) estén aquí y no sean readonly.
    fields = ('lote_id', 'cantidad_actual', 'unidad_medida_primaria', 'cantidad_producida_secundaria', 'unidad_medida_secundaria', 'ubicacion', 'observaciones', 'estado')
    readonly_fields = ('fecha_produccion',) # Fecha se asigna sola
    extra = 1 # Mostrar 1 formulario vacío para añadir
    verbose_name = "Lote WIP Producido"
    verbose_name_plural = "Lotes WIP Producidos (Salida de este Proceso)"
    # Asegúrate que los modelos relacionados estén registrados en sus admins con search_fields
    autocomplete_fields = ['ubicacion', 'unidad_medida_primaria', 'unidad_medida_secundaria']
    classes = ['collapse'] # Opcional: colapsar por defecto

class LotePtProducidoInline(GenericTabularInline):
    """Inline EDITABLE para AÑADIR/VER Lotes PT creados por un proceso."""
    model = LoteProductoTerminado
    ct_field = "proceso_final_content_type"
    ct_fk_field = "proceso_final_object_id"
    fields = ('lote_id', 'cantidad_actual', 'ubicacion', 'fecha_vencimiento', 'observaciones', 'estado') # Unidad viene del producto
    readonly_fields = ('fecha_produccion', 'unidad_medida_lote_display')
    extra = 1
    verbose_name = "Lote PT Producido"
    verbose_name_plural = "Lotes PT Producidos (Salida de este Proceso)"
    autocomplete_fields = ['ubicacion']
    classes = ['collapse']

    @admin.display(description='Unidad Stock')
    def unidad_medida_lote_display(self, obj):
        try: return obj.unidad_medida_lote.codigo if obj.unidad_medida_lote else '-'
        except AttributeError: return '-'

# =============================================
# === INLINES COMUNES (Paros, Desperdicios, Consumos) ===
# =============================================
# Definiendo clases base para reutilizar configuración
class BaseParoInline(admin.TabularInline):
    fields = ('causa_paro', 'hora_inicio_paro', 'hora_final_paro', 'observaciones', 'is_active')
    extra = 1; readonly_fields = ('creado_en', 'actualizado_en'); classes = ['collapse']
    autocomplete_fields = ['causa_paro'] # Asume CausaParo tiene search_fields

class BaseDesperdicioInline(admin.TabularInline):
    fields = ('tipo_desperdicio', 'cantidad_kg', 'observaciones', 'is_active') # Añadir metros si aplica a todos
    extra = 1; readonly_fields = ('creado_en', 'actualizado_en'); classes = ['collapse']
    autocomplete_fields = ['tipo_desperdicio'] # Asume TipoDesperdicio tiene search_fields

class BaseConsumoWipInline(admin.TabularInline):
    fields = ('lote_consumido', 'cantidad_kg_consumida')
    extra = 1; autocomplete_fields = ['lote_consumido']; readonly_fields = ('registrado_en',); classes = ['collapse']

class BaseConsumoMpInline(admin.TabularInline):
    fields = ('lote_consumido', 'cantidad_consumida') # Unidad viene del lote MP
    extra = 1; autocomplete_fields = ['lote_consumido']; readonly_fields = ('registrado_en',); classes = ['collapse']

# --- Inlines específicos heredando de los base ---
class ParoImpresionInline(BaseParoInline): model = ParoImpresion
class DesperdicioImpresionInline(BaseDesperdicioInline): model = DesperdicioImpresion; fields = ('tipo_desperdicio', 'cantidad_kg', 'cantidad_metros', 'observaciones', 'is_active') # Con metros
class ConsumoTintaImpresionInline(admin.TabularInline): model = ConsumoTintaImpresion; fields = ('tinta', 'cantidad_kg', 'lote_tinta', 'is_active'); extra = 1; readonly_fields = ('creado_en', 'actualizado_en'); autocomplete_fields = ['tinta']; classes = ['collapse']
class ConsumoSustratoImpresionInline(BaseConsumoMpInline): model = ConsumoSustratoImpresion; fields = ('lote_consumido', 'cantidad_kg_consumida') # Kg explícito

class ParoRefiladoInline(BaseParoInline): model = ParoRefilado
class DesperdicioRefiladoInline(BaseDesperdicioInline): model = DesperdicioRefilado
class ConsumoWipRefiladoInline(BaseConsumoWipInline): model = ConsumoWipRefilado
class ConsumoMpRefiladoInline(BaseConsumoMpInline): model = ConsumoMpRefilado

class ParoSelladoInline(BaseParoInline): model = ParoSellado
class DesperdicioSelladoInline(BaseDesperdicioInline): model = DesperdicioSellado
class ConsumoWipSelladoInline(BaseConsumoWipInline): model = ConsumoWipSellado
class ConsumoMpSelladoInline(BaseConsumoMpInline): model = ConsumoMpSellado

class ParoDobladoInline(BaseParoInline): model = ParoDoblado
class DesperdicioDobladoInline(BaseDesperdicioInline): model = DesperdicioDoblado
class ConsumoWipDobladoInline(BaseConsumoWipInline): model = ConsumoWipDoblado
class ConsumoMpDobladoInline(BaseConsumoMpInline): model = ConsumoMpDoblado

# =============================================
# === ADMIN PARA REGISTROS DE PROCESO ===
# =============================================
@admin.register(RegistroImpresion)
class RegistroImpresionAdmin(admin.ModelAdmin):
    list_display = ('id', 'orden_produccion', 'maquina', 'operario_principal', 'fecha', 'hora_inicio', 'hora_final', 'is_active')
    list_filter = ('fecha', 'maquina', 'operario_principal', 'is_active')
    search_fields = ('id', 'orden_produccion__op_numero', 'maquina__codigo', 'operario_principal__nombres', 'operario_principal__apellidos')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por') # Quitamos produccion_registrada...
    fieldsets = (
        (None, {'fields': ('orden_produccion', 'fecha', 'is_active')}),
        ('Operación', {'fields': ('maquina', 'operario_principal', 'hora_inicio', 'hora_final')}), # Quitamos kg_producidos_reportados
        ('Especificaciones Técnicas', {'fields': ('anilox', 'repeticion_mm', 'pistas', 'tipo_tinta_principal', 'aprobado_por')}),
        ('Retal (Opcional)', {'fields': ('usa_retal', 'pistas_retal')}),
        ('Otros Detalles', {'fields': ('embobinado', 'tipo_montaje')}),
    )
    inlines = [ ConsumoSustratoImpresionInline, ConsumoTintaImpresionInline, ParoImpresionInline, DesperdicioImpresionInline, LoteWipProducidoInline, LotePtProducidoInline ]
    save_model = OrdenProduccionAdmin.save_model # Reutilizar método save_model base
    save_formset = save_formset_with_user # Usar helper para guardar inlines

@admin.register(Refilado)
class RefiladoAdmin(admin.ModelAdmin):
    list_display = ('id', 'orden_produccion', 'maquina', 'operario_principal', 'fecha', 'hora_inicio', 'hora_final', 'is_active')
    list_filter = ('fecha', 'maquina', 'operario_principal', 'is_active')
    search_fields = ('id', 'orden_produccion__op_numero', 'maquina__codigo', 'operario_principal__nombres', 'operario_principal__apellidos')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por')
    fieldsets = (
         (None, {'fields': ('orden_produccion', 'fecha', 'is_active')}),
         ('Operación', {'fields': ('maquina', 'operario_principal', 'hora_inicio', 'hora_final', 'cantidad_programada_kg')}), # Quitamos kg_producidos_reportados
         ('Especificaciones Salida', {'fields': ('pistas', 'embobinado_salida', 'peso_rollo_objetivo_kg', 'embalaje')}),
    )
    inlines = [ ConsumoWipRefiladoInline, ConsumoMpRefiladoInline, ParoRefiladoInline, DesperdicioRefiladoInline, LoteWipProducidoInline, LotePtProducidoInline ]
    save_model = OrdenProduccionAdmin.save_model
    save_formset = save_formset_with_user

@admin.register(Sellado)
class SelladoAdmin(admin.ModelAdmin):
    list_display = ('id', 'orden_produccion', 'maquina', 'operario_principal', 'fecha', 'hora_inicio', 'hora_final', 'is_active')
    list_filter = ('fecha', 'maquina', 'operario_principal', 'is_active')
    search_fields = ('id', 'orden_produccion__op_numero', 'maquina__codigo', 'operario_principal__nombres', 'operario_principal__apellidos')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por')
    fieldsets = (
         (None, {'fields': ('orden_produccion', 'fecha', 'is_active')}),
         ('Operación', {'fields': ('maquina', 'operario_principal', 'hora_inicio', 'hora_final', 'cantidad_programada_unidades')}), # Quitamos unidades_producidas_reportadas
         ('Especificaciones Bolsa', {'fields': ('ancho_mm', 'largo_mm')}),
    )
    inlines = [ ConsumoWipSelladoInline, ConsumoMpSelladoInline, ParoSelladoInline, DesperdicioSelladoInline, LoteWipProducidoInline, LotePtProducidoInline ]
    save_model = OrdenProduccionAdmin.save_model
    save_formset = save_formset_with_user

@admin.register(Doblado)
class DobladoAdmin(admin.ModelAdmin):
    list_display = ('id', 'orden_produccion', 'maquina', 'operario_principal', 'fecha', 'hora_inicio', 'hora_final', 'is_active')
    list_filter = ('fecha', 'maquina', 'operario_principal', 'is_active')
    search_fields = ('id', 'orden_produccion__op_numero', 'maquina__codigo', 'operario_principal__nombres', 'operario_principal__apellidos')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por')
    fieldsets = (
         (None, {'fields': ('orden_produccion', 'fecha', 'is_active')}),
         ('Operación', {'fields': ('maquina', 'operario_principal', 'hora_inicio', 'hora_final', 'cantidad_programada_kg')}), # Quitamos kg_producidos_reportados
         ('Especificaciones', {'fields': ('medida_doblado_cm',)}),
    )
    inlines = [ ConsumoWipDobladoInline, ConsumoMpDobladoInline, ParoDobladoInline, DesperdicioDobladoInline, LoteWipProducidoInline, LotePtProducidoInline ]
    save_model = OrdenProduccionAdmin.save_model
    save_formset = save_formset_with_user

# =============================================
# === FIN ADMIN PRODUCCION ===
# =============================================