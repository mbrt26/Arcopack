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
    proceso_nombre = 'Impresion'
    
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
        elif orden.etapa_actual in ['LIBR', 'PROG']:
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
        
        # Lógica específica para refilado
        from ..models import Refilado
        
        registros_activos = Refilado.objects.filter(
            is_active=True,
            hora_final__isnull=True  # Registros en proceso
        ).select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        )
        
        context['registros_activos'] = registros_activos
        return context
    
    def get_orden_estado(self, orden):
        """Determina el estado específico para el proceso de refilado."""
        if orden.etapa_actual == 'REFI':
            return 'en_proceso'
        elif orden.etapa_actual == 'IMPR':
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