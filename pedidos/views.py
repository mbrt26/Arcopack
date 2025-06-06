# pedidos/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.db.models import Q, Sum, Count, F, Case, When, Value, IntegerField, Avg, ExpressionWrapper, DecimalField
from decimal import Decimal
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import Http404
from django.conf import settings
import json
from datetime import datetime, timedelta

from .models import Pedido, LineaPedido, SeguimientoPedido
from .forms import (
    PedidoForm, LineaPedidoFormSet, CambiarEstadoPedidoForm,
    FiltrosPedidoForm, CrearOrdenProduccionForm
)
from clientes.models import Cliente
from productos.models import ProductoTerminado


class PedidoListView(LoginRequiredMixin, ListView):
    """Vista para listar pedidos con filtros optimizada para HTML"""
    model = Pedido
    template_name = 'pedidos/pedido_list.html'
    context_object_name = 'pedidos'
    paginate_by = 20

    def get_queryset(self):
        queryset = Pedido.objects.select_related('cliente').prefetch_related(
            'lineas__producto'
        ).order_by('-fecha_pedido', '-numero_pedido')

        # Aplicar filtros desde GET parameters
        estado = self.request.GET.get('estado')
        prioridad = self.request.GET.get('prioridad')
        cliente_id = self.request.GET.get('cliente')
        numero_pedido = self.request.GET.get('numero_pedido')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        search = self.request.GET.get('search')
        con_orden = self.request.GET.get('con_orden')

        if estado:
            queryset = queryset.filter(estado=estado)
        
        if prioridad:
            queryset = queryset.filter(prioridad=prioridad)
        
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        
        if numero_pedido:
            queryset = queryset.filter(numero_pedido__icontains=numero_pedido)
        
        if fecha_desde:
            queryset = queryset.filter(fecha_pedido__gte=fecha_desde)
        
        if fecha_hasta:
            queryset = queryset.filter(fecha_pedido__lte=fecha_hasta)

        if search:
            queryset = queryset.filter(
                Q(numero_pedido__icontains=search) |
                Q(cliente__razon_social__icontains=search) |
                Q(pedido_cliente_referencia__icontains=search)
            )

        # Corregir el filtro de órdenes de producción
        if con_orden == 'si':
            try:
                from produccion.models import OrdenProduccion
                # Obtener pedidos que tienen órdenes de producción asociadas
                pedidos_con_op = OrdenProduccion.objects.filter(
                    id_pedido_contable__isnull=False
                ).values_list('id_pedido_contable', flat=True).distinct()
                queryset = queryset.filter(numero_pedido__in=pedidos_con_op)
            except ImportError:
                # Si no existe el módulo de producción, ignorar este filtro
                pass
        elif con_orden == 'no':
            try:
                from produccion.models import OrdenProduccion
                # Obtener pedidos que NO tienen órdenes de producción asociadas
                pedidos_con_op = OrdenProduccion.objects.filter(
                    id_pedido_contable__isnull=False
                ).values_list('id_pedido_contable', flat=True).distinct()
                queryset = queryset.exclude(numero_pedido__in=pedidos_con_op)
            except ImportError:
                # Si no existe el módulo de producción, ignorar este filtro
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Datos para filtros
        context['estados'] = Pedido.ESTADO_CHOICES
        context['prioridades'] = Pedido.PRIORIDAD_CHOICES
        context['clientes'] = Cliente.objects.filter(is_active=True).order_by('razon_social')
        context['today'] = timezone.now().date()
        
        # Filtros aplicados
        context['filtros'] = {
            'estado': self.request.GET.get('estado', ''),
            'prioridad': self.request.GET.get('prioridad', ''),
            'cliente': self.request.GET.get('cliente', ''),
            'numero_pedido': self.request.GET.get('numero_pedido', ''),
            'fecha_desde': self.request.GET.get('fecha_desde', ''),
            'fecha_hasta': self.request.GET.get('fecha_hasta', ''),
            'search': self.request.GET.get('search', ''),
            'con_orden': self.request.GET.get('con_orden', ''),
        }
        
        # Estadísticas rápidas - corregir consultas
        total_queryset = Pedido.objects.all()
        
        # Calcular pedidos sin orden de producción
        try:
            from produccion.models import OrdenProduccion
            pedidos_con_op = OrdenProduccion.objects.filter(
                id_pedido_contable__isnull=False
            ).values_list('id_pedido_contable', flat=True).distinct()
            sin_orden_produccion = total_queryset.exclude(numero_pedido__in=pedidos_con_op).count()
        except ImportError:
            sin_orden_produccion = 0
        
        context['estadisticas'] = {
            'total_pedidos': total_queryset.count(),
            'sin_orden_produccion': sin_orden_produccion,
            'pendientes_facturar': total_queryset.filter(estado='PENDIENTE_FACTURAR').count(),
        }
        
        return context


