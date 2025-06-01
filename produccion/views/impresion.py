# produccion/views/impresion.py
"""
Vistas específicas para el proceso de Impresión.
Incluye vistas HTML, ViewSets y acciones específicas para el proceso de impresión.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .base import (
    BaseProduccionViewSet, BaseProduccionCreateView, BaseProduccionUpdateView, 
    BaseProduccionDetailView, ValidationError, logger
)
from ..models import RegistroImpresion
from ..serializers import (
    RegistroImpresionSerializer, ConsumoImpresionSerializer, ProduccionImpresionSerializer
)
from ..forms import (
    RegistroImpresionForm, ParoImpresionFormset, DesperdicioImpresionFormset,
    ConsumoTintaImpresionFormset, ConsumoSustratoImpresionFormset, ProduccionImpresionFormset
)
from ..services import consumir_sustrato_impresion, registrar_produccion_rollo_impreso
from inventario.models import LoteProductoTerminado, LoteProductoEnProceso


# =============================================
# === VISTAS HTML PARA IMPRESIÓN ===
# =============================================

class RegistroImpresionCreateView(BaseProduccionCreateView):
    """Vista para crear un nuevo registro de impresión."""
    model = RegistroImpresion
    form_class = RegistroImpresionForm
    template_name = 'produccion/registro_impresion_form.html'
    success_url = '/produccion/impresion/'
    
    def get_formsets(self, context):
        """Define los formsets específicos para impresión."""
        data = self.request.POST if self.request.method == 'POST' else None
        
        # Para CreateView, no pasamos instance ya que self.object es None
        # Usamos prefijos para evitar conflictos entre formsets
        if hasattr(self, 'object') and self.object:
            # UpdateView - tenemos una instancia
            return {
                'paro_formset': ParoImpresionFormset(data, instance=self.object, prefix='paro_formset'),
                'desperdicio_formset': DesperdicioImpresionFormset(data, instance=self.object, prefix='desperdicio_formset'),
                'consumo_tinta_formset': ConsumoTintaImpresionFormset(data, instance=self.object, prefix='consumo_tinta_formset'),
                'consumo_sustrato_formset': ConsumoSustratoImpresionFormset(data, instance=self.object, prefix='consumo_sustrato_formset'),
                'produccion_formset': ProduccionImpresionFormset(data, instance=self.object, prefix='produccion_formset'),
            }
        else:
            # CreateView - no tenemos instancia aún
            return {
                'paro_formset': ParoImpresionFormset(data, prefix='paro_formset'),
                'desperdicio_formset': DesperdicioImpresionFormset(data, prefix='desperdicio_formset'),
                'consumo_tinta_formset': ConsumoTintaImpresionFormset(data, prefix='consumo_tinta_formset'),
                'consumo_sustrato_formset': ConsumoSustratoImpresionFormset(data, prefix='consumo_sustrato_formset'),
                'produccion_formset': ProduccionImpresionFormset(data, prefix='produccion_formset'),
            }
    
    def get_proceso_name(self):
        return "impresión"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar los formsets al contexto
        formsets = self.get_formsets(context)
        context.update({
            'page_title': 'Nuevo Registro de Impresión',
            'form_action': 'Crear',
            **formsets  # Agregar todos los formsets al contexto
        })
        return context


class RegistroImpresionUpdateView(BaseProduccionUpdateView):
    """Vista para actualizar un registro de impresión."""
    model = RegistroImpresion
    form_class = RegistroImpresionForm
    template_name = 'produccion/registro_impresion_form.html'
    success_url = '/produccion/impresion/'
    
    def get_formsets(self, context):
        """Define los formsets específicos para impresión."""
        data = self.request.POST if self.request.method == 'POST' else None
        return {
            'paro_formset': ParoImpresionFormset(data, instance=self.object, prefix='paro_formset'),
            'desperdicio_formset': DesperdicioImpresionFormset(data, instance=self.object, prefix='desperdicio_formset'),
            'consumo_tinta_formset': ConsumoTintaImpresionFormset(data, instance=self.object, prefix='consumo_tinta_formset'),
            'consumo_sustrato_formset': ConsumoSustratoImpresionFormset(data, instance=self.object, prefix='consumo_sustrato_formset'),
            'produccion_formset': ProduccionImpresionFormset(data, instance=self.object, prefix='produccion_formset'),
        }
    
    def get_proceso_name(self):
        return "impresión"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': f'Editar Registro de Impresión - {self.object.orden_produccion.op_numero}',
            'form_action': 'Actualizar',
            **self.get_formsets(context)
        })
        return context


class RegistroImpresionDetailView(BaseProduccionDetailView):
    """Vista para mostrar detalles de un registro de impresión."""
    template_name = 'produccion/registro_impresion_detail.html'
    
    def get_queryset(self):
        return RegistroImpresion.objects.select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        ).prefetch_related(
            'paros_impresion', 'desperdicios_impresion', 'consumos_tinta_impresion',
            'consumos_sustrato_impresion', 'produccion_impresion'
        )
    
    def get_lotes_producidos(self, registro):
        """Obtiene información de lotes producidos en impresión."""
        lotes_wip = LoteProductoEnProceso.objects.filter(
            registro_origen_impresion=registro
        ).select_related('ubicacion', 'producto')
        
        lotes_pt = LoteProductoTerminado.objects.filter(
            registro_origen_impresion=registro
        ).select_related('ubicacion', 'producto')
        
        return {
            'lotes_wip': lotes_wip,
            'lotes_pt': lotes_pt,
            'total_lotes': lotes_wip.count() + lotes_pt.count()
        }
    
    def calculate_totales(self, registro, lotes_data):
        """Calcula totales específicos para impresión."""
        # Calcular total de sustrato consumido
        total_sustrato_kg = sum(
            consumo.cantidad_kg for consumo in registro.consumos_sustrato_impresion.all()
        )
        
        # Calcular total de tinta consumida
        total_tinta_kg = sum(
            consumo.cantidad_kg for consumo in registro.consumos_tinta_impresion.all()
        )
        
        # Calcular total producido
        total_producido_kg = sum(
            produccion.kg_producidos for produccion in registro.produccion_impresion.all()
        )
        
        # Calcular eficiencia de material
        eficiencia_material = (total_producido_kg / total_sustrato_kg * 100) if total_sustrato_kg > 0 else 0
        
        return {
            'total_sustrato_kg': total_sustrato_kg,
            'total_tinta_kg': total_tinta_kg,
            'total_producido_kg': total_producido_kg,
            'eficiencia_material': round(eficiencia_material, 2),
        }
    
    def get_proceso_name(self):
        return "impresión"


# =============================================
# === VIEWSET PARA REGISTRO DE IMPRESIÓN ===
# =============================================

class RegistroImpresionViewSet(BaseProduccionViewSet):
    """ViewSet para Registros de Impresión."""
    queryset = RegistroImpresion.objects.filter(is_active=True).select_related(
        'orden_produccion', 'maquina', 'operario_principal'
    )
    serializer_class = RegistroImpresionSerializer

    @action(detail=True, methods=['post'], url_path='consumir-sustrato')
    def consumir_sustrato(self, request, pk=None):
        """Acción para consumir sustrato en el proceso de impresión."""
        registro = self.get_object()
        serializer = ConsumoImpresionSerializer(
            data=request.data,
            context={'registro_impresion': registro}  # Pasar el registro para filtrar lotes
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = consumir_sustrato_impresion(
                        registro_impresion=registro,
                        lote_sustrato_id=serializer.validated_data['lote_consumido'].lote_id,
                        cantidad_kg=serializer.validated_data['cantidad_kg'],
                        usuario=request.user
                    )
                return Response({
                    'status': 'success',
                    'message': f'Consumo registrado exitosamente. Lote: {lote.lote_id}'
                }, status=status.HTTP_200_OK)
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.exception(f"Error inesperado en consumir_sustrato: {e}")
                return Response({
                    'status': 'error',
                    'message': 'Error interno del servidor'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='registrar-produccion')
    def registrar_produccion(self, request, pk=None):
        """Acción para registrar producción del proceso de impresión."""
        registro = self.get_object()
        serializer = ProduccionImpresionSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = registrar_produccion_rollo_impreso(
                        registro_impresion=registro,
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