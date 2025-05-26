# produccion/views.py

import logging
from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.db import models, transaction
from django.db.models import Q, F, Case, When, Value, BooleanField
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from configuracion.models import Proceso

# Importar modelos de esta app
from .models import OrdenProduccion, RegistroImpresion, Refilado, Sellado, Doblado

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
        except Exception as e: logger.exception(...); return Response({'error': 'Error interno'}, status=500)

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
        registros = getattr(orden, f'registros_{self.proceso_nombre.lower()}').all()
        
        if not registros.exists():
            return 'pendiente'
            
        ultimo_registro = registros.order_by('-fecha', '-hora_inicio').first()
        if not ultimo_registro:
            return 'pendiente'
            
        if not ultimo_registro.hora_final:
            # Si tiene paro sin finalizar, está pausado
            paro_activo = ultimo_registro.paros.filter(
                hora_inicio_paro__isnull=False,
                hora_final_paro__isnull=True
            ).exists()
            return 'pausado' if paro_activo else 'proceso'
            
        # Si el último registro tiene hora final, revisar si hay más por hacer
        if self.proceso_nombre.lower() == 'sellado':
            produccion_total = ultimo_registro.bolsas_producidas or 0
            meta = orden.cantidad or 0
        else:
            produccion_total = sum(r.kg_producidos or 0 for r in registros)
            meta = orden.kg_total or 0
            
        return 'terminado' if produccion_total >= meta else 'pendiente'

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

class RefiladoKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Refilado."""
    template_name = 'produccion/kanban/refilado_kanban.html'
    proceso_nombre = 'Refilado'

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
        return context

class DobladoKanbanView(KanbanBaseView):
    """Vista Kanban para proceso de Doblado."""
    template_name = 'produccion/kanban/doblado_kanban.html'
    proceso_nombre = 'Doblado'