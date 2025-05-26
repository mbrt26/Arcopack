# pedidos/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from .models import Pedido, LineaPedido, SeguimientoPedido


class LineaPedidoInline(admin.TabularInline):
    """Inline para gestionar las líneas de pedido."""
    model = LineaPedido
    extra = 1
    fields = (
        'orden_linea', 'producto', 'cantidad', 'precio_unitario', 
        'descuento_porcentaje', 'subtotal_display', 'cantidad_producida', 
        'porcentaje_completado_display', 'fecha_entrega_requerida'
    )
    readonly_fields = ('subtotal_display', 'porcentaje_completado_display')
    autocomplete_fields = ['producto']
    
    @admin.display(description='Subtotal')
    def subtotal_display(self, obj):
        if obj.pk:
            return f"${obj.subtotal:,.2f}"
        return "-"
    
    @admin.display(description='% Completado')
    def porcentaje_completado_display(self, obj):
        if obj.pk:
            porcentaje = obj.porcentaje_completado
            if porcentaje >= 100:
                color = "green"
            elif porcentaje >= 50:
                color = "orange"
            else:
                color = "red"
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, porcentaje
            )
        return "-"


class SeguimientoPedidoInline(admin.TabularInline):
    """Inline para mostrar el seguimiento de cambios de estado."""
    model = SeguimientoPedido
    extra = 0
    fields = ('fecha_cambio', 'estado_anterior', 'estado_nuevo', 'usuario', 'observaciones')
    readonly_fields = ('fecha_cambio', 'usuario')
    
    def has_add_permission(self, request, obj):
        return False  # Solo lectura, los seguimientos se crean automáticamente


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """Administración de pedidos."""
    
    list_display = (
        'numero_pedido', 'cliente_link', 'estado_badge', 'fecha_pedido', 
        'fecha_compromiso', 'valor_total_display', 'tiene_op_display', 
        'porcentaje_completado_display', 'prioridad_badge'
    )
    list_filter = (
        'estado', 'prioridad', 'fecha_pedido', 'fecha_compromiso', 
        'cliente', 'creado_por'
    )
    search_fields = (
        'numero_pedido', 'cliente__razon_social', 'cliente__nit',
        'pedido_cliente_referencia', 'numero_factura'
    )
    readonly_fields = (
        'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',
        'valor_total_display', 'porcentaje_completado_display', 
        'ordenes_produccion_display'
    )
    autocomplete_fields = ['cliente']
    date_hierarchy = 'fecha_pedido'
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'numero_pedido', 'cliente', 'estado', 'prioridad'
            )
        }),
        ('Fechas', {
            'fields': (
                'fecha_pedido', 'fecha_compromiso', 'fecha_entrega_estimada',
                'fecha_entrega_real'
            )
        }),
        ('Información Comercial', {
            'fields': (
                'pedido_cliente_referencia', 'condiciones_pago', 
                'valor_total_display', 'observaciones'
            )
        }),
        ('Facturación', {
            'fields': ('numero_factura', 'fecha_facturacion'),
            'classes': ('collapse',)
        }),
        ('Producción', {
            'fields': ('ordenes_produccion_display', 'porcentaje_completado_display'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': (
                'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [LineaPedidoInline, SeguimientoPedidoInline]
    
    actions = ['marcar_confirmado', 'marcar_producido', 'marcar_pendiente_facturar']
    
    @admin.display(description='Cliente')
    def cliente_link(self, obj):
        if obj.cliente:
            url = reverse('admin:clientes_cliente_change', args=[obj.cliente.pk])
            return format_html('<a href="{}">{}</a>', url, obj.cliente.razon_social)
        return "-"
    
    @admin.display(description='Estado')
    def estado_badge(self, obj):
        colors = {
            'BORRADOR': '#6c757d',
            'CONFIRMADO': '#007bff',
            'EN_PRODUCCION': '#ffc107',
            'PRODUCIDO': '#28a745',
            'PENDIENTE_FACTURAR': '#fd7e14',
            'FACTURADO': '#20c997',
            'ENTREGADO': '#198754',
            'CANCELADO': '#dc3545',
        }
        color = colors.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_estado_display()
        )
    
    @admin.display(description='Prioridad')
    def prioridad_badge(self, obj):
        colors = {
            'BAJA': '#6c757d',
            'NORMAL': '#007bff',
            'ALTA': '#ffc107',
            'URGENTE': '#dc3545',
        }
        color = colors.get(obj.prioridad, '#007bff')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_prioridad_display()
        )
    
    @admin.display(description='Valor Total')
    def valor_total_display(self, obj):
        return f"${obj.valor_total:,.2f}"
    
    @admin.display(description='Tiene OP?', boolean=True)
    def tiene_op_display(self, obj):
        return obj.tiene_orden_produccion
    
    @admin.display(description='% Completado')
    def porcentaje_completado_display(self, obj):
        porcentaje = obj.porcentaje_completado
        if porcentaje >= 100:
            color = "green"
        elif porcentaje >= 50:
            color = "orange"
        else:
            color = "red"
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 5px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 5px; '
            'text-align: center; line-height: 20px; color: white; font-size: 11px; font-weight: bold;">'
            '{:.1f}%</div></div>',
            porcentaje, color, porcentaje
        )
    
    @admin.display(description='Órdenes de Producción')
    def ordenes_produccion_display(self, obj):
        ordenes = obj.ordenes_produccion_asociadas
        if ordenes:
            links = []
            for orden in ordenes:
                url = reverse('admin:produccion_ordenproduccion_change', args=[orden.pk])
                links.append(f'<a href="{url}">{orden.op_numero}</a>')
            return format_html(' | '.join(links))
        return "No tiene órdenes asociadas"
    
    def save_model(self, request, obj, form, change):
        """Guarda el modelo y registra cambios de estado."""
        estado_anterior = None
        if change:
            # Obtener el estado anterior
            estado_anterior = Pedido.objects.get(pk=obj.pk).estado
        
        # Asignar usuario de auditoría
        if not obj.pk:
            obj.creado_por = request.user
        obj.actualizado_por = request.user
        
        # Calcular total
        obj.calcular_total()
        
        super().save_model(request, obj, form, change)
        
        # Registrar cambio de estado si cambió
        if change and estado_anterior and estado_anterior != obj.estado:
            SeguimientoPedido.objects.create(
                pedido=obj,
                estado_anterior=estado_anterior,
                estado_nuevo=obj.estado,
                usuario=request.user,
                observaciones=f"Cambio de estado desde admin por {request.user.username}"
            )
    
    def save_formset(self, request, form, formset, change):
        """Guarda las líneas de pedido y recalcula el total."""
        super().save_formset(request, form, formset, change)
        if formset.model == LineaPedido:
            # Recalcular el total del pedido
            form.instance.calcular_total()
            form.instance.save(update_fields=['valor_total'])
    
    @admin.action(description='Marcar como confirmado')
    def marcar_confirmado(self, request, queryset):
        """Acción para marcar pedidos como confirmados."""
        count = 0
        for pedido in queryset.filter(estado='BORRADOR'):
            pedido.estado = 'CONFIRMADO'
            pedido.save()
            SeguimientoPedido.objects.create(
                pedido=pedido,
                estado_anterior='BORRADOR',
                estado_nuevo='CONFIRMADO',
                usuario=request.user,
                observaciones="Confirmado mediante acción masiva"
            )
            count += 1
        
        self.message_user(
            request,
            f"{count} pedido(s) marcado(s) como confirmado(s).",
            messages.SUCCESS
        )
    
    @admin.action(description='Marcar como producido')
    def marcar_producido(self, request, queryset):
        """Acción para marcar pedidos como producidos."""
        count = 0
        for pedido in queryset.filter(estado='EN_PRODUCCION'):
            pedido.estado = 'PRODUCIDO'
            pedido.save()
            SeguimientoPedido.objects.create(
                pedido=pedido,
                estado_anterior='EN_PRODUCCION',
                estado_nuevo='PRODUCIDO',
                usuario=request.user,
                observaciones="Marcado como producido mediante acción masiva"
            )
            count += 1
        
        self.message_user(
            request,
            f"{count} pedido(s) marcado(s) como producido(s).",
            messages.SUCCESS
        )
    
    @admin.action(description='Marcar como pendiente de facturar')
    def marcar_pendiente_facturar(self, request, queryset):
        """Acción para marcar pedidos como pendientes de facturar."""
        count = 0
        for pedido in queryset.filter(estado='PRODUCIDO'):
            pedido.estado = 'PENDIENTE_FACTURAR'
            pedido.save()
            SeguimientoPedido.objects.create(
                pedido=pedido,
                estado_anterior='PRODUCIDO',
                estado_nuevo='PENDIENTE_FACTURAR',
                usuario=request.user,
                observaciones="Marcado como pendiente de facturar mediante acción masiva"
            )
            count += 1
        
        self.message_user(
            request,
            f"{count} pedido(s) marcado(s) como pendiente(s) de facturar.",
            messages.SUCCESS
        )


