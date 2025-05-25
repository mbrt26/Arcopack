# inventario/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.conf import settings # Necesario para AUTH_USER_MODEL en FKs

# --- Importar modelos de ESTA app ---
from .models import (
    MateriaPrima, Tinta, LoteMateriaPrima, LoteProductoEnProceso,
    LoteProductoTerminado, MovimientoInventario
)
# --- Importar modelos de OTRAS apps (necesarios para filtros, links, etc.) ---
# Asegúrate que estas apps y modelos existen y están correctamente definidos
from configuracion.models import Ubicacion, UnidadMedida, Proveedor, CategoriaMateriaPrima, TipoTinta
from productos.models import ProductoTerminado
from produccion.models import OrdenProduccion # <<< ¡Importación Corregida!

# =============================================
# === ADMIN PARA ITEMS DE INVENTARIO ===
# =============================================

@admin.register(MateriaPrima)
class MateriaPrimaAdmin(admin.ModelAdmin):
    """Admin para Materia Prima."""
    list_display = ('codigo', 'nombre', 'categoria', 'unidad_medida', 'requiere_lote', 'is_active')
    list_filter = ('categoria', 'is_active', 'requiere_lote')
    search_fields = ('codigo', 'nombre', 'descripcion')
    list_select_related = ('categoria', 'unidad_medida') # Optimiza consultas
    fieldsets = (
        (None, {'fields': ('codigo', 'nombre', 'categoria', 'is_active')}),
        ('Detalles', {'fields': ('descripcion', 'unidad_medida', 'requiere_lote')}),
        ('Abastecimiento', {'fields': ('proveedor_preferido', 'stock_minimo', 'stock_maximo', 'tiempo_entrega_std_dias')}),
    )

    def save_model(self, request, obj, form, change): # Asigna usuario auditoría
        if not obj.pk: obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Tinta)
class TintaAdmin(admin.ModelAdmin):
    """Admin para Tintas."""
    list_display = ('codigo', 'nombre', 'tipo_tinta', 'color_exacto', 'unidad_medida', 'requiere_lote', 'is_active')
    list_filter = ('tipo_tinta', 'is_active', 'requiere_lote')
    search_fields = ('codigo', 'nombre', 'color_exacto', 'fabricante', 'referencia_fabricante')
    list_select_related = ('tipo_tinta', 'unidad_medida')
    fieldsets = (
        (None, {'fields': ('codigo', 'nombre', 'tipo_tinta', 'is_active')}),
        ('Detalles', {'fields': ('color_exacto', 'fabricante', 'referencia_fabricante', 'unidad_medida', 'requiere_lote')}),
    )

    def save_model(self, request, obj, form, change): # Asigna usuario auditoría
        if not obj.pk: obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)

# =============================================
# === ADMIN PARA LOTES DE INVENTARIO ===
# =============================================

