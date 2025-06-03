# produccion/views/refilado.py
"""
Vistas específicas para el proceso de Refilado.
Incluye vistas HTML, ViewSets y acciones específicas para el proceso de refilado.
"""

from django.db import transaction
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .base import (
    BaseProduccionViewSet, BaseProduccionCreateView, BaseProduccionUpdateView, 
    BaseProduccionDetailView, ValidationError, logger
)
from ..models import Refilado
from ..serializers import (
    RefiladoSerializer, ConsumoWipRefiladoSerializer, ConsumoMpRefiladoSerializer, 
    ProduccionRefiladoSerializer
)
from ..forms import (
    RegistroRefiladoForm, ParoRefiladoFormset, ConsumoWipRefiladoFormset, 
    ProduccionRefiladoFormSet
)
from ..services import (
    consumir_rollo_entrada_refilado, consumir_mp_refilado, registrar_produccion_rollo_refilado
)
from inventario.models import LoteProductoTerminado, LoteProductoEnProceso


# =============================================
# === VISTAS HTML PARA REFILADO ===
# =============================================

class RegistroRefiladoCreateView(BaseProduccionCreateView):
    """Vista para crear un nuevo registro de refilado."""
    model = Refilado
    form_class = RegistroRefiladoForm
    template_name = 'produccion/registro_refilado_form.html'
    success_url = reverse_lazy('produccion_web:registro-refilado-list')
    
    def get_formsets(self, context):
        """Define los formsets específicos para refilado."""
        # Pasar datos POST cuando se está procesando el formulario
        data = self.request.POST if self.request.method == 'POST' else None
        return {
            'paro_formset': ParoRefiladoFormset(data, instance=self.object, prefix='paro_formset'),
            'consumo_wip_formset': ConsumoWipRefiladoFormset(data, instance=self.object, prefix='consumo_wip_formset'),
            'produccion_formset': ProduccionRefiladoFormSet(data, instance=self.object, prefix='produccion_formset'),
        }
    
    def get_proceso_name(self):
        return "refilado"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar causas de paro al contexto
        from configuracion.models import CausaParo
        context['causas_paro'] = CausaParo.objects.all().order_by('codigo')
        
        context.update({
            'page_title': 'Nuevo Registro de Refilado',
            'form_action': 'Crear',
            **self.get_formsets(context)
        })
        return context


class RegistroRefiladoUpdateView(BaseProduccionUpdateView):
    """Vista para actualizar un registro de refilado."""
    model = Refilado
    form_class = RegistroRefiladoForm
    template_name = 'produccion/registro_refilado_form.html'
    success_url = reverse_lazy('produccion_web:registro-refilado-list')
    
    def get_formsets(self, context):
        """Define los formsets específicos para refilado."""
        # Pasar datos POST cuando se está procesando el formulario
        data = self.request.POST if self.request.method == 'POST' else None
        return {
            'paro_formset': ParoRefiladoFormset(data, instance=self.object, prefix='paro_formset'),
            'consumo_wip_formset': ConsumoWipRefiladoFormset(data, instance=self.object, prefix='consumo_wip_formset'),
            'produccion_formset': ProduccionRefiladoFormSet(data, instance=self.object, prefix='produccion_formset'),
        }
    
    def get_proceso_name(self):
        return "refilado"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar causas de paro al contexto
        from configuracion.models import CausaParo
        context['causas_paro'] = CausaParo.objects.all().order_by('codigo')
        
        context.update({
            'page_title': f'Editar Registro de Refilado - {self.object.orden_produccion.op_numero}',
            'form_action': 'Actualizar',
            **self.get_formsets(context)
        })
        return context


class RegistroRefiladoListView(ListView):
    """Vista para listar todos los registros de refilado."""
    model = Refilado
    template_name = 'produccion/registro_refilado_list.html'
    context_object_name = 'registros'
    
    def get_queryset(self):
        """Obtener todos los registros activos ordenados por fecha y hora."""
        return Refilado.objects.filter(is_active=True).select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        ).order_by('-fecha', '-hora_inicio')


