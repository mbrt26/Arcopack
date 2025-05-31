# produccion/views.py

import logging
from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, CreateView, UpdateView, ListView
from django.db import models, transaction
from django.db.models import Q, F, Case, When, Value, BooleanField
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from configuracion.models import Proceso

# Importar modelos de esta app
from .models import OrdenProduccion, RegistroImpresion, Refilado, Sellado, Doblado

# Importar formularios
from .forms import (
    OrdenProduccionForm, RegistroImpresionForm, ParoImpresionFormset,
    DesperdicioImpresionFormset, ConsumoTintaImpresionFormset,
    ConsumoSustratoImpresionFormset, RegistroRefiladoForm,
    ParoRefiladoFormset, ConsumoWipRefiladoFormset, ProduccionImpresionFormset,
    ProduccionRefiladoFormSet, RegistroSelladoForm, ParoSelladoFormset,
    ConsumoWipSelladoFormset, ProduccionSelladoFormSet, RegistroDobladoForm,
    ParoDobladoFormset, ConsumoWipDobladoFormset, ProduccionDobladoFormSet
)

# Importar Serializers de esta app
from .serializers import (
    OrdenProduccionSerializer,
    RegistroImpresionSerializer, ConsumoImpresionSerializer, ProduccionImpresionSerializer,
    RefiladoSerializer, ConsumoWipRefiladoSerializer, ConsumoMpRefiladoSerializer, ProduccionRefiladoSerializer,
    SelladoSerializer, ConsumoWipSelladoSerializer, ConsumoMpSelladoSerializer, ProduccionSelladoSerializer,
    DobladoSerializer, ConsumoWipDobladoSerializer, ConsumoMpDobladoSerializer, ProduccionDobladoSerializer,
    LoteMateriaPrimaSerializer, LoteProductoEnProcesoSerializer,
)

# Importar funciones de servicio
from .services import (
    # Impresión
    consumir_sustrato_impresion, registrar_produccion_rollo_impreso,
    # Refilado
    consumir_rollo_entrada_refilado, consumir_mp_refilado, registrar_produccion_rollo_refilado,
    # Sellado
    consumir_rollo_entrada_sellado, consumir_mp_sellado, registrar_produccion_bolsas_sellado,
    # Doblado
    consumir_rollo_entrada_doblado, consumir_mp_doblado, registrar_produccion_rollo_doblado,
)

# Importar excepciones de Django y modelos para type hints/checks
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth import get_user_model
from inventario.models import LoteProductoEnProceso, LoteProductoTerminado, LoteMateriaPrima # Para isinstance

logger = logging.getLogger(__name__)
User = get_user_model()

# =============================================
# === VISTAS HTML PARA PRODUCCIÓN ===
# =============================================

def orden_produccion_list_view(request):
    """Vista para listar las Órdenes de Producción (HTML)."""
    ordenes = OrdenProduccion.objects.filter(is_active=True).select_related(
        'cliente', 'producto', 'sustrato'
    ).order_by('-fecha_creacion')
    context = {
        'ordenes': ordenes,
        'page_title': 'Listado de Órdenes de Producción'
    }
    return render(request, 'produccion/orden_produccion_list.html', context)

def orden_produccion_detail_view(request, pk):
    """Vista para ver el detalle de una Orden de Producción (HTML)."""
    orden = get_object_or_404(
        OrdenProduccion.objects.select_related(
            'cliente', 'producto', 'sustrato', 'creado_por', 'actualizado_por'
        ).prefetch_related('procesos'),
        pk=pk,
        is_active=True
    )
    # Aquí podrías añadir más lógica para obtener datos relacionados
    # como registros de impresión, refilado, etc., si los necesitas en la plantilla.
    context = {
        'orden': orden,
        'page_title': f'Detalle OP: {orden.op_numero}'
    }
    return render(request, 'produccion/orden_produccion_detail.html', context)

@login_required
def anular_orden_view(request, pk):
    """Vista para anular una orden de producción."""
    orden = get_object_or_404(OrdenProduccion, pk=pk)
    if request.method == 'POST':
        orden.is_active = False
        orden.save(update_fields=['is_active'])
        messages.success(request, f'Orden {orden.op_numero} anulada exitosamente.')
    return redirect('produccion:produccion_orden_list')

