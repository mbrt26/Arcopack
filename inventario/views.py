# inventario/views.py

import logging
from decimal import Decimal # <<< AÑADIDO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
# Imports de Django para la consulta ORM
from django.db.models import Sum, Count, F, Value, CharField, DecimalField # <<< AÑADIDO DecimalField
from django.db.models.functions import Coalesce
from django.core.exceptions import ObjectDoesNotExist # Para manejo de errores
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages

# Importar modelos y serializers necesarios
from .models import LoteMateriaPrima, LoteProductoEnProceso, LoteProductoTerminado, MateriaPrima
from .serializers import StockItemSerializer
# from configuracion.models import UnidadMedida # Ya no se necesita aquí con el fix anterior

logger = logging.getLogger(__name__)


# Estados de lote considerados como stock disponible o en espera
ESTADOS_STOCK_VALIDO = ['DISPONIBLE', 'CUARENTENA']

class StockActualAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        logger.info(f"Usuario {request.user} solicitando stock actual.")
        try:
            # 1. Query MP con campos renombrados
            stock_mp = LoteMateriaPrima.objects.filter(
                estado__in=ESTADOS_STOCK_VALIDO
            ).values(
                # --- Renombrados con agg_ ---
                agg_item_id=F('materia_prima__id'),
                agg_item_codigo=F('materia_prima__codigo'),
                agg_item_nombre=F('materia_prima__nombre'),
                agg_ubicacion_id=F('ubicacion__id'),
                agg_ubicacion_codigo=F('ubicacion__codigo'),
                agg_ubicacion_nombre=F('ubicacion__nombre'),
                agg_unidad_medida_codigo=F('materia_prima__unidad_medida__codigo')
                # --------------------------
            ).annotate(
                tipo_item=Value('MP', output_field=CharField()),
                cantidad_total=Coalesce(Sum('cantidad_actual'), Decimal('0.0'), output_field=DecimalField()),
                numero_lotes=Count('id')
            ).filter(cantidad_total__gt=0).order_by('agg_ubicacion_codigo', 'agg_item_codigo') # Ordenar por los nuevos nombres

            # 2. Query WIP con campos renombrados
            stock_wip = LoteProductoEnProceso.objects.filter(
                estado__in=ESTADOS_STOCK_VALIDO
            ).values(
                # --- Renombrados con agg_ ---
                agg_item_id=F('producto_terminado__id'),
                agg_item_codigo=F('producto_terminado__codigo'),
                agg_item_nombre=F('producto_terminado__nombre'),
                agg_ubicacion_id=F('ubicacion__id'),
                agg_ubicacion_codigo=F('ubicacion__codigo'),
                agg_ubicacion_nombre=F('ubicacion__nombre'),
                agg_unidad_medida_codigo=F('unidad_medida_primaria__codigo')
                # --------------------------
            ).annotate(
                tipo_item=Value('WIP', output_field=CharField()),
                cantidad_total=Coalesce(Sum('cantidad_actual'), Decimal('0.0'), output_field=DecimalField()),
                numero_lotes=Count('id')
            ).filter(cantidad_total__gt=0).order_by('agg_ubicacion_codigo', 'agg_item_codigo')

            # 3. Query PT con campos renombrados
            stock_pt = LoteProductoTerminado.objects.filter(
                estado__in=ESTADOS_STOCK_VALIDO
            ).values(
                # --- Renombrados con agg_ ---
                agg_item_id=F('producto_terminado__id'),
                agg_item_codigo=F('producto_terminado__codigo'),
                agg_item_nombre=F('producto_terminado__nombre'),
                agg_ubicacion_id=F('ubicacion__id'),
                agg_ubicacion_codigo=F('ubicacion__codigo'),
                agg_ubicacion_nombre=F('ubicacion__nombre'),
                agg_unidad_medida_codigo=F('producto_terminado__unidad_medida__codigo')
                # --------------------------
            ).annotate(
                tipo_item=Value('PT', output_field=CharField()),
                cantidad_total=Coalesce(Sum('cantidad_actual'), Decimal('0.0'), output_field=DecimalField()),
                numero_lotes=Count('id')
            ).filter(cantidad_total__gt=0).order_by('agg_ubicacion_codigo', 'agg_item_codigo')

            # 4. Combinar resultados
            resultados_combinados = list(stock_mp) + list(stock_wip) + list(stock_pt)

            # 5. Serializar - ¡Necesita ajustarse al nuevo nombre de campos!
            serializer = StockItemSerializer(resultados_combinados, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.exception(f"Error inesperado al calcular stock actual: {e}")
            return Response({"error": "Error interno al procesar la solicitud de stock."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MateriaPrimaCreateView(CreateView):
    model = MateriaPrima
    template_name = 'inventario/materia_prima_form.html'
    fields = ['codigo', 'nombre', 'descripcion', 'categoria', 'unidad_medida', 
              'stock_minimo', 'stock_maximo', 'proveedor_preferido', 'requiere_lote']
    success_url = reverse_lazy('inventario:materia-prima-list')

    def form_valid(self, form):
        messages.success(self.request, 'Materia prima creada exitosamente.')
        return super().form_valid(form)

class MateriaPrimaUpdateView(UpdateView):
    model = MateriaPrima
    template_name = 'inventario/materia_prima_form.html'
    fields = ['codigo', 'nombre', 'descripcion', 'categoria', 'unidad_medida', 
              'stock_minimo', 'stock_maximo', 'proveedor_preferido', 'requiere_lote']
    success_url = reverse_lazy('inventario:materia-prima-list')

    def form_valid(self, form):
        messages.success(self.request, 'Materia prima actualizada exitosamente.')
        return super().form_valid(form)