class RegistroRefiladoDetailView(BaseProduccionDetailView):
    """Vista para mostrar detalles de un registro de refilado."""
    template_name = 'produccion/registro_refilado_detail.html'
    
    def get_queryset(self):
        return Refilado.objects.filter(is_active=True).select_related(
            'orden_produccion', 'orden_produccion__cliente', 'orden_produccion__producto',
            'maquina', 'operario_principal'
        )
    
    def get_lotes_producidos(self, registro):
        """Obtiene información de lotes producidos en refilado."""
        from django.contrib.contenttypes.models import ContentType
        from inventario.models import LoteProductoEnProceso, LoteProductoTerminado
        
        ct = ContentType.objects.get_for_model(registro.__class__)
        
        lotes_wip = LoteProductoEnProceso.objects.filter(
            proceso_origen_content_type=ct,
            proceso_origen_object_id=registro.id
        ).select_related('ubicacion', 'producto_terminado')
        
        lotes_pt = LoteProductoTerminado.objects.filter(
            proceso_final_content_type=ct,
            proceso_final_object_id=registro.id
        ).select_related('ubicacion', 'producto_terminado')
        
        lotes_data = [
            {
                'tipo': 'WIP',
                'lote_id': lote.lote_id,
                'cantidad_producida': lote.cantidad_producida_primaria
            } for lote in lotes_wip
        ] + [
            {
                'tipo': 'PT',
                'lote_id': lote.lote_id,
                'cantidad_producida': lote.cantidad_producida
            } for lote in lotes_pt
        ]
        
        return {
            'lotes_wip': lotes_wip,
            'lotes_pt': lotes_pt,
            'lotes_data': lotes_data,
            'total_lotes': lotes_wip.count() + lotes_pt.count()
        }
    
    def calculate_totales(self, registro, lotes_data):
        """Calcula totales específicos para refilado."""
        # Calcular totales de producción
        total_kg_producidos = sum(
            lote.cantidad_producida_primaria if hasattr(lote, 'cantidad_producida_primaria') 
            else lote.cantidad_producida
            for lote_type in ['lotes_wip', 'lotes_pt']
            for lote in lotes_data.get(lote_type, [])
        )
        
        # Calcular totales de consumo - CORREGIDO: usar nombres correctos de las relaciones
        total_kg_consumidos = sum(
            consumo.cantidad_kg_consumida 
            for consumo in registro.consumos_wip.all()
        ) + sum(
            consumo.cantidad_consumida 
            for consumo in registro.consumos_mp.all()
        )
        
        # Calcular rendimiento
        rendimiento = (total_kg_producidos / total_kg_consumidos * 100) if total_kg_consumidos > 0 else 0
        
        return {
            'total_kg_producidos': total_kg_producidos,
            'total_kg_consumidos': total_kg_consumidos,
            'rendimiento': round(rendimiento, 2),
        }
    
    def get_proceso_name(self):
        return "refilado"


# =============================================
# === VIEWSET PARA REGISTRO DE REFILADO ===
# =============================================

class RefiladoViewSet(BaseProduccionViewSet):
    """ViewSet para Registros de Refilado."""
    queryset = Refilado.objects.filter(is_active=True).select_related(
        'orden_produccion', 'maquina', 'operario_principal'
    )
    serializer_class = RefiladoSerializer
    
    @action(detail=True, methods=['post'], url_path='consumir-wip')
    def consumir_wip(self, request, pk=None):
        """Acción para consumir WIP (rollo) en el proceso de refilado."""
        registro = self.get_object()
        serializer = ConsumoWipRefiladoSerializer(
            data=request.data,
            context={'registro_refilado': registro}
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    consumo = consumir_rollo_entrada_refilado(
                        registro_refilado=registro,
                        lote_wip_id=serializer.validated_data['lote_consumido'].lote_id,
                        cantidad_kg=serializer.validated_data['cantidad_kg'],
                        usuario=request.user
                    )
                return Response({
                    'status': 'success',
                    'message': f'Consumo WIP registrado exitosamente. Lote: {consumo.lote_consumido.lote_id}'
                }, status=status.HTTP_200_OK)
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.exception(f"Error inesperado en consumir_wip: {e}")
                return Response({
                    'status': 'error',
                    'message': 'Error interno del servidor'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='consumir-mp')
    def consumir_mp(self, request, pk=None):
        """Acción para consumir Materia Prima en el proceso de refilado."""
        registro = self.get_object()
        serializer = ConsumoMpRefiladoSerializer(
            data=request.data,
            context={'registro_refilado': registro}
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    consumo = consumir_mp_refilado(
                        registro_refilado=registro,
                        lote_mp_id=serializer.validated_data['lote_consumido'].lote_id,
                        cantidad_kg=serializer.validated_data['cantidad_kg'],
                        usuario=request.user
                    )
                return Response({
                    'status': 'success',
                    'message': f'Consumo MP registrado exitosamente. Lote: {consumo.lote_consumido.lote_id}'
                }, status=status.HTTP_200_OK)
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.exception(f"Error inesperado en consumir_mp: {e}")
                return Response({
                    'status': 'error',
                    'message': 'Error interno del servidor'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='registrar-produccion')
    def registrar_produccion(self, request, pk=None):
        """Acción para registrar producción del proceso de refilado."""
        registro = self.get_object()
        serializer = ProduccionRefiladoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = registrar_produccion_rollo_refilado(
                        registro_refilado=registro,
                        lote_salida_id=serializer.validated_data['lote_salida_id'],
                        kg_producidos=serializer.validated_data['kg_producidos'],
                        metros_producidos=serializer.validated_data.get('metros_producidos'),
                        ubicacion_destino_codigo=serializer.validated_data['ubicacion_destino_codigo'],
                        usuario=request.user,
                        observaciones_lote=serializer.validated_data.get('observaciones_lote', '')
                    )
                
                tipo_lote = 'PT' if isinstance(lote, LoteProductoTerminado) else 'WIP'
                return Response({
                    'status': 'success',
                    'message': f'Producción registrada exitosamente. Lote: {lote.lote_id}',
                    'tipo_lote': tipo_lote,
                    'lote_creado_id': lote.lote_id,
                    'detalle': 'El tipo de lote (WIP/PT) se determina automáticamente según la secuencia de procesos de la OP.'
                }, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.exception(f"Error inesperado en registrar_produccion: {e}")
                return Response({
                    'status': 'error',
                    'message': 'Error interno del servidor'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
