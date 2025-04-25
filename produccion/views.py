# produccion/views.py

import logging
from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError

# Importar modelos de esta app
from .models import OrdenProduccion, RegistroImpresion, Refilado, Sellado, Doblado

# Importar Serializers de esta app
from .serializers import (
    OrdenProduccionSerializer,
    RegistroImpresionSerializer, ConsumoImpresionSerializer, ProduccionImpresionSerializer,
    RefiladoSerializer, ConsumoWipRefiladoSerializer, ConsumoMpRefiladoSerializer, ProduccionRefiladoSerializer,
    SelladoSerializer, ConsumoWipSelladoSerializer, ConsumoMpSelladoSerializer, ProduccionSelladoSerializer,
    DobladoSerializer, ConsumoWipDobladoSerializer, ConsumoMpDobladoSerializer, ProduccionDobladoSerializer,
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
from inventario.models import LoteProductoEnProceso, LoteProductoTerminado # Para isinstance

logger = logging.getLogger(__name__)
User = get_user_model()

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
    """ViewSet para gestionar Registros de Impresión y sus acciones."""
    queryset = RegistroImpresion.objects.filter(is_active=True).select_related(
        'orden_produccion', 'maquina', 'operario_principal', 'tipo_tinta_principal',
        'aprobado_por', 'orden_produccion__producto', 'orden_produccion__cliente', 'anilox'
    )
    serializer_class = RegistroImpresionSerializer
    permission_classes = [permissions.IsAuthenticated]

    # --- Métodos Estándar ---
    def perform_create(self, serializer): serializer.save(creado_por=self.request.user, actualizado_por=self.request.user)
    def perform_update(self, serializer): serializer.save(actualizado_por=self.request.user)
    def perform_destroy(self, instance): instance.is_active = False; instance.save(user=self.request.user)

    # --- Acciones Personalizadas ---
    @action(detail=True, methods=['post'], url_path='consumir-sustrato', serializer_class=ConsumoImpresionSerializer)
    def consumir_sustrato(self, request, pk=None):
        """Endpoint para registrar consumo de sustrato (MP)."""
        registro_impresion = self.get_object()
        serializer = self.get_serializer(data=request.data) # Usa el serializer definido en @action
        serializer.is_valid(raise_exception=True)
        try:
            lote_actualizado = consumir_sustrato_impresion(
                registro_impresion=registro_impresion, **serializer.validated_data, usuario=request.user
            )
            return Response({ 'status': 'consumo registrado', 'lote_id': lote_actualizado.lote_id, 'cantidad_restante': lote_actualizado.cantidad_actual }, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': 'Error interno'}, status=500)

    @action(detail=True, methods=['post'], url_path='registrar-produccion', serializer_class=ProduccionImpresionSerializer)
    def registrar_produccion(self, request, pk=None):
        """Endpoint para registrar producción de rollo WIP/PT."""
        registro_impresion = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            nuevo_lote = registrar_produccion_rollo_impreso(
                registro_impresion=registro_impresion, **serializer.validated_data, usuario=request.user
            )
            tipo_lote = "WIP" if isinstance(nuevo_lote, LoteProductoEnProceso) else "PT"
            if not registro_impresion.produccion_registrada_en_inventario: # Marcar flag (lógica demo)
                registro_impresion.produccion_registrada_en_inventario = True
                registro_impresion.save(update_fields=['produccion_registrada_en_inventario'], user=request.user)
            return Response({'status': f'producción registrada ({tipo_lote})', 'lote_creado_id': nuevo_lote.lote_id, 'tipo_lote': tipo_lote}, status=status.HTTP_201_CREATED)
        except (ValidationError, ValueError, RuntimeError, ObjectDoesNotExist) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': 'Error interno'}, status=500)

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
            # Marcar flag si Refilado tuviera uno
            return Response({'status': f'producción registrada ({tipo_lote})', 'lote_creado_id': nuevo_lote.lote_id, 'tipo_lote': tipo_lote}, status=status.HTTP_201_CREATED)
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
            # Marcar flag si Sellado tuviera uno
            return Response({'status': f'producción registrada ({tipo_lote})', 'lote_creado_id': nuevo_lote.lote_id, 'tipo_lote': tipo_lote}, status=status.HTTP_201_CREATED)
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
            # Marcar flag si Doblado tuviera uno
            return Response({'status': f'producción registrada ({tipo_lote})', 'lote_creado_id': nuevo_lote.lote_id, 'tipo_lote': tipo_lote}, status=status.HTTP_201_CREATED)
        except (ValidationError, ValueError, RuntimeError, ObjectDoesNotExist) as e: raise DRFValidationError(str(e))
        except Exception as e: logger.exception(...); return Response({'error': '...'}, status=500)