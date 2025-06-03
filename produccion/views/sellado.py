# produccion/views/sellado.py
"""
Vistas específicas para el proceso de Sellado.
Incluye vistas HTML, ViewSets y acciones específicas para el proceso de sellado.
"""

from django.db import transaction
from django.views.generic import ListView
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .base import (
    BaseProduccionViewSet, BaseProduccionCreateView, BaseProduccionUpdateView, 
    BaseProduccionDetailView, ValidationError, logger
)
from ..models import Sellado
from ..serializers import (
    SelladoSerializer, ConsumoWipSelladoSerializer, ConsumoMpSelladoSerializer, 
    ProduccionSelladoSerializer
)
from ..forms import (
    RegistroSelladoForm, ParoSelladoFormset, ConsumoWipSelladoFormset, 
    ProduccionSelladoFormSet
)
from ..services import (
    consumir_rollo_entrada_sellado, consumir_mp_sellado, registrar_produccion_bolsas_sellado
)
from inventario.models import LoteProductoTerminado, LoteProductoEnProceso


# =============================================
# === VISTAS HTML PARA SELLADO ===
# =============================================

class RegistroSelladoCreateView(BaseProduccionCreateView):
    """Vista para crear un nuevo registro de sellado."""
    model = Sellado
    form_class = RegistroSelladoForm
    template_name = 'produccion/registro_sellado_form.html'
    success_url = reverse_lazy('produccion_web:registro-sellado-list')
    
    def get_formsets(self, context):
        """Define los formsets específicos para sellado."""
        data = self.request.POST if self.request.method == 'POST' else None
        return {
            'paro_formset': ParoSelladoFormset(data, instance=self.object, prefix='paro_formset'),
            'consumo_wip_formset': ConsumoWipSelladoFormset(data, instance=self.object, prefix='consumo_wip_formset'),
            'produccion_formset': ProduccionSelladoFormSet(data, instance=self.object, prefix='produccion_formset'),
        }
    
    def get_proceso_name(self):
        return "sellado"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar causas de paro al contexto
        from configuracion.models import CausaParo
        context['causas_paro'] = CausaParo.objects.all().order_by('codigo')
        
        context.update({
            'page_title': 'Nuevo Registro de Sellado',
            'form_action': 'Crear',
            **self.get_formsets(context)
        })
        return context


class RegistroSelladoUpdateView(BaseProduccionUpdateView):
    """Vista para actualizar un registro de sellado."""
    model = Sellado
    form_class = RegistroSelladoForm
    template_name = 'produccion/registro_sellado_form.html'
    success_url = reverse_lazy('produccion_web:registro-sellado-list')
    
    def get_formsets(self, context):
        """Define los formsets específicos para sellado."""
        data = self.request.POST if self.request.method == 'POST' else None
        return {
            'paro_formset': ParoSelladoFormset(data, instance=self.object, prefix='paro_formset'),
            'consumo_wip_formset': ConsumoWipSelladoFormset(data, instance=self.object, prefix='consumo_wip_formset'),
            'produccion_formset': ProduccionSelladoFormSet(data, instance=self.object, prefix='produccion_formset'),
        }
    
    def get_proceso_name(self):
        return "sellado"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar causas de paro al contexto
        from configuracion.models import CausaParo
        context['causas_paro'] = CausaParo.objects.all().order_by('codigo')
        
        context.update({
            'page_title': f'Editar Registro de Sellado - {self.object.orden_produccion.op_numero}',
            'form_action': 'Actualizar',
            **self.get_formsets(context)
        })
        return context


class RegistroSelladoListView(ListView):
    """Vista para listar todos los registros de sellado."""
    model = Sellado
    template_name = 'produccion/registro_sellado_list.html'
    context_object_name = 'registros'
    
    def get_queryset(self):
        """Obtener todos los registros activos ordenados por fecha y hora."""
        return Sellado.objects.filter(is_active=True).select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        ).order_by('-fecha', '-hora_inicio')