class PedidoDetailView(LoginRequiredMixin, DetailView):
    """Vista de detalle de un pedido optimizada para HTML"""
    model = Pedido
    template_name = 'pedidos/pedido_detail.html'
    context_object_name = 'pedido'

    def get_queryset(self):
        return Pedido.objects.select_related(
            'cliente', 'creado_por', 'actualizado_por'
        ).prefetch_related(
            'lineas__producto',
            'seguimientos__usuario'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = self.get_object()
        
        # Información del cliente
        context['cliente'] = pedido.cliente
        
        # Resumen de líneas con información de producción
        resumen_lineas = []
        for linea in pedido.lineas.all():
            # Buscar órdenes de producción asociadas a este pedido específico
            try:
                from produccion.models import OrdenProduccion
                ordenes = OrdenProduccion.objects.filter(
                    id_pedido_contable=pedido.numero_pedido,
                    producto=linea.producto
                )
                tiene_orden = ordenes.exists()
            except ImportError:
                ordenes = []
                tiene_orden = False
            
            resumen_lineas.append({
                'linea': linea,
                'tiene_orden': tiene_orden,
                'ordenes': ordenes,
                'porcentaje_completado': linea.porcentaje_completado,
            })
        
        context['resumen_lineas'] = resumen_lineas
        
        # Órdenes de producción asociadas al pedido
        try:
            from produccion.models import OrdenProduccion
            context['ordenes_produccion'] = OrdenProduccion.objects.filter(
                id_pedido_contable=pedido.numero_pedido
            ).select_related('producto').order_by('-fecha_creacion')
        except ImportError:
            context['ordenes_produccion'] = []
        
        # Seguimientos
        context['seguimientos'] = pedido.seguimientos.select_related('usuario').order_by('-fecha_cambio')[:10]
        
        # Calcular progreso general
        context['progreso_general'] = pedido.porcentaje_completado
        
        return context


class PedidoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un nuevo pedido simplificada para HTML"""
    model = Pedido
    form_class = PedidoForm
    template_name = 'pedidos/pedido_form.html'
    permission_required = 'pedidos.add_pedido'

    def get_success_url(self):
        return reverse('pedidos_web:pedido_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['lineas_formset'] = LineaPedidoFormSet(
                self.request.POST,
                instance=self.object
            )
        else:
            context['lineas_formset'] = LineaPedidoFormSet(instance=self.object)
        
        # Productos activos para el formulario - CORREGIDO: usar is_active en lugar de activo
        productos = ProductoTerminado.objects.filter(is_active=True).values(
            'id', 'codigo', 'nombre'
        )
        context['productos_json'] = json.dumps(list(productos))
        
        context['es_nuevo'] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        lineas_formset = context['lineas_formset']
        
        if lineas_formset.is_valid():
            with transaction.atomic():
                # Guardar el pedido
                pedido = form.save(commit=False)
                
                # Generar número de pedido automáticamente
                pedido.numero_pedido = Pedido.generar_numero_pedido()
                
                # Asignar usuario que crea
                pedido.creado_por = self.request.user
                pedido.actualizado_por = self.request.user
                pedido.save()
                
                # Guardar las líneas del pedido
                lineas_formset.instance = pedido
                lineas_formset.save()
                
                # Calcular y actualizar el valor total
                pedido.valor_total = pedido.calcular_total()
                pedido.save(update_fields=['valor_total'])
                
                # Registrar seguimiento
                SeguimientoPedido.objects.create(
                    pedido=pedido,
                    estado_nuevo='BORRADOR',
                    observaciones='Creación inicial del pedido',
                    usuario=self.request.user
                )
                
                messages.success(
                    self.request,
                    f'Pedido {pedido.numero_pedido} creado exitosamente'
                )
                
                return redirect(pedido.get_absolute_url())
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        context = self.get_context_data()
        lineas_formset = context.get('lineas_formset')
        
        # Construir mensajes de error más específicos
        error_messages = []
        
        # Errores del formulario principal
        if form.errors:
            for field, errors in form.errors.items():
                field_name = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_name}: {error}")
        
        # Errores no asociados a campos específicos del formulario principal
        if form.non_field_errors():
            for error in form.non_field_errors():
                error_messages.append(f"Error general: {error}")
        
        # Errores del formset de líneas
        if lineas_formset and hasattr(lineas_formset, 'errors'):
            # Errores generales del formset
            if hasattr(lineas_formset, 'non_form_errors') and lineas_formset.non_form_errors():
                for error in lineas_formset.non_form_errors():
                    error_messages.append(f"Error en líneas: {error}")
            
            # Errores de formularios individuales en el formset
            for i, form_errors in enumerate(lineas_formset.errors):
                if form_errors:
                    for field, errors in form_errors.items():
                        for error in errors:
                            error_messages.append(f"Línea {i+1} - {field}: {error}")
        
        # Mostrar errores específicos o mensaje genérico
        if error_messages:
            for error_msg in error_messages:
                messages.error(self.request, error_msg)
        else:
            messages.error(
                self.request,
                'Error al crear el pedido. Verifique los datos ingresados.'
            )
        
        return super().form_invalid(form)


class PedidoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para editar un pedido existente"""
    model = Pedido
    form_class = PedidoForm
    template_name = 'pedidos/pedido_form.html'
    permission_required = 'pedidos.change_pedido'

    def get_success_url(self):
        return reverse('pedidos_web:pedido_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['lineas_formset'] = LineaPedidoFormSet(
                self.request.POST,
                instance=self.object
            )
        else:
            context['lineas_formset'] = LineaPedidoFormSet(instance=self.object)
        
        # Productos activos para el formulario - CORREGIDO: usar is_active en lugar de activo
        productos = ProductoTerminado.objects.filter(is_active=True).values(
            'id', 'codigo', 'nombre'
        )
        context['productos_json'] = json.dumps(list(productos))
        
        context['es_nuevo'] = False
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        lineas_formset = context['lineas_formset']
        
        # Solo permitir edición si el pedido está en estado BORRADOR
        if self.object.estado not in ['BORRADOR']:
            messages.error(
                self.request,
                'Solo se pueden editar pedidos en estado BORRADOR'
            )
            return redirect('pedidos_web:pedido_detail', pk=self.object.pk)
        
        with transaction.atomic():
            form.instance.actualizado_por = self.request.user
            self.object = form.save()
            
            if lineas_formset.is_valid():
                lineas_formset.save()
                
                # Recalcular total
                self.object.calcular_total()
                self.object.save()
                
                messages.success(
                    self.request,
                    f'Pedido {self.object.numero_pedido} actualizado exitosamente'
                )
                return super().form_valid(form)
            else:
                return self.form_invalid(form)

    def form_invalid(self, form):
        context = self.get_context_data()
        lineas_formset = context.get('lineas_formset')
        
        # Construir mensajes de error más específicos
        error_messages = []
        
        # Errores del formulario principal
        if form.errors:
            for field, errors in form.errors.items():
                field_name = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_name}: {error}")
        
        # Errores no asociados a campos específicos del formulario principal
        if form.non_field_errors():
            for error in form.non_field_errors():
                error_messages.append(f"Error general: {error}")
        
        # Errores del formset de líneas
        if lineas_formset and hasattr(lineas_formset, 'errors'):
            # Errores generales del formset
            if hasattr(lineas_formset, 'non_form_errors') and lineas_formset.non_form_errors():
                for error in lineas_formset.non_form_errors():
                    error_messages.append(f"Error en líneas: {error}")
            
            # Errores de formularios individuales en el formset
            for i, form_errors in enumerate(lineas_formset.errors):
                if form_errors:
                    for field, errors in form_errors.items():
                        for error in errors:
                            error_messages.append(f"Línea {i+1} - {field}: {error}")
        
        # Mostrar errores específicos o mensaje genérico
        if error_messages:
            for error_msg in error_messages:
                messages.error(self.request, error_msg)
        else:
            messages.error(
                self.request,
                'Error al actualizar el pedido. Verifique los datos ingresados.'
            )
        
        return super().form_invalid(form)


