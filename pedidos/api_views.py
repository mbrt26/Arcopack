# pedidos/api_views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import Pedido, LineaPedido, SeguimientoPedido
from .serializers import (
    PedidoListSerializer, PedidoDetailSerializer, PedidoCreateSerializer,
    LineaPedidoSerializer, SeguimientoPedidoSerializer,
    CambiarEstadoPedidoSerializer, EstadisticasPedidosSerializer,
    ResumenPedidoSerializer
)
from .utils import PedidosUtils, NotificacionesPedidos
from productos.models import ProductoTerminado


class PedidoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de pedidos"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'prioridad', 'cliente']
    search_fields = ['numero_pedido', 'cliente__razon_social', 'pedido_cliente_referencia']
    ordering_fields = ['fecha_pedido', 'fecha_compromiso', 'valor_total', 'numero_pedido']
    ordering = ['-fecha_pedido']

    def get_queryset(self):
        return Pedido.objects.select_related('cliente', 'creado_por').prefetch_related(
            'lineas__producto', 'seguimientos'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return PedidoListSerializer
        elif self.action == 'create':
            return PedidoCreateSerializer
        else:
            return PedidoDetailSerializer

    def perform_create(self, serializer):
        # Generar número de pedido automáticamente
        numero_pedido = PedidosUtils.generar_numero_pedido()
        serializer.save(
            numero_pedido=numero_pedido,
            creado_por=self.request.user,
            actualizado_por=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(actualizado_por=self.request.user)

    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """Cambia el estado de un pedido"""
        pedido = self.get_object()
        serializer = CambiarEstadoPedidoSerializer(data=request.data)
        
        if serializer.is_valid():
            nuevo_estado = serializer.validated_data['nuevo_estado']
            observaciones = serializer.validated_data.get('observaciones', '')
            
            # Validar transición de estado
            if not PedidosUtils.validar_transicion_estado(pedido.estado, nuevo_estado):
                return Response(
                    {'error': f'No se puede cambiar de {pedido.get_estado_display()} a {dict(Pedido.ESTADO_CHOICES)[nuevo_estado]}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            estado_anterior = pedido.estado
            pedido.estado = nuevo_estado
            
            # Actualizar campos específicos según el estado
            if nuevo_estado == 'FACTURADO':
                pedido.numero_factura = serializer.validated_data.get('numero_factura')
                pedido.fecha_facturacion = serializer.validated_data.get('fecha_facturacion')
            elif nuevo_estado == 'ENTREGADO':
                pedido.fecha_entrega_real = timezone.now().date()
            
            pedido.actualizado_por = request.user
            pedido.save()
            
            # Crear seguimiento
            SeguimientoPedido.objects.create(
                pedido=pedido,
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado,
                usuario=request.user,
                observaciones=observaciones
            )
            
            # Enviar notificación
            NotificacionesPedidos.notificar_cambio_estado(pedido, estado_anterior, request.user)
            
            return Response({
                'mensaje': f'Estado cambiado exitosamente a {pedido.get_estado_display()}',
                'estado_anterior': estado_anterior,
                'estado_nuevo': nuevo_estado
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtiene estadísticas de pedidos"""
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        
        # Convertir strings a fechas si se proporcionan
        if fecha_inicio:
            from datetime import datetime
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        if fecha_fin:
            from datetime import datetime
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        stats = PedidosUtils.calcular_estadisticas_pedidos(fecha_inicio, fecha_fin)
        serializer = EstadisticasPedidosSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Obtiene resumen ejecutivo de pedidos"""
        periodo = request.query_params.get('periodo', 'mes')  # mes, trimestre, año
        hoy = timezone.now().date()
        
        if periodo == 'mes':
            fecha_inicio = hoy.replace(day=1)
            mes_anterior = (fecha_inicio - timedelta(days=1)).replace(day=1)
            fecha_fin_anterior = fecha_inicio - timedelta(days=1)
        elif periodo == 'trimestre':
            # Lógica para trimestre
            mes_actual = hoy.month
            trimestre_inicio = ((mes_actual - 1) // 3) * 3 + 1
            fecha_inicio = hoy.replace(month=trimestre_inicio, day=1)
            mes_anterior = trimestre_inicio - 3 if trimestre_inicio > 3 else 9
            año_anterior = hoy.year if trimestre_inicio > 3 else hoy.year - 1
            fecha_anterior = hoy.replace(year=año_anterior, month=mes_anterior, day=1)
            fecha_fin_anterior = fecha_inicio - timedelta(days=1)
        else:  # año
            fecha_inicio = hoy.replace(month=1, day=1)
            fecha_anterior = fecha_inicio.replace(year=hoy.year - 1)
            fecha_fin_anterior = fecha_inicio - timedelta(days=1)
        
        # Estadísticas período actual
        pedidos_actuales = Pedido.objects.filter(fecha_pedido__gte=fecha_inicio)
        
        stats_actuales = pedidos_actuales.aggregate(
            total_pedidos=Count('id'),
            valor_total=Sum('valor_total')
        )
        
        # Contar por estados
        confirmados = pedidos_actuales.filter(estado='CONFIRMADO').count()
        en_produccion = pedidos_actuales.filter(estado='EN_PRODUCCION').count()
        pendientes_facturar = pedidos_actuales.filter(estado='PENDIENTE_FACTURAR').count()
        facturados = pedidos_actuales.filter(estado='FACTURADO').count()
        
        # Estadísticas período anterior para calcular crecimiento
        if 'fecha_anterior' in locals():
            pedidos_anteriores = Pedido.objects.filter(
                fecha_pedido__gte=fecha_anterior,
                fecha_pedido__lte=fecha_fin_anterior
            )
            valor_anterior = pedidos_anteriores.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
            
            if valor_anterior > 0:
                crecimiento = ((stats_actuales['valor_total'] or 0) - valor_anterior) / valor_anterior * 100
            else:
                crecimiento = 0 if stats_actuales['valor_total'] == 0 else 100
        else:
            crecimiento = None
        
        resumen = {
            'periodo': periodo,
            'total_pedidos': stats_actuales['total_pedidos'] or 0,
            'valor_total': stats_actuales['valor_total'] or 0,
            'pedidos_confirmados': confirmados,
            'pedidos_en_produccion': en_produccion,
            'pedidos_pendientes_facturar': pendientes_facturar,
            'pedidos_facturados': facturados,
            'crecimiento_porcentual': crecimiento
        }
        
        serializer = ResumenPedidoSerializer(resumen)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def alertas(self, request):
        """Obtiene alertas de pedidos"""
        alertas = PedidosUtils.obtener_alertas_produccion()
        return Response({'alertas': alertas})

    @action(detail=False, methods=['get'])
    def vencidos(self, request):
        """Obtiene pedidos vencidos"""
        pedidos_vencidos = PedidosUtils.obtener_pedidos_vencidos()
        serializer = PedidoListSerializer(pedidos_vencidos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def proximos_vencer(self, request):
        """Obtiene pedidos próximos a vencer"""
        dias = int(request.query_params.get('dias', 7))
        pedidos = PedidosUtils.obtener_pedidos_proximos_vencer(dias)
        serializer = PedidoListSerializer(pedidos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def imprimir(self, request, pk=None):
        """Genera datos para impresión del pedido"""
        pedido = self.get_object()
        serializer = PedidoDetailSerializer(pedido)
        
        # Agregar información adicional para impresión
        data = serializer.data
        data['fecha_impresion'] = timezone.now()
        data['impreso_por'] = request.user.username
        
        return Response(data)


class LineaPedidoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de líneas de pedido"""
    serializer_class = LineaPedidoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        pedido_id = self.request.query_params.get('pedido_id')
        if pedido_id:
            return LineaPedido.objects.filter(pedido_id=pedido_id).select_related('producto')
        return LineaPedido.objects.select_related('producto', 'pedido')

    def perform_create(self, serializer):
        linea = serializer.save()
        # Recalcular total del pedido
        linea.pedido.calcular_total()
        linea.pedido.save()

    def perform_update(self, serializer):
        linea = serializer.save()
        # Recalcular total del pedido
        linea.pedido.calcular_total()
        linea.pedido.save()

    def perform_destroy(self, instance):
        pedido = instance.pedido
        instance.delete()
        # Recalcular total del pedido
        pedido.calcular_total()
        pedido.save()


class ProductoInfoAPIView(APIView):
    """API para obtener información de productos para pedidos"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        producto_id = request.query_params.get('producto_id')
        if not producto_id:
            return Response({'error': 'producto_id es requerido'}, status=400)
        
        try:
            producto = ProductoTerminado.objects.get(id=producto_id)
            return Response({
                'id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio_venta': producto.precio_venta,
                'unidad_medida': producto.unidad_medida,
                'stock_disponible': getattr(producto, 'stock_disponible', 0)
            })
        except ProductoTerminado.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=404)