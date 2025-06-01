# produccion/views/doblado.py
"""
Vistas específicas para el proceso de Doblado.
Incluye vistas HTML, ViewSets y acciones específicas para el proceso de doblado.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .base import (
    BaseProduccionViewSet, BaseProduccionCreateView, BaseProduccionUpdateView, 
    BaseProduccionDetailView, ValidationError, logger
)
from ..models import Doblado
from ..serializers import (
    DobladoSerializer, ConsumoWipDobladoSerializer, ConsumoMpDobladoSerializer, 
    ProduccionDobladoSerializer
)
from ..forms import (
    RegistroDobladoForm, ParoDobladoFormset, ConsumoWipDobladoFormset, 
    ProduccionDobladoFormSet
)
from ..services import (
    consumir_rollo_entrada_doblado, consumir_mp_doblado, registrar_produccion_rollo_doblado
)
from inventario.models import LoteProductoTerminado, LoteProductoEnProceso


# =============================================
# === VISTAS HTML PARA DOBLADO ===
# =============================================

class RegistroDobladoCreateView(BaseProduccionCreateView):
    """Vista para crear un nuevo registro de doblado."""
    model = Doblado
    form_class = RegistroDobladoForm
    template_name = 'produccion/registro_doblado_form.html'
    success_url = '/produccion/doblado/'
    
    def get_formsets(self, context):
        """Define los formsets específicos para doblado."""
        data = self.request.POST if self.request.method == 'POST' else None
        return {
            'paro_formset': ParoDobladoFormset(data, instance=self.object, prefix='paro_formset'),
            'consumo_wip_formset': ConsumoWipDobladoFormset(data, instance=self.object, prefix='consumo_wip_formset'),
            'produccion_formset': ProduccionDobladoFormSet(data, instance=self.object, prefix='produccion_formset'),
        }
    
    def get_proceso_name(self):
        return "doblado"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Nuevo Registro de Doblado',
            'form_action': 'Crear',
            **self.get_formsets(context)
        })
        return context


class RegistroDobladoUpdateView(BaseProduccionUpdateView):
    """Vista para actualizar un registro de doblado."""
    model = Doblado
    form_class = RegistroDobladoForm
    template_name = 'produccion/registro_doblado_form.html'
    success_url = '/produccion/doblado/'
    
    def get_formsets(self, context):
        """Define los formsets específicos para doblado."""
        data = self.request.POST if self.request.method == 'POST' else None
        return {
            'paro_formset': ParoDobladoFormset(data, instance=self.object, prefix='paro_formset'),
            'consumo_wip_formset': ConsumoWipDobladoFormset(data, instance=self.object, prefix='consumo_wip_formset'),
            'produccion_formset': ProduccionDobladoFormSet(data, instance=self.object, prefix='produccion_formset'),
        }
    
    def get_proceso_name(self):
        return "doblado"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': f'Editar Registro de Doblado - {self.object.orden_produccion.op_numero}',
            'form_action': 'Actualizar',
            **self.get_formsets(context)
        })
        return context


class RegistroDobladoDetailView(BaseProduccionDetailView):
    """Vista para mostrar detalles de un registro de doblado."""
    template_name = 'produccion/registro_doblado_detail.html'
    
    def get_queryset(self):
        return Doblado.objects.select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        ).prefetch_related(
            'paros_doblado', 'desperdicios_doblado', 'consumos_wip_doblado',
            'consumos_mp_doblado'
        )
    
    def get_lotes_producidos(self, registro):
        """Obtiene información de lotes producidos en doblado."""
        lotes_wip = LoteProductoEnProceso.objects.filter(
            registro_origen_doblado=registro
        ).select_related('ubicacion', 'producto')
        
        lotes_pt = LoteProductoTerminado.objects.filter(
            registro_origen_doblado=registro
        ).select_related('ubicacion', 'producto')
        
        return {
            'lotes_wip': lotes_wip,
            'lotes_pt': lotes_pt,
            'total_lotes': lotes_wip.count() + lotes_pt.count()
        }
    
    def calculate_totales(self, registro, lotes_data):
        """Calcula totales específicos para doblado."""
        # Calcular total de WIP consumido
        total_wip_kg = sum(
            consumo.cantidad_kg_consumida for consumo in registro.consumos_wip_doblado.all()
        )
        
        # Calcular total de MP consumida
        total_mp_kg = sum(
            consumo.cantidad_consumida for consumo in registro.consumos_mp_doblado.all()
        )
        
        # Calcular total producido
        total_producido_kg = sum(
            lote.cantidad_actual for lote in lotes_data['lotes_wip']
        ) + sum(
            lote.cantidad_actual for lote in lotes_data['lotes_pt']
        )
        
        # Calcular eficiencia de material
        total_entrada = total_wip_kg + total_mp_kg
        eficiencia_material = (total_producido_kg / total_entrada * 100) if total_entrada > 0 else 0
        
        return {
            'total_wip_kg': total_wip_kg,
            'total_mp_kg': total_mp_kg,
            'total_producido_kg': total_producido_kg,
            'eficiencia_material': round(eficiencia_material, 2),
        }
    
    def get_proceso_name(self):
        return "doblado"


# =============================================
# === VIEWSET PARA REGISTRO DE DOBLADO ===
# =============================================

class DobladoViewSet(BaseProduccionViewSet):
    """ViewSet para Registros de Doblado."""
    queryset = Doblado.objects.filter(is_active=True).select_related(
        'orden_produccion', 'maquina', 'operario_principal'
    )
    serializer_class = DobladoSerializer

    @action(detail=True, methods=['post'], url_path='consumir-wip')
    def consumir_wip(self, request, pk=None):
        """Acción para consumir WIP (rollo) en el proceso de doblado."""
        registro = self.get_object()
        serializer = ConsumoWipDobladoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = consumir_rollo_entrada_doblado(
                        doblado=registro,
                        lote_entrada_id=serializer.validated_data['lote_entrada_id'],
                        cantidad_kg=serializer.validated_data['cantidad_kg'],
                        usuario=request.user
                    )
                return Response({
                    'status': 'success',
                    'message': f'Consumo WIP registrado exitosamente. Lote: {lote.lote_id}'
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
        """Acción para consumir Materia Prima en el proceso de doblado."""
        registro = self.get_object()
        serializer = ConsumoMpDobladoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = consumir_mp_doblado(
                        doblado=registro,
                        lote_mp_id=serializer.validated_data['lote_mp_id'],
                        cantidad_consumida=serializer.validated_data['cantidad_consumida'],
                        usuario=request.user
                    )
                return Response({
                    'status': 'success',
                    'message': f'Consumo MP registrado exitosamente. Lote: {lote.lote_id}'
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
        """Acción para registrar producción del proceso de doblado."""
        registro = self.get_object()
        serializer = ProduccionDobladoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = registrar_produccion_rollo_doblado(
                        doblado=registro,
                        lote_salida_id=serializer.validated_data['lote_salida_id'],
                        kg_producidos=serializer.validated_data['kg_producidos'],
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