@login_required
@permission_required('pedidos.change_pedido')
def cambiar_estado_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    
    if request.method == 'POST':
        form = CambiarEstadoPedidoForm(pedido, request.POST)
        
        if form.is_valid():
            nuevo_estado = form.cleaned_data['nuevo_estado']
            observaciones = form.cleaned_data.get('observaciones', '')
            
            # Validar transición de estado
            if nuevo_estado == pedido.estado:
                messages.warning(request, 'El pedido ya se encuentra en ese estado')
                return redirect('pedidos_web:pedido_detail', pk=pk)
            
            # Validaciones específicas según el estado actual y el nuevo estado
            transiciones_validas = {
                'BORRADOR': ['CONFIRMADO', 'CANCELADO'],
                'CONFIRMADO': ['EN_PRODUCCION', 'CANCELADO'],
                'EN_PRODUCCION': ['PRODUCIDO', 'CANCELADO'],
                'PRODUCIDO': ['PENDIENTE_FACTURAR', 'CANCELADO'],
                'PENDIENTE_FACTURAR': ['FACTURADO', 'CANCELADO'],
                'FACTURADO': ['ENTREGADO', 'CANCELADO'],
                'ENTREGADO': [],  # Estado final
                'CANCELADO': []    # Estado final
            }
            
            if nuevo_estado not in transiciones_validas.get(pedido.estado, []):
                messages.error(
                    request,
                    f'No se puede cambiar el estado de {pedido.get_estado_display()} a {dict(Pedido.ESTADO_CHOICES)[nuevo_estado]}'
                )
                return redirect('pedidos_web:pedido_detail', pk=pk)
            
            # Guardar estado anterior para el seguimiento
            estado_anterior = pedido.estado
            
            # Actualizar estado
            pedido.estado = nuevo_estado
            
            # Si se está facturando, validar y guardar número de factura y fecha
            if nuevo_estado == 'FACTURADO':
                if not form.cleaned_data.get('numero_factura'):
                    messages.error(request, 'Debe proporcionar un número de factura')
                    return redirect('pedidos_web:pedido_detail', pk=pk)
                    
                pedido.numero_factura = form.cleaned_data.get('numero_factura')
                pedido.fecha_facturacion = form.cleaned_data.get('fecha_facturacion') or timezone.now().date()
            
            # Si se está entregando, guardar fecha de entrega real
            if nuevo_estado == 'ENTREGADO':
                pedido.fecha_entrega_real = form.cleaned_data.get('fecha_entrega_real') or timezone.now().date()
            
            # Si se está cancelando, validar que haya una observación
            if nuevo_estado == 'CANCELADO' and not observaciones:
                messages.error(request, 'Debe proporcionar un motivo para cancelar el pedido')
                return redirect('pedidos_web:pedido_detail', pk=pk)
            
            pedido.actualizado_por = request.user
            pedido.save()
            
            # Registrar seguimiento
            SeguimientoPedido.objects.create(
                pedido=pedido,
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado,
                observaciones=observaciones,
                usuario=request.user
            )
            
            messages.success(request, f'Estado del pedido actualizado a {dict(Pedido.ESTADO_CHOICES)[nuevo_estado]}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Error en {field}: {error}')
    
    return redirect('pedidos_web:pedido_detail', pk=pk)


