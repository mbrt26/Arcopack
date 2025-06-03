# produccion/views/kanban.py
"""
Vistas para los tableros Kanban de los diferentes procesos de producción.
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse

from ..models import OrdenProduccion

class KanbanBaseView(TemplateView):
    """Vista base para todos los tableros Kanban."""
    
    def get_orden_estado(self, orden):
        """Determina el estado de una orden de producción para el proceso específico."""
        # Implementar lógica específica según el proceso
        return 'pendiente'  # Por defecto
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener órdenes activas - FIX: usar 'etapa_actual' en lugar de 'estado'
        ordenes = OrdenProduccion.objects.filter(
            is_active=True,
            etapa_actual__in=['IMPR', 'REFI', 'SELL', 'DOBL', 'LIBR', 'PROG']  # Etapas relevantes para producción
        ).select_related(
            'cliente', 'producto'
        ).order_by('fecha_compromiso_entrega')
        
        # Organizar órdenes por estado para el tablero Kanban
        ordenes_pendientes = []
        ordenes_en_proceso = []
        ordenes_completadas = []
        
        for orden in ordenes:
            estado = self.get_orden_estado(orden)
            if estado == 'pendiente':
                ordenes_pendientes.append(orden)
            elif estado == 'en_proceso':
                ordenes_en_proceso.append(orden)
            elif estado == 'completado':
                ordenes_completadas.append(orden)
        
        context.update({
            'ordenes_pendientes': ordenes_pendientes,
            'ordenes_en_proceso': ordenes_en_proceso,
            'ordenes_completadas': ordenes_completadas,
            'proceso_nombre': getattr(self, 'proceso_nombre', 'Proceso'),
            'page_title': f'Kanban - {getattr(self, "proceso_nombre", "Proceso")}',
            'titulo': f'Kanban - {getattr(self, "proceso_nombre", "Proceso")}',
            # Agregar URLs y texto para botones de nuevo registro
            'create_url': getattr(self, 'create_url', '#'),
            'create_button_text': getattr(self, 'create_button_text', 'Nuevo Registro')
        })
        
        return context


class ImpresionKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Impresión."""
    template_name = 'produccion/kanban/impresion_kanban.html'
    proceso_nombre = 'Impresión'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Configurar URL para el botón de nuevo registro
        context['create_url'] = reverse('produccion_web:impresion-create')
        context['create_button_text'] = 'Nuevo Registro de Impresión'
        
        # Lógica específica para impresión
        from ..models import RegistroImpresion
        
        registros_activos = RegistroImpresion.objects.filter(
            is_active=True,
            hora_final__isnull=True  # Registros en proceso
        ).select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        )
        
        context['registros_activos'] = registros_activos
        return context
    
    def get_orden_estado(self, orden):
        """Determina el estado específico para el proceso de impresión."""
        if orden.etapa_actual == 'IMPR':
            return 'en_proceso'
        elif orden.etapa_actual == 'PROG':
            return 'pendiente'
        elif orden.etapa_actual in ['REFI', 'SELL', 'DOBL', 'TERM']:
            return 'completado'
        return 'pendiente'


class RefiladoKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Refilado."""
    template_name = 'produccion/kanban/refilado_kanban.html'
    proceso_nombre = 'Refilado'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Configurar URL para el botón de nuevo registro
        context['create_url'] = reverse('produccion_web:refilado-create')
        context['create_button_text'] = 'Nuevo Registro de Refilado'
        
        # Obtener todas las órdenes relevantes para refilado
        from ..models import Refilado
        
        # Obtener órdenes que están en etapas relevantes para refilado
        ordenes_query = OrdenProduccion.objects.filter(
            is_active=True,
            etapa_actual__in=['PROG', 'IMPR', 'REFI']  # Etapas relevantes para refilado
        ).select_related(
            'cliente', 'producto'  # Corregido: 'producto' en lugar de 'producto_terminado'
        ).prefetch_related(
            'registros_refilado',  # Corregido: usar 'registros_refilado' en lugar de 'refilados'
            'registros_refilado__paros_refilado'  # También corregir esta referencia
        ).order_by('fecha_compromiso_entrega')
        
        # Categorizar órdenes por estado
        ordenes_pendientes = []
        ordenes_proceso = []
        ordenes_pausadas = []
        ordenes_terminadas = []
        
        for orden in ordenes_query:
            # Obtener el registro de refilado activo más reciente
            registro_actual = orden.registros_refilado.filter(
                is_active=True
            ).order_by('-fecha', '-hora_inicio').first()
            
            # Determinar estado de la orden
            if orden.etapa_actual == 'REFI':
                if registro_actual:
                    # Verificar si hay paros activos
                    paro_actual = registro_actual.paros_refilado.filter(
                        hora_final_paro__isnull=True
                    ).first()
                    
                    if paro_actual:
                        orden.paro_actual = paro_actual
                        orden.registro_actual = registro_actual
                        ordenes_pausadas.append(orden)
                    elif registro_actual.hora_final is None:
                        # En proceso (iniciado pero no terminado)
                        orden.registro_actual = registro_actual
                        ordenes_proceso.append(orden)
                    else:
                        # Terminado
                        orden.registro_actual = registro_actual
                        ordenes_terminadas.append(orden)
                else:
                    # Orden en etapa REFI pero sin registro de refilado - va a pendientes
                    # Agregar información de lotes WIP disponibles
                    from inventario.models import LoteProductoEnProceso
                    lotes_wip = LoteProductoEnProceso.objects.filter(
                        orden_produccion=orden,
                        cantidad_actual__gt=0,
                        estado='DISPONIBLE'
                    ).order_by('creado_en')  # Corregido: usar 'creado_en' en lugar de 'fecha_creacion'
                    orden.lotes_wip_disponibles = lotes_wip
                    ordenes_pendientes.append(orden)
            elif orden.etapa_actual in ['PROG', 'IMPR']:
                # Pendiente de iniciar refilado
                # Agregar información de lotes WIP disponibles
                from inventario.models import LoteProductoEnProceso
                lotes_wip = LoteProductoEnProceso.objects.filter(
                    orden_produccion=orden,
                    cantidad_actual__gt=0,
                    estado='DISPONIBLE'
                ).order_by('creado_en')  # Corregido: usar 'creado_en' en lugar de 'fecha_creacion'
                orden.lotes_wip_disponibles = lotes_wip
                ordenes_pendientes.append(orden)
        
        # Calcular totales de producción para órdenes terminadas
        for orden in ordenes_terminadas:
            if hasattr(orden, 'registro_actual') and orden.registro_actual:
                # Calcular producción total del registro
                from inventario.models import LoteProductoEnProceso, LoteProductoTerminado
                from django.contrib.contenttypes.models import ContentType
                
                ct = ContentType.objects.get_for_model(Refilado)
                
                # Sumar producción de lotes WIP y PT generados por este registro
                lotes_wip = LoteProductoEnProceso.objects.filter(
                    proceso_origen_content_type=ct,
                    proceso_origen_object_id=orden.registro_actual.id
                )
                lotes_pt = LoteProductoTerminado.objects.filter(
                    proceso_final_content_type=ct,
                    proceso_final_object_id=orden.registro_actual.id
                )
                
                total_wip = sum(lote.cantidad_producida_primaria for lote in lotes_wip)
                total_pt = sum(lote.cantidad_producida for lote in lotes_pt)
                orden.produccion_total = total_wip + total_pt
        
        # Actualizar contexto con las variables correctas que espera el template
        context.update({
            'ordenes_pendientes': ordenes_pendientes,
            'ordenes_proceso': ordenes_proceso,
            'ordenes_pausadas': ordenes_pausadas,
            'ordenes_terminadas': ordenes_terminadas,
            # También mantener las variables originales para compatibilidad
            'ordenes_en_proceso': ordenes_proceso,
            'ordenes_completadas': ordenes_terminadas,
        })
        
        return context
    
    def get_orden_estado(self, orden):
        """Determina el estado específico para el proceso de refilado."""
        if orden.etapa_actual == 'REFI':
            return 'en_proceso'
        elif orden.etapa_actual in ['PROG', 'IMPR']:
            return 'pendiente'
        elif orden.etapa_actual in ['SELL', 'DOBL', 'TERM']:
            return 'completado'
        return 'pendiente'


class SelladoKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Sellado."""
    template_name = 'produccion/kanban/sellado_kanban.html'
    proceso_nombre = 'Sellado'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Configurar URL para el botón de nuevo registro
        context['create_url'] = reverse('produccion_web:sellado-create')
        context['create_button_text'] = 'Nuevo Registro de Sellado'
        
        # Lógica específica para sellado
        from ..models import Sellado
        
        registros_activos = Sellado.objects.filter(
            is_active=True,
            hora_final__isnull=True  # Registros en proceso
        ).select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        )
        
        context['registros_activos'] = registros_activos
        return context
    
    def get_orden_estado(self, orden):
        """Determina el estado específico para el proceso de sellado."""
        if orden.etapa_actual == 'SELL':
            return 'en_proceso'
        elif orden.etapa_actual in ['IMPR', 'REFI']:
            return 'pendiente'
        elif orden.etapa_actual in ['DOBL', 'TERM']:
            return 'completado'
        return 'pendiente'


class DobladoKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Doblado."""
    template_name = 'produccion/kanban/doblado_kanban.html'
    proceso_nombre = 'Doblado'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Configurar URL para el botón de nuevo registro
        context['create_url'] = reverse('produccion_web:doblado-create')
        context['create_button_text'] = 'Nuevo Registro de Doblado'
        
        # Lógica específica para doblado
        from ..models import Doblado
        
        registros_activos = Doblado.objects.filter(
            is_active=True,
            hora_final__isnull=True  # Registros en proceso
        ).select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        )
        
        context['registros_activos'] = registros_activos
        return context
    
    def get_orden_estado(self, orden):
        """Determina el estado específico para el proceso de doblado."""
        if orden.etapa_actual == 'DOBL':
            return 'en_proceso'
        elif orden.etapa_actual in ['IMPR', 'REFI', 'SELL']:
            return 'pendiente'
        elif orden.etapa_actual == 'TERM':
            return 'completado'
        return 'pendiente'