class RegistroSelladoDetailView(BaseProduccionDetailView):
    """Vista para mostrar detalles de un registro de sellado."""
    template_name = 'produccion/registro_sellado_detail.html'
    
    def get_queryset(self):
        return Sellado.objects.filter(is_active=True).select_related(
            'orden_produccion', 'orden_produccion__cliente', 'orden_produccion__producto',
            'maquina', 'operario_principal'
        )
    
    def get_lotes_producidos(self, registro):
        """Obtiene información de lotes producidos en sellado (bolsas)."""
        from django.contrib.contenttypes.models import ContentType
        
        ct = ContentType.objects.get_for_model(registro.__class__)
        
        # Sellado normalmente produce PT (bolsas) pero puede producir WIP en algunos casos
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
                'cantidad_producida': lote.cantidad_actual
            } for lote in lotes_wip
        ] + [
            {
                'tipo': 'PT',
                'lote_id': lote.lote_id,
                'cantidad_producida': lote.cantidad_actual
            } for lote in lotes_pt
        ]
        
        return {
            'lotes_wip': lotes_wip,
            'lotes_pt': lotes_pt,
            'lotes_data': lotes_data,
            'total_lotes': lotes_wip.count() + lotes_pt.count()
        }
    
    def calculate_totales(self, registro, lotes_data):
        """Calcula totales específicos para sellado."""
        # Calcular total de WIP consumido
        total_wip_kg = sum(
            consumo.cantidad_kg_consumida 
            for consumo in registro.consumos_wip.all()
        )
        
        # Calcular total de MP consumida (zipper, válvulas, etc.)
        total_mp_unidades = sum(
            consumo.cantidad_consumida 
            for consumo in registro.consumos_mp.all()
        )
        
        # Calcular total producido (unidades de bolsas)
        total_producido_unidades = sum(
            lote.cantidad_actual
            for lote_type in ['lotes_wip', 'lotes_pt']
            for lote in lotes_data.get(lote_type, [])
        )
        
        # Calcular eficiencia de material (unidades producidas vs kg de WIP)
        eficiencia_material = (total_producido_unidades / total_wip_kg) if total_wip_kg > 0 else 0
        
        return {
            'total_wip_kg': total_wip_kg,
            'total_mp_unidades': total_mp_unidades,
            'total_producido_unidades': total_producido_unidades,
            'eficiencia_material': round(eficiencia_material, 2),
        }
    
    def get_proceso_name(self):
        return "sellado"


# =============================================
# === VIEWSET PARA REGISTRO DE SELLADO ===
# =============================================

class SelladoViewSet(BaseProduccionViewSet):
    """ViewSet para Registros de Sellado."""
    queryset = Sellado.objects.filter(is_active=True).select_related(
        'orden_produccion', 'maquina', 'operario_principal'
    )
    serializer_class = SelladoSerializer

    @action(detail=True, methods=['post'], url_path='consumir-wip')
    def consumir_wip(self, request, pk=None):
        """Acción para consumir WIP (rollo) en el proceso de sellado."""
        registro = self.get_object()
        serializer = ConsumoWipSelladoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = consumir_rollo_entrada_sellado(
                        sellado=registro,
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
        """Acción para consumir Materia Prima en el proceso de sellado."""
        registro = self.get_object()
        serializer = ConsumoMpSelladoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = consumir_mp_sellado(
                        sellado=registro,
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
        """Acción para registrar producción del proceso de sellado."""
        registro = self.get_object()
        serializer = ProduccionSelladoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = registrar_produccion_bolsas_sellado(
                        sellado=registro,
                        lote_salida_id=serializer.validated_data['lote_salida_id'],
                        unidades_producidas=serializer.validated_data['unidades_producidas'],
                        ubicacion_destino_codigo=serializer.validated_data['ubicacion_destino_codigo'],
                        usuario=request.user,
                        observaciones_lote=serializer.validated_data.get('observaciones_lote', '')
                    )
                return Response({
                    'status': 'success',
                    'message': f'Producción registrada exitosamente. Lote: {lote.lote_id}',
                    'tipo_lote': 'PT',  # Sellado siempre produce PT (bolsas)
                    'lote_creado_id': lote.lote_id,
                    'detalle': 'Bolsas selladas registradas como Producto Terminado.'
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