@login_required
def get_producto_info(request):
    """API para obtener información de un producto"""
    producto_id = request.GET.get('producto_id')
    
    if not producto_id:
        return JsonResponse({'error': 'ID de producto requerido'}, status=400)
    
    try:
        # CORREGIDO: usar is_active en lugar de activo
        producto = ProductoTerminado.objects.get(id=producto_id, is_active=True)
        data = {
            'id': producto.id,
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'unidad_medida': producto.unidad_medida.simbolo if producto.unidad_medida else 'UN'
        }
        return JsonResponse(data)
    except ProductoTerminado.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)


@login_required
def dashboard_pedidos(request):
    """Dashboard con estadísticas de pedidos optimizado para HTML"""
    
    # Fechas para filtrado
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
    inicio_anio = hoy.replace(month=1, day=1)
    
    # Filtro de fecha opcional
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    # Query base
    queryset = Pedido.objects.all()
    
    # Aplicar filtros si existen
    if fecha_desde:
        try:
            fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            queryset = queryset.filter(fecha_pedido__gte=fecha_desde)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            queryset = queryset.filter(fecha_pedido__lte=fecha_hasta)
        except ValueError:
            pass
    
    # Estadísticas generales
    estadisticas = {
        'total_pedidos': queryset.count(),
        'pedidos_mes_actual': queryset.filter(fecha_pedido__gte=inicio_mes).count(),
        'pedidos_mes_anterior': queryset.filter(
            fecha_pedido__gte=inicio_mes_anterior,
            fecha_pedido__lt=inicio_mes
        ).count(),
        'pedidos_anio': queryset.filter(fecha_pedido__gte=inicio_anio).count(),
        'valor_total': queryset.aggregate(total=Sum('valor_total'))['total'] or 0,
        'valor_total_mes': queryset.filter(
            fecha_pedido__gte=inicio_mes
        ).aggregate(total=Sum('valor_total'))['total'] or 0,
        'promedio_valor': queryset.aggregate(
            promedio=Avg('valor_total')
        )['promedio'] or 0,
    }
    
    # Estadísticas por estado
    estados_count = queryset.values('estado').annotate(
        count=Count('id'),
        valor_total=Sum('valor_total')
    ).order_by('estado')
    
    # Convertir a diccionario para fácil acceso en template
    estados_dict = {}
    for estado in estados_count:
        nombre_estado = dict(Pedido.ESTADO_CHOICES).get(estado['estado'], estado['estado'])
        estados_dict[estado['estado']] = {
            'nombre': nombre_estado,
            'count': estado['count'],
            'valor_total': estado['valor_total'] or 0,
            'porcentaje': (estado['count'] / estadisticas['total_pedidos'] * 100) if estadisticas['total_pedidos'] > 0 else 0
        }
    
    # Pedidos por prioridad
    prioridades_count = queryset.values('prioridad').annotate(
        count=Count('id')
    ).order_by('prioridad')
    
    prioridades_dict = {}
    for prioridad in prioridades_count:
        nombre_prioridad = dict(Pedido.PRIORIDAD_CHOICES).get(prioridad['prioridad'], prioridad['prioridad'])
        prioridades_dict[prioridad['prioridad']] = {
            'nombre': nombre_prioridad,
            'count': prioridad['count'],
            'porcentaje': (prioridad['count'] / estadisticas['total_pedidos'] * 100) if estadisticas['total_pedidos'] > 0 else 0
        }
    
    # Pedidos por mes (para gráfico)
    meses_anteriores = 6
    pedidos_por_mes = []
    
    for i in range(meses_anteriores, -1, -1):
        fecha_inicio = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1)
        fecha_inicio = fecha_inicio.replace(month=((fecha_inicio.month - i - 1) % 12) + 1)
        if fecha_inicio.month > hoy.month:
            fecha_inicio = fecha_inicio.replace(year=fecha_inicio.year - 1)
            
        fecha_fin = fecha_inicio.replace(month=fecha_inicio.month % 12 + 1, day=1) - timedelta(days=1)
        if fecha_inicio.month == 12:
            fecha_fin = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1, day=1) - timedelta(days=1)
        
        count = queryset.filter(fecha_pedido__gte=fecha_inicio, fecha_pedido__lte=fecha_fin).count()
        valor = queryset.filter(fecha_pedido__gte=fecha_inicio, fecha_pedido__lte=fecha_fin).aggregate(
            total=Sum('valor_total')
        )['total'] or 0
        
        pedidos_por_mes.append({
            'mes': fecha_inicio.strftime('%B %Y'),
            'count': count,
            'valor': valor
        })
    
    # Últimos pedidos
    ultimos_pedidos = queryset.select_related('cliente').order_by('-creado_en')[:10]
    
    # Pedidos próximos a vencer
    fecha_limite = timezone.now().date() + timedelta(days=7)
    pedidos_proximos = queryset.filter(
        fecha_compromiso__lte=fecha_limite,
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    ).select_related('cliente').order_by('fecha_compromiso')[:10]
    
    # Top clientes
    top_clientes = queryset.values('cliente__razon_social').annotate(
        count=Count('id'),
        valor_total=Sum('valor_total')
    ).order_by('-valor_total')[:5]
    
    context = {
        'estadisticas': estadisticas,
        'estados': estados_dict,
        'prioridades': prioridades_dict,
        'pedidos_por_mes': pedidos_por_mes,
        'ultimos_pedidos': ultimos_pedidos,
        'pedidos_proximos': pedidos_proximos,
        'top_clientes': top_clientes,
        'today': hoy,
        'filtros': {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }
    
    return render(request, 'pedidos/dashboard.html', context)


@login_required
@permission_required('pedidos.view_pedido')
def reporte_pedidos(request):
    """Vista para generar reportes de pedidos"""
    
    # Filtros del reporte
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    cliente_id = request.GET.get('cliente')
    estado = request.GET.get('estado')
    
    # Query base
    queryset = Pedido.objects.select_related('cliente').prefetch_related('lineas__producto')
    
    # Aplicar filtros
    if fecha_desde:
        queryset = queryset.filter(fecha_pedido__gte=fecha_desde)
    if fecha_hasta:
        queryset = queryset.filter(fecha_pedido__lte=fecha_hasta)
    if cliente_id:
        queryset = queryset.filter(cliente_id=cliente_id)
    if estado:
        queryset = queryset.filter(estado=estado)
    
    # Obtener pedidos y calcular totales
    pedidos = queryset.order_by('-fecha_pedido')
    
    # Resumen
    resumen = {
        'total_pedidos': pedidos.count(),
        'valor_total': sum(p.valor_total for p in pedidos),
        'promedio_por_pedido': 0
    }
    
    if resumen['total_pedidos'] > 0:
        resumen['promedio_por_pedido'] = resumen['valor_total'] / resumen['total_pedidos']
    
    context = {
        'pedidos': pedidos,
        'resumen': resumen,
        'clientes': Cliente.objects.filter(is_active=True).order_by('razon_social'),
        'estados': Pedido.ESTADO_CHOICES,
        'filtros': {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'cliente_id': cliente_id,
            'estado': estado,
        }
    }
    
    return render(request, 'pedidos/reporte_pedidos.html', context)


@login_required
@permission_required('pedidos.delete_pedido')
def eliminar_pedido(request, pk):
    """Vista para eliminar un pedido"""
    pedido = get_object_or_404(Pedido, pk=pk)
    
    # Solo permitir eliminación si está en estado BORRADOR
    if pedido.estado != 'BORRADOR':
        messages.error(
            request,
            'Solo se pueden eliminar pedidos en estado BORRADOR'
        )
        return redirect('pedidos_web:pedido_detail', pk=pk)
    
    if request.method == 'POST':
        numero_pedido = pedido.numero_pedido
        pedido.delete()
        messages.success(
            request,
            f'Pedido {numero_pedido} eliminado exitosamente'
        )
        return redirect('pedidos:pedido_list')
    
    return render(request, 'pedidos/confirmar_eliminar.html', {
        'pedido': pedido
    })


@login_required
@permission_required('produccion.add_ordenproduccion')
def crear_orden_produccion(request, pk):
    """Vista para crear órdenes de producción desde un pedido"""
    pedido = get_object_or_404(Pedido, pk=pk)
    
    # Validar que el pedido esté en estado CONFIRMADO
    if pedido.estado not in ['CONFIRMADO', 'EN_PRODUCCION']:
        messages.error(
            request,
            'Solo se pueden crear órdenes de producción para pedidos en estado CONFIRMADO o EN_PRODUCCION'
        )
        return redirect('pedidos_web:pedido_detail', pk=pk)
    
    # Verificar si hay líneas disponibles para producción
    lineas_disponibles = pedido.lineas.filter(cantidad__gt=F('cantidad_producida'))
    if not lineas_disponibles.exists():
        messages.warning(
            request,
            'Todas las líneas de este pedido ya tienen órdenes de producción asociadas'
        )
        return redirect('pedidos_web:pedido_detail', pk=pk)
    
    if request.method == 'POST':
        form = CrearOrdenProduccionForm(pedido, request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Obtener datos del formulario
                    lineas_seleccionadas = form.cleaned_data['lineas_seleccionadas']
                    fecha_compromiso = form.cleaned_data['fecha_compromiso']
                    prioridad = form.cleaned_data['prioridad']
                    tipo_orden = form.cleaned_data['tipo_orden']
                    observaciones = form.cleaned_data.get('observaciones', '')
                    
                    # Importar aquí para evitar importación circular
                    from produccion.models import OrdenProduccion
                    from inventario.models import MateriaPrima
                    
                    # Obtener una materia prima por defecto para usar como sustrato
                    try:
                        sustrato_default = MateriaPrima.objects.filter(is_active=True).first()
                        if not sustrato_default:
                            sustrato_default = MateriaPrima.objects.first()
                        if not sustrato_default:
                            raise Exception('No se encontró ninguna materia prima para usar como sustrato')
                    except Exception as e:
                        messages.error(request, f'Error al obtener materia prima por defecto: {str(e)}')
                        return redirect('pedidos_web:pedido_detail', pk=pedido.pk)
                    
                    # Generar órdenes según el tipo seleccionado
                    if tipo_orden == 'individual':
                        # Crear una orden por cada línea seleccionada
                        for linea in lineas_seleccionadas:
                            # Calcular cantidad pendiente
                            cantidad_pendiente = linea.cantidad - linea.cantidad_producida
                            
                            if cantidad_pendiente <= 0:
                                continue
                                
                            # Crear orden de producción
                            orden = OrdenProduccion.objects.create(
                                id_pedido_contable=pedido.numero_pedido,
                                cliente=pedido.cliente,
                                producto=linea.producto,
                                cantidad_solicitada_kg=cantidad_pendiente,
                                fecha_compromiso_entrega=fecha_compromiso,
                                etapa_actual='PLAN',
                                observaciones=f"{observaciones}\nLínea de pedido: {linea.orden_linea}",
                                creado_por=request.user,
                                # Campos requeridos que no están en el formulario
                                op_numero=f"OP-{pedido.numero_pedido}-{linea.orden_linea}",
                                sustrato=sustrato_default,
                                ancho_sustrato_mm=linea.producto.ancho or Decimal('0.01'),
                                calibre_sustrato_um=linea.producto.calibre_um or Decimal('0.01')
                            )
                            
                            # Actualizar línea de pedido
                            linea.cantidad_producida += cantidad_pendiente
                            linea.save(update_fields=['cantidad_producida'])
                            
                    else:  # tipo_orden == 'consolidada'
                        # Agrupar líneas por producto
                        productos_agrupados = {}
                        for linea in lineas_seleccionadas:
                            cantidad_pendiente = linea.cantidad - linea.cantidad_producida
                            if cantidad_pendiente <= 0:
                                continue
                                
                            if linea.producto.id not in productos_agrupados:
                                productos_agrupados[linea.producto.id] = {
                                    'producto': linea.producto,
                                    'cantidad_total': 0,
                                    'lineas': []
                                }
                                
                            productos_agrupados[linea.producto.id]['cantidad_total'] += cantidad_pendiente
                            productos_agrupados[linea.producto.id]['lineas'].append({
                                'linea': linea,
                                'cantidad_pendiente': cantidad_pendiente
                            })
                        
                        # Crear una orden por producto
                        for producto_id, datos in productos_agrupados.items():
                            # Crear orden de producción
                            orden = OrdenProduccion.objects.create(
                                id_pedido_contable=pedido.numero_pedido,
                                cliente=pedido.cliente,
                                producto=datos['producto'],
                                cantidad_solicitada_kg=datos['cantidad_total'],
                                fecha_compromiso_entrega=fecha_compromiso,
                                etapa_actual='PLAN',
                                observaciones=observaciones,
                                creado_por=request.user,
                                # Campos requeridos que no están en el formulario
                                op_numero=f"OP-{pedido.numero_pedido}-CONS-{datos['producto'].codigo}",
                                sustrato=sustrato_default,
                                ancho_sustrato_mm=datos['producto'].ancho or Decimal('0.01'),
                                calibre_sustrato_um=datos['producto'].calibre_um or Decimal('0.01')
                            )
                            
                            # Actualizar líneas de pedido
                            for item in datos['lineas']:
                                linea = item['linea']
                                cantidad = item['cantidad_pendiente']
                                
                                linea.cantidad_producida += cantidad
                                linea.save(update_fields=['cantidad_producida'])
                    
                    # Actualizar estado del pedido si es necesario
                    if pedido.estado == 'CONFIRMADO':
                        estado_anterior = pedido.estado
                        pedido.estado = 'EN_PRODUCCION'
                        pedido.save(update_fields=['estado'])
                        
                        # Registrar cambio de estado
                        SeguimientoPedido.objects.create(
                            pedido=pedido,
                            estado_anterior=estado_anterior,
                            estado_nuevo='EN_PRODUCCION',
                            observaciones='Cambio automático al crear orden de producción',
                            usuario=request.user
                        )
                    
                    messages.success(
                        request,
                        f'Órdenes de producción creadas exitosamente para el pedido {pedido.numero_pedido}'
                    )
                    
            except Exception as e:
                messages.error(request, f'Error al crear órdenes de producción: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Error en {field}: {error}')
    else:
        # Mostrar formulario
        return render(request, 'pedidos/crear_orden_produccion.html', {
            'pedido': pedido,
            'form': CrearOrdenProduccionForm(pedido),
            'lineas_disponibles': lineas_disponibles
        })
    
    return redirect('pedidos_web:pedido_detail', pk=pk)