@admin.register(LineaPedido)
class LineaPedidoAdmin(admin.ModelAdmin):
    """Administración de líneas de pedido."""
    
    list_display = (
        'pedido_link', 'producto_link', 'cantidad', 'precio_unitario',
        'subtotal_display', 'cantidad_producida', 'porcentaje_completado_display'
    )
    list_filter = ('pedido__estado', 'producto__tipo_materia_prima', 'fecha_entrega_requerida')
    search_fields = (
        'pedido__numero_pedido', 'producto__codigo', 'producto__nombre',
        'especificaciones_tecnicas'
    )
    autocomplete_fields = ['pedido', 'producto']
    
    @admin.display(description='Pedido')
    def pedido_link(self, obj):
        url = reverse('admin:pedidos_pedido_change', args=[obj.pedido.pk])
        return format_html('<a href="{}">{}</a>', url, obj.pedido.numero_pedido)
    
    @admin.display(description='Producto')
    def producto_link(self, obj):
        url = reverse('admin:productos_productoterminado_change', args=[obj.producto.pk])
        return format_html('<a href="{}">{}</a>', url, obj.producto.codigo)
    
    @admin.display(description='Subtotal')
    def subtotal_display(self, obj):
        return f"${obj.subtotal:,.2f}"
    
    @admin.display(description='% Completado')
    def porcentaje_completado_display(self, obj):
        porcentaje = obj.porcentaje_completado
        if porcentaje >= 100:
            color = "green"
        elif porcentaje >= 50:
            color = "orange"
        else:
            color = "red"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, porcentaje
        )


@admin.register(SeguimientoPedido)
class SeguimientoPedidoAdmin(admin.ModelAdmin):
    """Administración de seguimientos de pedido (solo lectura)."""
    
    list_display = (
        'pedido_link', 'fecha_cambio', 'estado_anterior', 'estado_nuevo',
        'usuario_link'
    )
    list_filter = ('estado_anterior', 'estado_nuevo', 'fecha_cambio', 'usuario')
    search_fields = ('pedido__numero_pedido', 'observaciones')
    readonly_fields = ('pedido', 'estado_anterior', 'estado_nuevo', 'fecha_cambio', 'usuario')
    
    def has_add_permission(self, request):
        return False  # Solo lectura
    
    def has_change_permission(self, request, obj=None):
        return False  # Solo lectura
    
    def has_delete_permission(self, request, obj=None):
        return False  # Solo lectura
    
    @admin.display(description='Pedido')
    def pedido_link(self, obj):
        url = reverse('admin:pedidos_pedido_change', args=[obj.pedido.pk])
        return format_html('<a href="{}">{}</a>', url, obj.pedido.numero_pedido)
    
    @admin.display(description='Usuario')
    def usuario_link(self, obj):
        if obj.usuario:
            return obj.usuario.username
        return "-"