@admin.register(LoteMateriaPrima)
class LoteMateriaPrimaAdmin(admin.ModelAdmin):
    """Admin para Lotes de Materia Prima."""
    list_display = ('lote_id', 'materia_prima_link', 'cantidad_actual', 'unidad_medida_lote', 'ubicacion', 'estado', 'fecha_recepcion', 'proveedor_link')
    list_filter = ('estado', 'ubicacion', 'materia_prima', 'proveedor', 'fecha_recepcion', 'fecha_vencimiento')
    search_fields = ('lote_id', 'materia_prima__codigo', 'materia_prima__nombre', 'documento_recepcion', 'proveedor__razon_social')
    list_select_related = ('materia_prima', 'ubicacion', 'proveedor', 'materia_prima__unidad_medida')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por')
    date_hierarchy = 'fecha_recepcion'
    fieldsets = (
        (None, {'fields': ('lote_id', 'materia_prima', 'proveedor', 'documento_recepcion')}),
        ('Stock y Ubicación', {'fields': ('cantidad_actual', 'cantidad_recibida', 'ubicacion', 'estado')}),
        ('Fechas', {'fields': ('fecha_recepcion', 'fecha_vencimiento')}),
        ('Costos y Observaciones', {'fields': ('costo_unitario', 'observaciones')}),
        ('Auditoría', {'fields': ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Unidad')
    def unidad_medida_lote(self, obj):
        try: return obj.unidad_medida_lote.codigo if obj.unidad_medida_lote else '-'
        except AttributeError: return '-'

    @admin.display(description='Materia Prima')
    def materia_prima_link(self, obj):
        if obj.materia_prima:
            link = reverse("admin:inventario_materiaprima_change", args=[obj.materia_prima.id])
            return format_html('<a href="{}">{}</a>', link, obj.materia_prima)
        return "-"

    @admin.display(description='Proveedor')
    def proveedor_link(self, obj):
        if obj.proveedor:
            link = reverse("admin:configuracion_proveedor_change", args=[obj.proveedor.id]) # Asume que Proveedor está en configuracion app
            return format_html('<a href="{}">{}</a>', link, obj.proveedor)
        return "-"

    def save_model(self, request, obj, form, change): # Asigna usuario auditoría
        if not obj.pk: obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)

@admin.register(LoteProductoEnProceso)
class LoteProductoEnProcesoAdmin(admin.ModelAdmin):
    """Admin para Lotes de Producto en Proceso (WIP)."""
    list_display = ('lote_id', 'producto_terminado_link', 'orden_produccion_link', 'cantidad_actual', 'unidad_medida_lote', 'ubicacion', 'estado', 'fecha_produccion')
    list_filter = ('estado', 'ubicacion', 'producto_terminado', 'orden_produccion__op_numero', 'fecha_produccion')
    search_fields = ('lote_id', 'producto_terminado__codigo', 'producto_terminado__nombre', 'orden_produccion__op_numero')
    list_select_related = ('producto_terminado', 'orden_produccion', 'ubicacion', 'unidad_medida_primaria')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por', 'proceso_origen_link', 'cantidad_producida_primaria', 'unidad_medida_primaria', 'cantidad_producida_secundaria', 'unidad_medida_secundaria', 'fecha_produccion')
    date_hierarchy = 'fecha_produccion'
    fieldsets = (
        (None, {'fields': ('lote_id', 'producto_terminado', 'orden_produccion', 'proceso_origen_link')}),
        ('Stock y Ubicación', {'fields': ('cantidad_actual', ('cantidad_producida_primaria', 'unidad_medida_primaria'), ('cantidad_producida_secundaria', 'unidad_medida_secundaria'), 'ubicacion', 'estado')}),
        ('Fechas y Obs.', {'fields': ('fecha_produccion', 'observaciones')}),
        ('Auditoría', {'fields': ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Unidad')
    def unidad_medida_lote(self, obj):
        try: return obj.unidad_medida_lote.codigo if obj.unidad_medida_lote else '-'
        except AttributeError: return '-'

    @admin.display(description='Producto')
    def producto_terminado_link(self, obj):
        if obj.producto_terminado:
            link = reverse("admin:productos_productoterminado_change", args=[obj.producto_terminado.id])
            return format_html('<a href="{}">{}</a>', link, obj.producto_terminado)
        return "-"

    @admin.display(description='Orden Producción')
    def orden_produccion_link(self, obj):
        if obj.orden_produccion:
            link = reverse("admin:produccion_ordenproduccion_change", args=[obj.orden_produccion.id])
            return format_html('<a href="{}">{}</a>', link, obj.orden_produccion.op_numero)
        return "-"

    @admin.display(description='Proceso Origen')
    def proceso_origen_link(self, obj):
        if obj.proceso_origen_content_object:
            try:
                link = reverse(f"admin:{obj.proceso_origen_content_type.app_label}_{obj.proceso_origen_content_type.model}_change", args=[obj.proceso_origen_object_id])
                return format_html('<a href="{}">{}</a>', link, obj.proceso_origen_content_object)
            except Exception: return f"{obj.proceso_origen_content_type.model}: {obj.proceso_origen_object_id}"
        return "-"

    def save_model(self, request, obj, form, change): # Asigna usuario auditoría
        if not obj.pk: obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)

@admin.register(LoteProductoTerminado)
class LoteProductoTerminadoAdmin(admin.ModelAdmin):
    """Admin para Lotes de Producto Terminado (PT)."""
    list_display = ('lote_id', 'producto_terminado_link', 'orden_produccion_link', 'cantidad_actual', 'unidad_medida_lote', 'ubicacion', 'estado', 'fecha_produccion')
    list_filter = ('estado', 'ubicacion', 'producto_terminado', 'orden_produccion__op_numero', 'fecha_produccion', 'fecha_vencimiento')
    search_fields = ('lote_id', 'producto_terminado__codigo', 'producto_terminado__nombre', 'orden_produccion__op_numero')
    list_select_related = ('producto_terminado', 'orden_produccion', 'ubicacion', 'producto_terminado__unidad_medida')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por', 'proceso_final_link', 'cantidad_producida', 'fecha_produccion')
    date_hierarchy = 'fecha_produccion'
    fieldsets = (
        (None, {'fields': ('lote_id', 'producto_terminado', 'orden_produccion', 'proceso_final_link')}),
        ('Stock y Ubicación', {'fields': ('cantidad_actual', 'cantidad_producida', 'ubicacion', 'estado')}),
        ('Fechas y Obs.', {'fields': ('fecha_produccion', 'fecha_vencimiento', 'observaciones')}),
        ('Auditoría', {'fields': ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Unidad')
    def unidad_medida_lote(self, obj):
        try: return obj.unidad_medida_lote.codigo if obj.unidad_medida_lote else '-'
        except AttributeError: return '-'

    producto_terminado_link = LoteProductoEnProcesoAdmin.producto_terminado_link # Reutilizar
    orden_produccion_link = LoteProductoEnProcesoAdmin.orden_produccion_link # Reutilizar

    @admin.display(description='Proceso Final')
    def proceso_final_link(self, obj):
        if obj.proceso_final_content_object:
             try:
                 link = reverse(f"admin:{obj.proceso_final_content_type.app_label}_{obj.proceso_final_content_type.model}_change", args=[obj.proceso_final_object_id])
                 return format_html('<a href="{}">{}</a>', link, obj.proceso_final_content_object)
             except Exception: return f"{obj.proceso_final_content_type.model}: {obj.proceso_final_object_id}"
        return "-"

    def save_model(self, request, obj, form, change): # Asigna usuario auditoría
        if not obj.pk: obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)

# =============================================
# === ADMIN PARA MOVIMIENTOS DE INVENTARIO ===
# =============================================

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    """Admin para visualizar Movimientos de Inventario (solo lectura)."""
    list_display = ('timestamp', 'tipo_movimiento', 'lote_link', 'cantidad', 'unidad_medida', 'ubicacion_origen', 'ubicacion_destino', 'usuario_link', 'documento_referencia', 'proceso_referencia_link')
    list_filter = ('tipo_movimiento', 'timestamp', ('lote_content_type', admin.RelatedOnlyFieldListFilter), 'usuario', 'unidad_medida', 'ubicacion_origen', 'ubicacion_destino') # Filtrar por tipo de lote
    search_fields = ('lote_object_id', 'documento_referencia', 'observaciones', 'usuario__username')
    # list_select_related mejora rendimiento pero es más complejo con GenericForeignKey
    # list_select_related = ('unidad_medida', 'ubicacion_origen', 'ubicacion_destino', 'usuario')
    readonly_fields = [f.name for f in MovimientoInventario._meta.get_fields()] # Todos readonly
    date_hierarchy = 'timestamp'

    @admin.display(description='Lote Afectado')
    def lote_link(self, obj):
        if obj.lote_content_object:
            lote_ct = obj.lote_content_type
            try: link = reverse(f"admin:{lote_ct.app_label}_{lote_ct.model}_change", args=[obj.lote_object_id]); return format_html('<a href="{}">{}</a>', link, obj.lote_content_object)
            except Exception: return f"{lote_ct.model}: {obj.lote_object_id}"
        return obj.lote_object_id

    @admin.display(description='Usuario')
    def usuario_link(self, obj):
        if obj.usuario:
            try: link = reverse("admin:auth_user_change", args=[obj.usuario.id]); return format_html('<a href="{}">{}</a>', link, obj.usuario.username)
            except Exception: return obj.usuario.username
        return "-"

    @admin.display(description='Referencia Proceso')
    def proceso_referencia_link(self, obj):
        if obj.proceso_referencia_content_object:
            proceso_ct = obj.proceso_referencia_content_type
            try: link = reverse(f"admin:{proceso_ct.app_label}_{proceso_ct.model}_change", args=[obj.proceso_referencia_object_id]); return format_html('<a href="{}">{}</a>', link, obj.proceso_referencia_content_object)
            except Exception: return f"{proceso_ct.model}: {obj.proceso_referencia_object_id}"
        return "-"

    # Deshabilitar añadir/cambiar/borrar movimientos manualmente
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False