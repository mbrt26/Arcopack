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
from django.views.generic import ListView, TemplateView, DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.core.paginator import Paginator

# Importar modelos y serializers necesarios
from .models import (
    LoteMateriaPrima, LoteProductoEnProceso, LoteProductoTerminado, 
    MateriaPrima, MovimientoInventario
)
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

class MateriaPrimaListView(ListView):
    model = MateriaPrima
    template_name = 'inventario/materia_prima_list.html'
    context_object_name = 'materias_primas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # You can add filtering/sorting here if needed
        return queryset.order_by('codigo')


class MateriaPrimaCreateView(CreateView):
    model = MateriaPrima
    template_name = 'inventario/materia_prima_form.html'
    fields = ['codigo', 'nombre', 'descripcion', 'categoria', 'unidad_medida', 
              'stock_minimo', 'stock_maximo', 'proveedor_preferido', 'requiere_lote']
    success_url = reverse_lazy('inventario_web:materia-prima-list')

    def form_valid(self, form):
        messages.success(self.request, 'Materia prima creada exitosamente.')
        return super().form_valid(form)

class MateriaPrimaUpdateView(UpdateView):
    model = MateriaPrima
    template_name = 'inventario/materia_prima_form.html'
    fields = ['codigo', 'nombre', 'descripcion', 'categoria', 'unidad_medida', 
              'stock_minimo', 'stock_maximo', 'proveedor_preferido', 'requiere_lote']
    success_url = reverse_lazy('inventario_web:materia-prima-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Materia prima actualizada correctamente.')
        return super().form_valid(form)


class LoteListView(LoginRequiredMixin, TemplateView):
    """Vista para listar lotes de inventario con pestañas por tipo."""
    template_name = 'inventario/lote_list.html'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de búsqueda
        search_query = self.request.GET.get('q', '')
        estado_filter = self.request.GET.get('estado', '')
        ubicacion_filter = self.request.GET.get('ubicacion', '')
        
        # Filtrar lotes de materia prima
        mp_lotes = LoteMateriaPrima.objects.select_related(
            'materia_prima', 'ubicacion', 'proveedor'
        ).order_by('-fecha_recepcion')
        
        # Aplicar filtros si existen
        if search_query:
            mp_lotes = mp_lotes.filter(
                Q(lote_id__icontains=search_query) |
                Q(materia_prima__codigo__icontains=search_query) |
                Q(materia_prima__nombre__icontains=search_query)
            )
        
        if estado_filter:
            mp_lotes = mp_lotes.filter(estado=estado_filter)
            
        if ubicacion_filter:
            mp_lotes = mp_lotes.filter(ubicacion_id=ubicacion_filter)
        
        # Paginar resultados
        paginator = Paginator(mp_lotes, self.paginate_by)
        page = self.request.GET.get('page')
        mp_lotes_paginated = paginator.get_page(page)
        
        context.update({
            'mp_lotes': mp_lotes_paginated,
            'search_query': search_query,
            'estado_filter': estado_filter,
            'ubicacion_filter': ubicacion_filter,
            'estados_lote': LoteMateriaPrima.ESTADO_LOTE_CHOICES,
        })
        
        return context


class MovimientoListView(LoginRequiredMixin, ListView):
    """Vista para listar movimientos de inventario."""
    model = MovimientoInventario
    template_name = 'inventario/movimiento_list.html'
    context_object_name = 'movimientos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = MovimientoInventario.objects.select_related(
            'lote_content_type', 'ubicacion_origen', 'ubicacion_destino', 'usuario', 'unidad_medida'
        ).order_by('-timestamp')
        
        # Filtros
        tipo_movimiento = self.request.GET.get('tipo_movimiento')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if tipo_movimiento:
            queryset = queryset.filter(tipo_movimiento=tipo_movimiento)
            
        if fecha_desde:
            queryset = queryset.filter(timestamp__date__gte=fecha_desde)
            
        if fecha_hasta:
            queryset = queryset.filter(timestamp__date__lte=fecha_hasta)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'tipo_movimiento': self.request.GET.get('tipo_movimiento', ''),
            'fecha_desde': self.request.GET.get('fecha_desde', ''),
            'fecha_hasta': self.request.GET.get('fecha_hasta', ''),
            'tipos_movimiento': MovimientoInventario.TIPO_MOVIMIENTO_CHOICES,
            'tipos_entrada': MovimientoInventario.TIPOS_ENTRADA,
            'tipos_salida': MovimientoInventario.TIPOS_SALIDA,
        })
        return context


class MateriaPrimaDetailView(LoginRequiredMixin, DetailView):
    """Vista para ver el detalle de una materia prima."""
    model = MateriaPrima
    template_name = 'inventario/materia_prima_detail.html'
    context_object_name = 'materia_prima'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener los lotes de la materia prima
        context['lotes'] = LoteMateriaPrima.objects.filter(
            materia_prima=self.object
        ).order_by('-fecha_recepcion')
        return context


class LoteCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear un nuevo lote de materia prima."""
    model = LoteMateriaPrima
    template_name = 'inventario/lote_form.html'
    fields = ['materia_prima', 'lote_id', 'cantidad_recibida', 'ubicacion', 
              'proveedor', 'fecha_recepcion', 'fecha_vencimiento', 'observaciones']
    success_url = reverse_lazy('inventario_web:lote-list')

    def get_initial(self):
        initial = super().get_initial()
        # Si se proporciona una materia prima en la URL, pre-seleccionarla
        materia_prima_id = self.request.GET.get('materia_prima')
        if materia_prima_id:
            initial['materia_prima'] = materia_prima_id
        return initial

    def form_valid(self, form):
        # Establecer los valores iniciales del lote
        form.instance.estado = 'DISPONIBLE'
        form.instance.cantidad_actual = form.instance.cantidad_recibida
        form.instance.creado_por = self.request.user
        messages.success(self.request, 'Lote creado exitosamente.')
        return super().form_valid(form)
