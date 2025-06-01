# produccion/views/api.py
"""
ViewSets y APIs para los diferentes procesos de producción.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models import (
    RegistroImpresion, Refilado, Sellado, Doblado
)
from inventario.models import LoteMateriaPrima, LoteProductoEnProceso
from ..serializers import (
    RegistroImpresionSerializer, RefiladoSerializer,
    SelladoSerializer, DobladoSerializer
)

# =============================================
# === VIEWSET PARA SELLADO ===
# =============================================
class SelladoViewSet(viewsets.ModelViewSet):
    """ViewSet para el modelo Sellado."""
    queryset = Sellado.objects.filter(is_active=True)
    serializer_class = SelladoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        orden_id = self.request.query_params.get('orden_id')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        
        if orden_id:
            queryset = queryset.filter(orden_produccion_id=orden_id)
        if fecha_inicio:
            queryset = queryset.filter(fecha_registro__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_registro__lte=fecha_fin)
            
        return queryset.select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        )

# =============================================
# === VIEWSET PARA DOBLADO ===
# =============================================
class DobladoViewSet(viewsets.ModelViewSet):
    """ViewSet para el modelo Doblado."""
    queryset = Doblado.objects.filter(is_active=True)
    serializer_class = DobladoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        orden_id = self.request.query_params.get('orden_id')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        
        if orden_id:
            queryset = queryset.filter(orden_produccion_id=orden_id)
        if fecha_inicio:
            queryset = queryset.filter(fecha_registro__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_registro__lte=fecha_fin)
            
        return queryset.select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        )

# =============================================
# === VIEWSET PARA CONSUMOS ===
# =============================================

class LoteMPDisponibleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para lotes de materia prima disponibles."""
    queryset = LoteMateriaPrima.objects.filter(cantidad_actual__gt=0, estado='DISPONIBLE')
    serializer_class = None  # Necesitará ser creado o usar uno genérico
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        producto_id = self.request.query_params.get('producto_id')
        ubicacion = self.request.query_params.get('ubicacion')
        
        if producto_id:
            queryset = queryset.filter(materia_prima__productos_relacionados__id=producto_id)
        if ubicacion:
            queryset = queryset.filter(ubicacion__codigo=ubicacion)
            
        return queryset.select_related('materia_prima', 'ubicacion')

class LoteWIPDisponibleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para lotes WIP disponibles."""
    queryset = LoteProductoEnProceso.objects.filter(cantidad_actual__gt=0, estado='DISPONIBLE')
    serializer_class = None  # Necesitará ser creado o usar uno genérico
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        producto_id = self.request.query_params.get('producto_id')
        ubicacion = self.request.query_params.get('ubicacion')
        proceso_origen = self.request.query_params.get('proceso_origen')
        
        if producto_id:
            queryset = queryset.filter(producto_terminado_id=producto_id)
        if ubicacion:
            queryset = queryset.filter(ubicacion__codigo=ubicacion)
        if proceso_origen:
            queryset = queryset.filter(proceso_origen_content_type__model=proceso_origen)
            
        return queryset.select_related('producto_terminado', 'ubicacion')

# =============================================
# === API FUNCTIONS FOR LOTES ===
# =============================================

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
    ).select_related('producto_terminado', 'ubicacion')
    
    data = [
        {
            'id': lote.id, 
            'text': f"{lote.lote_id} - {lote.cantidad_actual} Kg"
        }
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
    
    lotes = LoteMateriaPrima.objects.filter(
        orden_produccion_id=op_id,
        estado='DISPONIBLE'
    ).select_related('materia_prima', 'ubicacion')
    
    data = [
        {
            'id': lote.id, 
            'text': f"{lote.lote_id} - {lote.cantidad_actual} {lote.materia_prima.unidad_medida.codigo}"
        }
        for lote in lotes
    ]
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def lotes_mp_por_producto(request, producto_id):
    """API endpoint para obtener lotes de MP disponibles por producto."""
    try:
        lotes = LoteMateriaPrima.objects.filter(
            materia_prima__productos_relacionados__id=producto_id,
            cantidad_actual__gt=0,
            estado='DISPONIBLE'
        ).select_related('materia_prima', 'ubicacion')
        
        data = [
            {
                'id': lote.id,
                'lote_id': lote.lote_id,
                'cantidad_actual': float(lote.cantidad_actual),
                'materia_prima': lote.materia_prima.nombre,
                'ubicacion': lote.ubicacion.nombre if lote.ubicacion else None
            }
            for lote in lotes
        ]
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def lotes_wip_por_producto(request, producto_id):
    """API endpoint para obtener lotes WIP disponibles por producto."""
    try:
        lotes = LoteProductoEnProceso.objects.filter(
            producto_terminado_id=producto_id,
            cantidad_actual__gt=0,
            estado='DISPONIBLE'
        ).select_related('producto_terminado', 'ubicacion')
        
        data = [
            {
                'id': lote.id,
                'lote_id': lote.lote_id,
                'cantidad_actual': float(lote.cantidad_actual),
                'producto': lote.producto_terminado.nombre,
                'ubicacion': lote.ubicacion.nombre if lote.ubicacion else None
            }
            for lote in lotes
        ]
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)