class ProcesoListView(LoginRequiredMixin, ListView):
    """Vista para listar los procesos productivos."""
    model = Proceso
    template_name = 'produccion/proceso_list.html'
    context_object_name = 'procesos'
    
    def get_queryset(self):
        procesos = Proceso.objects.order_by('orden_flujo', 'nombre')
        for proceso in procesos:
            proceso.kanban_url = f"{proceso.nombre.lower()}-kanban"
        return procesos

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Procesos de Producción'
        return context

class ResultadosProduccionView(LoginRequiredMixin, TemplateView):
    """Vista para mostrar los resultados de producción."""
    template_name = 'produccion/resultados_produccion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Resultados de Producción'
        # Aquí puedes agregar la lógica para obtener estadísticas de producción
        return context

# =============================================
# === VIEWSET PARA ORDEN DE PRODUCCIÓN ===
# =============================================
class OrdenProduccionViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD básico para Ordenes de Producción."""
    queryset = OrdenProduccion.objects.filter(is_active=True).select_related(
        'cliente', 'producto', 'sustrato', 'creado_por', 'actualizado_por'
    ).prefetch_related('procesos')
    serializer_class = OrdenProduccionSerializer
    permission_classes = [permissions.IsAuthenticated] # Requiere login

    # Opcional: Filtros/Búsqueda/Ordenación
    # filter_backends = [...]
    # filterset_fields = [...]
    # search_fields = [...]
    # ordering_fields = [...]
    # ordering = [...]

    def perform_create(self, serializer):
        """Asigna usuario creador."""
        serializer.save(creado_por=self.request.user, actualizado_por=self.request.user)

    def perform_update(self, serializer):
        """Asigna usuario actualizador y valida cambio de código."""
        instance = serializer.instance
        validated_data = serializer.validated_data
        nuevo_codigo = validated_data.get('codigo', instance.codigo)
        # Validar cambio de código (aunque también está en Serializer/Modelo)
        if instance.codigo != nuevo_codigo and instance._has_related_orders(): # Usa método helper del modelo
             raise DRFValidationError({'codigo': "No se puede cambiar código si OP tiene registros asociados."}) # O adaptar mensaje
        serializer.save(actualizado_por=self.request.user)

    def perform_destroy(self, instance: OrdenProduccion):
        """Soft delete: Marca como Anulada e inactiva."""
        if instance.is_active:
            instance.is_active = False
            instance.etapa_actual = 'ANUL'
            instance.save(user=self.request.user)
            logger.info(f"Orden Producción '{instance.op_numero}' anulada por usuario '{self.request.user}'.")

# =============================================
# === VIEWSET PARA REGISTRO DE IMPRESIÓN ===
# =============================================
class RegistroImpresionViewSet(viewsets.ModelViewSet):
    """ViewSet para Registros de Impresión."""
    queryset = RegistroImpresion.objects.filter(is_active=True)
    serializer_class = RegistroImpresionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def consumir_sustrato(self, request, pk=None):
        registro = self.get_object()
        serializer = ConsumoImpresionSerializer(
            data=request.data,
            registro_impresion=registro  # Pasar el registro para filtrar lotes
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
                })
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['post'])
    def registrar_produccion(self, request, pk=None):
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
                return Response({
                    'status': 'success',
                    'message': f'Producción registrada exitosamente. Lote: {lote.lote_id}',
                    'tipo_lote': 'PT' if isinstance(lote, LoteProductoTerminado) else 'WIP',
                    'detalle': 'El tipo de lote (WIP/PT) se determina automáticamente según la secuencia de procesos de la OP.'
                })
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
        return Response(serializer.errors, status=400)

# =============================================
# === VIEWSET PARA REFILADO ===
# =============================================
class RefiladoViewSet(viewsets.ModelViewSet):
    """ViewSet para Refilado con acciones."""
    queryset = Refilado.objects.filter(is_active=True).select_related('orden_produccion', 'maquina', 'operario_principal')
    serializer_class = RefiladoSerializer
    permission_classes = [permissions.IsAuthenticated]

    perform_create = RegistroImpresionViewSet.perform_create # Reutilizar
    perform_update = RegistroImpresionViewSet.perform_update # Reutilizar
    perform_destroy = RegistroImpresionViewSet.perform_destroy # Reutilizar

    @action(detail=True, methods=['post'], url_path='consumir-wip', serializer_class=ConsumoWipRefiladoSerializer)
    def consumir_wip(self, request, pk=None):
        refilado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consumir_rollo_entrada_refilado(refilado=refilado, usuario=request.user, **serializer.validated_data)
            return Response({'status': 'consumo WIP registrado'}, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': 'Error interno'}, status=500)

    @action(detail=True, methods=['post'], url_path='consumir-mp', serializer_class=ConsumoMpRefiladoSerializer)
    def consumir_mp(self, request, pk=None):
        refilado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consumir_mp_refilado(refilado=refilado, usuario=request.user, **serializer.validated_data)
            return Response({'status': 'consumo MP registrado'}, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': 'Error interno'}, status=500)

    @action(detail=True, methods=['post'], url_path='registrar-produccion', serializer_class=ProduccionRefiladoSerializer)
    def registrar_produccion(self, request, pk=None):
        refilado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            nuevo_lote = registrar_produccion_rollo_refilado(refilado=refilado, usuario=request.user, **serializer.validated_data)
            tipo_lote = "WIP" if isinstance(nuevo_lote, LoteProductoEnProceso) else "PT"
            return Response({'status': f'producción registrada ({tipo_lote})', 'lote_creado_id': nuevo_lote.lote_id, 'tipo_lote': tipo_lote, 'detalle': 'El tipo de lote se determina automáticamente según la secuencia de procesos de la OP.'}, status=status.HTTP_201_CREATED)
        except (ValidationError, ValueError, RuntimeError, ObjectDoesNotExist) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': 'Error interno'}, status=500)

# =============================================
# === VIEWSET PARA SELLADO ===
# =============================================
class SelladoViewSet(viewsets.ModelViewSet):
    """ViewSet para Sellado con acciones."""
    queryset = Sellado.objects.filter(is_active=True).select_related('orden_produccion', 'maquina', 'operario_principal')
    serializer_class = SelladoSerializer
    permission_classes = [permissions.IsAuthenticated]

    perform_create = RegistroImpresionViewSet.perform_create
    perform_update = RegistroImpresionViewSet.perform_update
    perform_destroy = RegistroImpresionViewSet.perform_destroy

    @action(detail=True, methods=['post'], url_path='consumir-wip', serializer_class=ConsumoWipSelladoSerializer)
    def consumir_wip(self, request, pk=None):
        sellado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consumir_rollo_entrada_sellado(sellado=sellado, usuario=request.user, **serializer.validated_data)
            return Response({'status': 'consumo WIP registrado'}, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': 'Error interno'}, status=500)

    @action(detail=True, methods=['post'], url_path='consumir-mp', serializer_class=ConsumoMpSelladoSerializer)
    def consumir_mp(self, request, pk=None):
        sellado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consumir_mp_sellado(sellado=sellado, usuario=request.user, **serializer.validated_data)
            return Response({'status': 'consumo MP registrado'}, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': '...'}, status=500)

    @action(detail=True, methods=['post'], url_path='registrar-produccion', serializer_class=ProduccionSelladoSerializer)
    def registrar_produccion(self, request, pk=None):
        sellado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            nuevo_lote = registrar_produccion_bolsas_sellado(sellado=sellado, usuario=request.user, **serializer.validated_data)
            tipo_lote = "WIP" if isinstance(nuevo_lote, LoteProductoEnProceso) else "PT"
            return Response({'status': f'producción registrada ({tipo_lote})', 'lote_creado_id': nuevo_lote.lote_id, 'tipo_lote': tipo_lote, 'detalle': 'El tipo de lote se determina automáticamente según la secuencia de procesos de la OP.'}, status=status.HTTP_201_CREATED)
        except (ValidationError, ValueError, RuntimeError, ObjectDoesNotExist) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': '...'}, status=500)

# =============================================
# === VIEWSET PARA DOBLADO ===
# =============================================
class DobladoViewSet(viewsets.ModelViewSet):
    """ViewSet para Doblado con acciones."""
    queryset = Doblado.objects.filter(is_active=True).select_related('orden_produccion', 'maquina', 'operario_principal')
    serializer_class = DobladoSerializer
    permission_classes = [permissions.IsAuthenticated]

    perform_create = RegistroImpresionViewSet.perform_create
    perform_update = RegistroImpresionViewSet.perform_update
    perform_destroy = RegistroImpresionViewSet.perform_destroy

    @action(detail=True, methods=['post'], url_path='consumir-wip', serializer_class=ConsumoWipDobladoSerializer)
    def consumir_wip(self, request, pk=None):
        doblado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consumir_rollo_entrada_doblado(doblado=doblado, usuario=request.user, **serializer.validated_data)
            return Response({'status': 'consumo WIP registrado'}, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': '...'}, status=500)

    @action(detail=True, methods=['post'], url_path='consumir-mp', serializer_class=ConsumoMpDobladoSerializer)
    def consumir_mp(self, request, pk=None):
        doblado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consumir_mp_doblado(doblado=doblado, usuario=request.user, **serializer.validated_data)
            return Response({'status': 'consumo MP registrado'}, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': '...'}, status=500)

    @action(detail=True, methods=['post'], url_path='registrar-produccion', serializer_class=ProduccionDobladoSerializer)
    def registrar_produccion(self, request, pk=None):
        doblado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            nuevo_lote = registrar_produccion_rollo_doblado(doblado=doblado, usuario=request.user, **serializer.validated_data)
            tipo_lote = "WIP" if isinstance(nuevo_lote, LoteProductoEnProceso) else "PT"
            return Response({'status': f'producción registrada ({tipo_lote})', 'lote_creado_id': nuevo_lote.lote_id, 'tipo_lote': tipo_lote, 'detalle': 'El tipo de lote se determina automáticamente según la secuencia de procesos de la OP.'}, status=status.HTTP_201_CREATED)
        except (ValidationError, ValueError, RuntimeError, ObjectDoesNotExist) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': '...'}, status=500)

# =============================================
# === VIEWSET PARA CONSUMOS ===
# =============================================

class LoteMPDisponibleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Vista para listar lotes MP disponibles para el primer proceso de la secuencia de la OP.
    Solo muestra lotes de la materia prima (sustrato) definida en la OP y que estén DISPONIBLES.
    El front-end debe asegurarse de usar este endpoint solo para el primer proceso de la secuencia.
    """
    serializer_class = LoteMateriaPrimaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        op_id = self.request.query_params.get('op_id')
        if not op_id:
            return LoteMateriaPrima.objects.none()
        try:
            op = OrdenProduccion.objects.get(id=op_id)
            return LoteMateriaPrima.objects.filter(
                materia_prima=op.sustrato,
                estado='DISPONIBLE'
            ).select_related('materia_prima', 'ubicacion')
        except OrdenProduccion.DoesNotExist:
            return LoteMateriaPrima.objects.none()

class LoteWIPDisponibleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Vista para listar lotes WIP disponibles para consumo en procesos intermedios de la OP.
    Solo muestra lotes generados por la misma orden de producción y que estén DISPONIBLES.
    El front-end debe usar este endpoint para los procesos que no son el primero ni el último de la secuencia.
    """
    serializer_class = LoteProductoEnProcesoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        op_id = self.request.query_params.get('op_id')
        if not op_id:
            return LoteProductoEnProceso.objects.none()
        return LoteProductoEnProceso.objects.filter(
            orden_produccion_id=op_id,
            estado='DISPONIBLE'
        ).select_related('producto_terminado', 'ubicacion', 'orden_produccion')

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def lote_wip_json_api(request):
    """Endpoint para listar lotes WIP disponibles de una OP via API"""
    op_id = request.query_params.get('op_id')
    if not op_id:
        return Response([], status=status.HTTP_200_OK)
    lotes = LoteProductoEnProceso.objects.filter(
        orden_produccion_id=op_id,
        estado='DISPONIBLE'
    )
    data = [
        {'id': lote.id, 'text': f"{lote.lote_id} - {lote.cantidad_actual} Kg"}
        for lote in lotes
    ]
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def lote_mp_json_api(request):
    """Endpoint para listar lotes MP disponibles de una OP via API"""
    op_id = request.query_params.get('op_id')
    if not op_id:
        return Response([], status=status.HTTP_200_OK)
    from .models import OrdenProduccion
    from inventario.models import LoteMateriaPrima
    try:
        op = OrdenProduccion.objects.get(id=op_id)
    except OrdenProduccion.DoesNotExist:
        return Response([], status=status.HTTP_200_OK)
    lotes = LoteMateriaPrima.objects.filter(
        materia_prima=op.sustrato,
        estado='DISPONIBLE'
    )
    data = [
        {'id': lote.id, 'text': f"{lote.lote_id} - {lote.cantidad_actual} Kg"}
        for lote in lotes
    ]
    return Response(data, status=status.HTTP_200_OK)

class KanbanBaseView(TemplateView):
    """Vista base para tableros Kanban de procesos."""
    template_name = None
    proceso_nombre = None
    
    def get_queryset(self):
        """Obtiene órdenes de producción para el proceso específico."""
        return OrdenProduccion.objects.filter(
            procesos_secuencia__proceso__nombre__iexact=self.proceso_nombre,
            is_active=True
        ).distinct().select_related(
            'producto'
        ).prefetch_related(
            'registros_impresion',
            'registros_refilado',
            'registros_sellado',
            'registros_doblado',
            'lotes_wip_producidos',
            'lotes_pt_producidos'
        )

    def get_orden_estado(self, orden):
        """Determina el estado actual de la orden para este proceso."""
        proceso_nombre_lower = self.proceso_nombre.lower()
        
        # Obtener registros según el tipo de proceso
        if proceso_nombre_lower == 'impresion':
            registros = orden.registros_impresion.all()
        elif proceso_nombre_lower == 'refilado':
            registros = orden.registros_refilado.all()
        elif proceso_nombre_lower == 'sellado':
            registros = orden.registros_sellado.all()
        elif proceso_nombre_lower == 'doblado':
            registros = orden.registros_doblado.all()
        else:
            return 'pendiente'
        
        if not registros.exists():
            return 'pendiente'
            
        ultimo_registro = registros.order_by('-fecha', '-hora_inicio').first()
        if not ultimo_registro:
            return 'pendiente'
            
        # Verificar si el proceso está en curso (sin hora final)
        if not ultimo_registro.hora_final:
            # Verificar si hay paros activos
            if hasattr(ultimo_registro, 'paros_impresion'):
                paro_activo = ultimo_registro.paros_impresion.filter(
                    hora_inicio_paro__isnull=False,
                    hora_final_paro__isnull=True
                ).exists()
            elif hasattr(ultimo_registro, 'paros_refilado'):
                paro_activo = ultimo_registro.paros_refilado.filter(
                    hora_inicio_paro__isnull=False,
                    hora_final_paro__isnull=True
                ).exists()
            elif hasattr(ultimo_registro, 'paros_sellado'):
                paro_activo = ultimo_registro.paros_sellado.filter(
                    hora_inicio_paro__isnull=False,
                    hora_final_paro__isnull=True
                ).exists()
            elif hasattr(ultimo_registro, 'paros_doblado'):
                paro_activo = ultimo_registro.paros_doblado.filter(
                    hora_inicio_paro__isnull=False,
                    hora_final_paro__isnull=True
                ).exists()
            else:
                paro_activo = False
                
            return 'pausado' if paro_activo else 'proceso'
            
        # Si el último registro tiene hora final, verificar la producción
        try:
            # Para impresión, calcular producción basada en lotes WIP/PT generados
            if proceso_nombre_lower == 'impresion':
                # Buscar lotes WIP/PT generados por registros de impresión de esta orden
                from inventario.models import LoteProductoEnProceso, LoteProductoTerminado
                lotes_wip = LoteProductoEnProceso.objects.filter(
                    orden_produccion=orden,
                    proceso_origen_content_type__model='registroimpresion'
                ).aggregate(total=models.Sum('cantidad_actual'))['total'] or 0
                
                lotes_pt = LoteProductoTerminado.objects.filter(
                    orden_produccion=orden,
                    proceso_origen_content_type__model='registroimpresion'
                ).aggregate(total=models.Sum('cantidad_actual'))['total'] or 0
                
                produccion_total = lotes_wip + lotes_pt
                
            elif proceso_nombre_lower == 'sellado':
                # Para sellado, usar lotes PT generados (bolsas)
                from inventario.models import LoteProductoTerminado
                produccion_total = LoteProductoTerminado.objects.filter(
                    orden_produccion=orden,
                    proceso_origen_content_type__model='sellado'
                ).aggregate(total=models.Sum('cantidad_actual'))['total'] or 0
                
            else:
                # Para refilado y doblado, usar lotes WIP/PT generados
                from inventario.models import LoteProductoEnProceso, LoteProductoTerminado
                model_name = f'{proceso_nombre_lower}'
                
                lotes_wip = LoteProductoEnProceso.objects.filter(
                    orden_produccion=orden,
                    proceso_origen_content_type__model=model_name
                ).aggregate(total=models.Sum('cantidad_actual'))['total'] or 0
                
                lotes_pt = LoteProductoTerminado.objects.filter(
                    orden_produccion=orden,
                    proceso_origen_content_type__model=model_name
                ).aggregate(total=models.Sum('cantidad_actual'))['total'] or 0
                
                produccion_total = lotes_wip + lotes_pt
                
            # Comparar con la meta de la orden
            meta = orden.cantidad_solicitada_kg or 0
            return 'terminado' if produccion_total >= meta else 'pendiente'
            
        except Exception as e:
            # En caso de error, asumir que está pendiente
            logger.warning(f"Error calculando estado de orden {orden.pk}: {e}")
            return 'pendiente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ordenes = self.get_queryset()
        
        # Clasificar órdenes por estado
        ordenes_por_estado = {
            'pendientes': [],
            'proceso': [],
            'pausadas': [],
            'terminadas': []
        }
        
        for orden in ordenes:
            estado = self.get_orden_estado(orden)
            orden.estado_actual = estado
            orden.registro_actual = getattr(orden, f'registros_{self.proceso_nombre.lower()}').order_by('-fecha', '-hora_inicio').first()
            
            # Agregar datos específicos según el proceso
            if estado == 'pendiente':
                if self.proceso_nombre.lower() != 'impresion':
                    # Para procesos que consumen WIP, buscar lotes disponibles
                    orden.lotes_wip_disponibles = orden.lotes_wip_producidos.filter(estado='DISPONIBLE')
                
                if self.proceso_nombre.lower() == 'sellado':
                    orden.proxima_meta = orden.cantidad - (orden.unidades_producidas or 0)
                elif self.proceso_nombre.lower() == 'doblado':
                    orden.medida_doblado = orden.producto.dob_medida_cm if orden.producto else None
            
            ordenes_por_estado[estado + 's' if estado != 'proceso' else 'proceso'].append(orden)
        
        context.update({
            'ordenes_pendientes': ordenes_por_estado['pendientes'],
            'ordenes_proceso': ordenes_por_estado['proceso'],
            'ordenes_pausadas': ordenes_por_estado['pausadas'],
            'ordenes_terminadas': ordenes_por_estado['terminadas'],
            'proceso': self.proceso_nombre,
            'titulo': f'Tablero {self.proceso_nombre}'
        })
        
        return context

class ImpresionKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Impresión."""
    template_name = 'produccion/kanban/impresion_kanban.html'
    proceso_nombre = 'Impresion'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse('produccion_web:registro-impresion-create')
        context['create_button_text'] = 'Nuevo Registro de Impresión'
        return context

class RefiladoKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Refilado."""
    template_name = 'produccion/kanban/refilado_kanban.html'
    proceso_nombre = 'Refilado'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse('produccion_web:registro-refilado-create')
        context['create_button_text'] = 'Nuevo Registro de Refilado'
        return context

class SelladoKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Sellado."""
    template_name = 'produccion/kanban/sellado_kanban.html'
    proceso_nombre = 'Sellado'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calcular porcentaje de avance para órdenes en proceso
        for orden in context['ordenes_proceso']:
            if orden.registro_actual and orden.cantidad:
                produccion_actual = orden.registro_actual.lotes_pt.aggregate(
                    total=models.Sum('cantidad_producida')
                )['total'] or 0
                orden.porcentaje_avance = min(100, (produccion_actual / orden.cantidad) * 100)
        
        context['create_url'] = reverse('produccion_web:registro-sellado-create')
        context['create_button_text'] = 'Nuevo Registro de Sellado'
        return context

class DobladoKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Doblado."""
    template_name = 'produccion/kanban/doblado_kanban.html'
    proceso_nombre = 'Doblado'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse('produccion_web:registro-doblado-create')
        context['create_button_text'] = 'Nuevo Registro de Doblado'
        return context

# =============================================
# === VISTAS WEB PARA FORMULARIOS ===
# =============================================

class RegistroImpresionCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear un nuevo registro de impresión."""
    model = RegistroImpresion
    form_class = RegistroImpresionForm
    template_name = 'produccion/registro_impresion_form.html'
    
    def get_success_url(self):
        return reverse('produccion_web:impresion-kanban')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['paro_formset'] = ParoImpresionFormset(self.request.POST)
            context['desperdicio_formset'] = DesperdicioImpresionFormset(self.request.POST)
            context['consumo_tinta_formset'] = ConsumoTintaImpresionFormset(self.request.POST)
            context['consumo_sustrato_formset'] = ConsumoSustratoImpresionFormset(self.request.POST)
            context['produccion_formset'] = ProduccionImpresionFormset(self.request.POST)
        else:
            context['paro_formset'] = ParoImpresionFormset()
            context['desperdicio_formset'] = DesperdicioImpresionFormset()
            context['consumo_tinta_formset'] = ConsumoTintaImpresionFormset()
            context['consumo_sustrato_formset'] = ConsumoSustratoImpresionFormset()
            context['produccion_formset'] = ProduccionImpresionFormset()
        context['page_title'] = 'Nuevo Registro de Impresión'
        context['cancel_url'] = reverse('produccion_web:impresion-kanban')
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        paro_formset = context['paro_formset']
        desperdicio_formset = context['desperdicio_formset']
        consumo_tinta_formset = context['consumo_tinta_formset']
        consumo_sustrato_formset = context['consumo_sustrato_formset']
        produccion_formset = context['produccion_formset']
        
        if (paro_formset.is_valid() and desperdicio_formset.is_valid() and
            consumo_tinta_formset.is_valid() and consumo_sustrato_formset.is_valid() and
            produccion_formset.is_valid()):
            
            with transaction.atomic():
                self.object = form.save()
                
                # Save related formsets
                paro_formset.instance = self.object
                paro_formset.save()
                
                desperdicio_formset.instance = self.object
                desperdicio_formset.save()
                
                consumo_tinta_formset.instance = self.object
                consumo_tinta_formset.save()
                
                consumo_sustrato_formset.instance = self.object
                consumo_sustrato_formset.save()
                
                # Save production formset with custom logic
                produccion_formset.registro_impresion = self.object
                produccion_formset.save()
            
            messages.success(self.request, 'Registro de impresión creado exitosamente.')
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class RegistroRefiladoCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear un nuevo registro de refilado."""
    model = Refilado
    form_class = RegistroRefiladoForm
    template_name = 'produccion/registro_refilado_form.html'
    success_url = reverse_lazy('produccion_web:refilado-kanban')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['paro_formset'] = ParoRefiladoFormset(self.request.POST)
            context['consumo_wip_formset'] = ConsumoWipRefiladoFormset(self.request.POST)
            context['produccion_formset'] = ProduccionRefiladoFormSet(self.request.POST)
        else:
            context['paro_formset'] = ParoRefiladoFormset()
            context['consumo_wip_formset'] = ConsumoWipRefiladoFormset()
            context['produccion_formset'] = ProduccionRefiladoFormSet()
        context['page_title'] = 'Nuevo Registro de Refilado'
        context['cancel_url'] = reverse('produccion_web:refilado-kanban')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        paro_formset = context['paro_formset']
        consumo_wip_formset = context['consumo_wip_formset']
        produccion_formset = context['produccion_formset']

        if (paro_formset.is_valid() and consumo_wip_formset.is_valid() and 
            produccion_formset.is_valid()):
            
            with transaction.atomic():
                self.object = form.save()
                
                # Save related formsets
                paro_formset.instance = self.object
                paro_formset.save()
                
                consumo_wip_formset.instance = self.object
                consumo_wip_formset.save()
                
                # Save production formset with custom logic
                produccion_formset.registro_refilado = self.object
                produccion_formset.save()
            
            messages.success(self.request, 'Registro de refilado creado exitosamente.')
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

class RegistroSelladoCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear un nuevo registro de sellado."""
    model = Sellado
    form_class = RegistroSelladoForm
    template_name = 'produccion/registro_sellado_form.html'
    success_url = reverse_lazy('produccion_web:sellado-kanban')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['paro_formset'] = ParoSelladoFormset(self.request.POST)
            context['consumo_wip_formset'] = ConsumoWipSelladoFormset(self.request.POST)
            context['produccion_formset'] = ProduccionSelladoFormSet(self.request.POST)
        else:
            context['paro_formset'] = ParoSelladoFormset()
            context['consumo_wip_formset'] = ConsumoWipSelladoFormset()
            context['produccion_formset'] = ProduccionSelladoFormSet()
        context['page_title'] = 'Nuevo Registro de Sellado'
        context['cancel_url'] = reverse('produccion_web:sellado-kanban')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        paro_formset = context['paro_formset']
        consumo_wip_formset = context['consumo_wip_formset']
        produccion_formset = context['produccion_formset']

        if (paro_formset.is_valid() and consumo_wip_formset.is_valid() and 
            produccion_formset.is_valid()):
            
            with transaction.atomic():
                self.object = form.save()
                
                # Save related formsets
                paro_formset.instance = self.object
                paro_formset.save()
                
                consumo_wip_formset.instance = self.object
                consumo_wip_formset.save()
                
                # Save production formset with custom logic
                produccion_formset.registro_sellado = self.object
                produccion_formset.save()
            
            messages.success(self.request, 'Registro de sellado creado exitosamente.')
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

class RegistroDobladoCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear un nuevo registro de doblado."""
    model = Doblado
    form_class = RegistroDobladoForm
    template_name = 'produccion/registro_doblado_form.html'
    success_url = reverse_lazy('produccion_web:doblado-kanban')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['paro_formset'] = ParoDobladoFormset(self.request.POST)
            context['consumo_wip_formset'] = ConsumoWipDobladoFormset(self.request.POST)
            context['produccion_formset'] = ProduccionDobladoFormSet(self.request.POST)
        else:
            context['paro_formset'] = ParoDobladoFormset()
            context['consumo_wip_formset'] = ConsumoWipDobladoFormset()
            context['produccion_formset'] = ProduccionDobladoFormSet()
        context['page_title'] = 'Nuevo Registro de Doblado'
        context['cancel_url'] = reverse('produccion_web:doblado-kanban')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        paro_formset = context['paro_formset']
        consumo_wip_formset = context['consumo_wip_formset']
        produccion_formset = context['produccion_formset']

        if (paro_formset.is_valid() and consumo_wip_formset.is_valid() and 
            produccion_formset.is_valid()):
            
            with transaction.atomic():
                self.object = form.save()
                
                # Save related formsets
                paro_formset.instance = self.object
                paro_formset.save()
                
                consumo_wip_formset.instance = self.object
                consumo_wip_formset.save()
                
                # Save production formset with custom logic
                produccion_formset.registro_doblado = self.object
                produccion_formset.save()
            
            messages.success(self.request, 'Registro de doblado creado exitosamente.')
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

class OrdenProduccionCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear una nueva orden de producción."""
    model = OrdenProduccion
    form_class = OrdenProduccionForm
    template_name = 'produccion/orden_produccion_form.html'
    success_url = reverse_lazy('produccion_web:orden-produccion-list')
    
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        form.instance.actualizado_por = self.request.user
        messages.success(self.request, 'Orden de producción creada exitosamente.')
        return super().form_valid(form)


class OrdenProduccionUpdateView(LoginRequiredMixin, UpdateView):
    """Vista para actualizar una orden de producción."""
    model = OrdenProduccion
    form_class = OrdenProduccionForm
    template_name = 'produccion/orden_produccion_form.html'
    
    def get_queryset(self):
        return OrdenProduccion.objects.filter(is_active=True)
    
    def get_success_url(self):
        return reverse('produccion_web:orden-produccion-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.actualizado_por = self.request.user
        messages.success(self.request, 'Orden de producción actualizada exitosamente.')
        return super().form_valid(form)