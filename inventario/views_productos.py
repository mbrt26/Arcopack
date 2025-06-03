"""
Vistas para la gestión de inventario de productos en proceso (WIP) y productos terminados (PT).
"""
from django.views.generic import TemplateView, DetailView, FormView, UpdateView, ListView
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages

from .models import LoteProductoEnProceso, LoteProductoTerminado, Ubicacion, MovimientoInventario
from django.contrib.contenttypes.models import ContentType
from productos.models import ProductoTerminado
from .forms import (
    TransferirWIPForm, ConsumirWIPForm, AjustarStockWIPForm,
    TransferirPTForm, ConsumirPTForm, AjustarStockPTForm, DespacharPTForm
)


class ProductoEnProcesoListView(LoginRequiredMixin, TemplateView):
    """Vista para listar lotes de productos en proceso (WIP)."""
    template_name = 'inventario/producto_en_proceso_list.html'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de búsqueda
        search_query = self.request.GET.get('q', '')
        estado_filter = self.request.GET.get('estado', '')
        ubicacion_filter = self.request.GET.get('ubicacion', '')
        producto_filter = self.request.GET.get('producto', '')
        
        # Filtrar lotes de producto en proceso
        wip_lotes = LoteProductoEnProceso.objects.select_related(
            'producto_terminado', 'ubicacion', 'orden_produccion'
        ).order_by('-creado_en')
        
        # Aplicar filtros si existen
        if search_query:
            wip_lotes = wip_lotes.filter(
                Q(lote_id__icontains=search_query) |
                Q(producto_terminado__codigo__icontains=search_query) |
                Q(producto_terminado__nombre__icontains=search_query) |
                Q(orden_produccion__codigo__icontains=search_query)
            )
        
        if estado_filter:
            wip_lotes = wip_lotes.filter(estado=estado_filter)
            
        if ubicacion_filter:
            wip_lotes = wip_lotes.filter(ubicacion_id=ubicacion_filter)
            
        if producto_filter:
            wip_lotes = wip_lotes.filter(producto_terminado_id=producto_filter)
        
        # Paginar resultados
        paginator = Paginator(wip_lotes, self.paginate_by)
        page = self.request.GET.get('page')
        wip_lotes_paginated = paginator.get_page(page)
        
        # Obtener las ubicaciones para el filtro
        ubicaciones = Ubicacion.objects.all().order_by('nombre')
        
        # Obtener los productos terminados para el filtro
        productos = ProductoTerminado.objects.filter(
            lotes_wip__isnull=False
        ).distinct().order_by('codigo')
        
        context.update({
            'wip_lotes': wip_lotes_paginated,
            'search_query': search_query,
            'estado_filter': estado_filter,
            'ubicacion_filter': ubicacion_filter,
            'producto_filter': producto_filter,
            'estados_lote': LoteProductoEnProceso.ESTADO_LOTE_CHOICES,
            'ubicaciones': ubicaciones,
            'productos': productos,
        })
        
        return context


class ProductoEnProcesoDetailView(LoginRequiredMixin, DetailView):
    """Vista detallada de un lote de producto en proceso (WIP)."""
    model = LoteProductoEnProceso
    template_name = 'inventario/producto_en_proceso_detail.html'
    context_object_name = 'lote'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = self.object
        
        # Agregar información adicional al contexto si es necesario
        context.update({
            'titulo': f'Detalle de Lote WIP: {lote.lote_id}',
        })
        
        return context


class ProductoEnProcesoHistoryView(LoginRequiredMixin, DetailView):
    """Vista para mostrar el historial de movimientos de un lote WIP."""
    model = LoteProductoEnProceso
    template_name = 'inventario/producto_en_proceso_history.html'
    context_object_name = 'lote'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = self.get_object()
        
        # Obtener todos los movimientos relacionados con este lote
        content_type = ContentType.objects.get_for_model(LoteProductoEnProceso)
        movimientos = MovimientoInventario.objects.filter(
            content_type=content_type,
            object_id=lote.id
        ).order_by('-timestamp')
        
        context['titulo'] = f'Historial de Movimientos - Lote WIP: {lote.lote_id}'
        context['movimientos'] = movimientos
        return context


class TransferirWIPView(LoginRequiredMixin, FormView):
    """Vista para transferir un lote WIP a otra ubicación."""
    template_name = 'inventario/producto_en_proceso_transferir.html'
    form_class = TransferirWIPForm
    
    def get_success_url(self):
        return reverse('inventario_web:wip-detail', kwargs={'pk': self.kwargs['pk']})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['lote_id'] = self.kwargs['pk']
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = get_object_or_404(LoteProductoEnProceso, pk=self.kwargs['pk'])
        context['lote'] = lote
        context['titulo'] = f'Transferir Lote WIP: {lote.lote_id}'
        return context
    
    def form_valid(self, form):
        lote = get_object_or_404(LoteProductoEnProceso, pk=self.kwargs['pk'])
        
        # Verificar que el lote esté disponible
        if lote.estado != 'DISPONIBLE':
            messages.error(self.request, f'No se puede transferir el lote {lote.lote_id} porque no está disponible')
            return self.form_invalid(form)
        
        ubicacion_origen = lote.ubicacion
        ubicacion_destino = form.cleaned_data['ubicacion_destino']
        observaciones = form.cleaned_data['observaciones']
        
        # Crear movimiento de salida
        MovimientoInventario.objects.create(
            content_type=ContentType.objects.get_for_model(LoteProductoEnProceso),
            object_id=lote.id,
            tipo_movimiento='TRANSFERENCIA_SALIDA',
            cantidad=lote.cantidad_actual,
            unidad_medida=lote.unidad_medida_primaria,
            ubicacion_origen=ubicacion_origen,
            ubicacion_destino=ubicacion_destino,
            observaciones=observaciones,
            usuario=self.request.user
        )
        
        # Crear movimiento de entrada
        MovimientoInventario.objects.create(
            content_type=ContentType.objects.get_for_model(LoteProductoEnProceso),
            object_id=lote.id,
            tipo_movimiento='TRANSFERENCIA_ENTRADA',
            cantidad=lote.cantidad_actual,
            unidad_medida=lote.unidad_medida_primaria,
            ubicacion_origen=ubicacion_origen,
            ubicacion_destino=ubicacion_destino,
            observaciones=observaciones,
            usuario=self.request.user
        )
        
        # Actualizar ubicación del lote
        lote.ubicacion = ubicacion_destino
        lote.save()
        
        messages.success(self.request, f'Lote {lote.lote_id} transferido exitosamente a {ubicacion_destino.nombre}')
        return super().form_valid(form)


class ConsumirWIPView(LoginRequiredMixin, FormView):
    """Vista para consumir un lote WIP."""
    template_name = 'inventario/producto_en_proceso_consumir.html'
    form_class = ConsumirWIPForm
    
    def get_success_url(self):
        return reverse('inventario_web:wip-detail', kwargs={'pk': self.kwargs['pk']})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['lote_id'] = self.kwargs['pk']
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = get_object_or_404(LoteProductoEnProceso, pk=self.kwargs['pk'])
        context['lote'] = lote
        context['titulo'] = f'Consumir Lote WIP: {lote.lote_id}'
        return context
    
    def form_valid(self, form):
        lote = get_object_or_404(LoteProductoEnProceso, pk=self.kwargs['pk'])
        
        # Verificar que el lote esté disponible
        if lote.estado != 'DISPONIBLE':
            messages.error(self.request, f'No se puede consumir el lote {lote.lote_id} porque no está disponible')
            return self.form_invalid(form)
        
        cantidad = form.cleaned_data['cantidad']
        documento_referencia = form.cleaned_data['documento_referencia']
        observaciones = form.cleaned_data['observaciones']
        
        # Verificar que la cantidad a consumir sea válida
        if cantidad > lote.cantidad_actual:
            form.add_error('cantidad', f'La cantidad a consumir no puede ser mayor que el stock actual ({lote.cantidad_actual})')
            return self.form_invalid(form)
        
        # Crear movimiento de consumo
        MovimientoInventario.objects.create(
            content_type=ContentType.objects.get_for_model(LoteProductoEnProceso),
            object_id=lote.id,
            tipo_movimiento='CONSUMO_WIP',
            cantidad=cantidad,
            unidad_medida=lote.unidad_medida_primaria,
            ubicacion_origen=lote.ubicacion,
            documento_referencia=documento_referencia,
            observaciones=observaciones,
            usuario=self.request.user
        )
        
        # Actualizar cantidad del lote
        lote.cantidad_actual -= cantidad
        
        # Si se consumió todo, marcar como consumido
        if lote.cantidad_actual <= 0:
            lote.estado = 'CONSUMIDO'
            messages.success(self.request, f'Lote {lote.lote_id} consumido completamente')
        else:
            messages.success(self.request, f'Se consumieron {cantidad} {lote.unidad_medida_primaria.codigo} del lote {lote.lote_id}')
        
        lote.save()
        return super().form_valid(form)


class AjustarStockWIPView(LoginRequiredMixin, FormView):
    """Vista para ajustar el stock de un lote WIP."""
    template_name = 'inventario/producto_en_proceso_ajustar.html'
    form_class = AjustarStockWIPForm
    
    def get_success_url(self):
        return reverse('inventario_web:wip-detail', kwargs={'pk': self.kwargs['pk']})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['lote_id'] = self.kwargs['pk']
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = get_object_or_404(LoteProductoEnProceso, pk=self.kwargs['pk'])
        context['lote'] = lote
        context['titulo'] = f'Ajustar Stock de Lote WIP: {lote.lote_id}'
        return context
    
    def form_valid(self, form):
        lote = get_object_or_404(LoteProductoEnProceso, pk=self.kwargs['pk'])
        
        # Verificar que el lote esté disponible
        if lote.estado != 'DISPONIBLE':
            messages.error(self.request, f'No se puede ajustar el lote {lote.lote_id} porque no está disponible')
            return self.form_invalid(form)
        
        tipo_ajuste = form.cleaned_data['tipo_ajuste']
        cantidad = form.cleaned_data['cantidad']
        motivo = form.cleaned_data['motivo']
        observaciones = form.cleaned_data['observaciones']
        
        # Verificar que la cantidad sea válida para ajustes negativos
        if tipo_ajuste == 'AJUSTE_NEGATIVO' and cantidad > lote.cantidad_actual:
            form.add_error('cantidad', f'La cantidad a reducir no puede ser mayor que el stock actual ({lote.cantidad_actual})')
            return self.form_invalid(form)
        
        # Crear movimiento de ajuste
        MovimientoInventario.objects.create(
            content_type=ContentType.objects.get_for_model(LoteProductoEnProceso),
            object_id=lote.id,
            tipo_movimiento=tipo_ajuste,
            cantidad=cantidad,
            unidad_medida=lote.unidad_medida_primaria,
            ubicacion_origen=lote.ubicacion if tipo_ajuste == 'AJUSTE_NEGATIVO' else None,
            ubicacion_destino=lote.ubicacion if tipo_ajuste == 'AJUSTE_POSITIVO' else None,
            observaciones=f'Motivo: {dict(form.fields["motivo"].choices)[motivo]}. {observaciones}',
            usuario=self.request.user
        )
        
        # Actualizar cantidad del lote
        if tipo_ajuste == 'AJUSTE_POSITIVO':
            lote.cantidad_actual += cantidad
            messages.success(self.request, f'Se incrementó el stock del lote {lote.lote_id} en {cantidad} {lote.unidad_medida_primaria.codigo}')
        else:  # AJUSTE_NEGATIVO
            lote.cantidad_actual -= cantidad
            messages.success(self.request, f'Se redujo el stock del lote {lote.lote_id} en {cantidad} {lote.unidad_medida_primaria.codigo}')
        
        # Si el ajuste negativo dejó el lote en 0, marcarlo como consumido
        if lote.cantidad_actual <= 0:
            lote.estado = 'CONSUMIDO'
            messages.success(self.request, f'El lote {lote.lote_id} ha sido marcado como consumido')
        
        lote.save()
        return super().form_valid(form)       


class ProductoTerminadoListView(LoginRequiredMixin, TemplateView):
    """Vista para listar lotes de productos terminados (PT)."""
    template_name = 'inventario/producto_terminado_list.html'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de búsqueda
        search_query = self.request.GET.get('q', '')
        estado_filter = self.request.GET.get('estado', '')
        ubicacion_filter = self.request.GET.get('ubicacion', '')
        producto_filter = self.request.GET.get('producto', '')
        
        # Filtrar lotes de producto terminado
        pt_lotes = LoteProductoTerminado.objects.select_related(
            'producto_terminado', 'ubicacion', 'orden_produccion'
        ).order_by('-creado_en')
        
        # Aplicar filtros si existen
        if search_query:
            pt_lotes = pt_lotes.filter(
                Q(lote_id__icontains=search_query) |
                Q(producto_terminado__codigo__icontains=search_query) |
                Q(producto_terminado__nombre__icontains=search_query) |
                Q(orden_produccion__codigo__icontains=search_query)
            )
        
        if estado_filter:
            pt_lotes = pt_lotes.filter(estado=estado_filter)
            
        if ubicacion_filter:
            pt_lotes = pt_lotes.filter(ubicacion_id=ubicacion_filter)
            
        if producto_filter:
            pt_lotes = pt_lotes.filter(producto_terminado_id=producto_filter)
        
        # Paginar resultados
        paginator = Paginator(pt_lotes, self.paginate_by)
        page = self.request.GET.get('page')
        pt_lotes_paginated = paginator.get_page(page)
        
        # Obtener las ubicaciones para el filtro
        ubicaciones = Ubicacion.objects.all().order_by('nombre')
        
        # Obtener los productos terminados para el filtro
        productos = ProductoTerminado.objects.filter(
            lotes_pt__isnull=False
        ).distinct().order_by('codigo')
        
        context.update({
            'pt_lotes': pt_lotes_paginated,
            'search_query': search_query,
            'estado_filter': estado_filter,
            'ubicacion_filter': ubicacion_filter,
            'producto_filter': producto_filter,
            'estados_lote': LoteProductoTerminado.ESTADO_LOTE_CHOICES,
            'ubicaciones': ubicaciones,
            'productos': productos,
            'titulo': 'Inventario de Productos Terminados',
        })
        
        return context


class ProductoTerminadoDetailView(LoginRequiredMixin, DetailView):
    """Vista detallada de un lote de producto terminado (PT)."""
    model = LoteProductoTerminado
    template_name = 'inventario/producto_terminado_detail.html'
    context_object_name = 'lote'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = self.object
        
        # Agregar información adicional al contexto si es necesario
        context.update({
            'titulo': f'Detalle de Lote PT: {lote.lote_id}',
        })
        
        return context


class ProductoTerminadoHistoryView(LoginRequiredMixin, DetailView):
    """Vista para mostrar el historial de movimientos de un lote PT."""
    model = LoteProductoTerminado
    template_name = 'inventario/producto_terminado_history.html'
    context_object_name = 'lote'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = self.object
        
        # Obtener el content type para LoteProductoTerminado
        content_type = ContentType.objects.get_for_model(LoteProductoTerminado)
        
        # Obtener los movimientos relacionados con este lote
        movimientos = MovimientoInventario.objects.filter(
            lote_content_type=content_type,
            lote_object_id=lote.id
        ).order_by('-timestamp')
        
        context.update({
            'titulo': f'Historial de Lote PT: {lote.lote_id}',
            'movimientos': movimientos,
        })
        
        return context


class TransferirPTView(LoginRequiredMixin, FormView):
    """Vista para transferir un lote PT a otra ubicación."""
    template_name = 'inventario/producto_terminado_transferir.html'
    form_class = TransferirPTForm
    
    def get_success_url(self):
        return reverse('inventario_web:pt-detail', kwargs={'pk': self.kwargs['pk']})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'lote_id': self.kwargs['pk']}
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        context['lote'] = lote
        context['titulo'] = f'Transferir Lote PT: {lote.lote_id}'
        return context
    
    def form_valid(self, form):
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        tipo_transferencia = form.cleaned_data['tipo_transferencia']
        ubicacion_destino = form.cleaned_data['ubicacion_destino']
        observaciones = form.cleaned_data['observaciones']
        ubicacion_anterior = lote.ubicacion
        
        # Obtener el content type para LoteProductoTerminado
        content_type = ContentType.objects.get_for_model(LoteProductoTerminado)
        
        if tipo_transferencia == 'TOTAL':
            # Transferencia total del lote
            cantidad_transferir = lote.cantidad_actual
            
            # Crear movimiento de inventario
            MovimientoInventario.objects.create(
                tipo_movimiento='TRANSFERENCIA',
                cantidad=cantidad_transferir,
                ubicacion_origen=ubicacion_anterior,
                ubicacion_destino=ubicacion_destino,
                lote_content_type=content_type,
                lote_object_id=lote.id,
                observaciones=observaciones,
                usuario=self.request.user,
                unidad_medida=lote.unidad_medida_lote
            )
            
            # Actualizar ubicación del lote
            lote.ubicacion = ubicacion_destino
            lote.save()
            
            messages.success(
                self.request, 
                f'Lote {lote.lote_id} transferido completamente de {ubicacion_anterior.nombre} a {ubicacion_destino.nombre}'
            )
        else:  # PARCIAL
            # Transferencia parcial - crear un nuevo lote
            cantidad_transferir = form.cleaned_data['cantidad']
            cantidad_restante = lote.cantidad_actual - cantidad_transferir
            
            with transaction.atomic():
                # Crear un nuevo lote para la cantidad transferida
                nuevo_lote = LoteProductoTerminado.objects.create(
                    producto_terminado=lote.producto_terminado,
                    orden_produccion=lote.orden_produccion,
                    proceso_final_content_type=lote.proceso_final_content_type,
                    proceso_final_object_id=lote.proceso_final_object_id,
                    cantidad_producida=cantidad_transferir,
                    fecha_produccion=lote.fecha_produccion,
                    fecha_vencimiento=lote.fecha_vencimiento,
                    ubicacion=ubicacion_destino,
                    estado='DISPONIBLE',
                    creado_por=self.request.user
                )
                
                # Registrar movimiento de salida del lote original
                MovimientoInventario.objects.create(
                    tipo_movimiento='TRANSFERENCIA_SALIDA',
                    cantidad=cantidad_transferir,
                    ubicacion_origen=ubicacion_anterior,
                    lote_content_type=content_type,
                    lote_object_id=lote.id,
                    observaciones=f"Transferencia parcial: {observaciones}",
                    usuario=self.request.user,
                    unidad_medida=lote.unidad_medida_lote
                )
                
                # Registrar movimiento de entrada al nuevo lote
                MovimientoInventario.objects.create(
                    tipo_movimiento='TRANSFERENCIA_ENTRADA',
                    cantidad=cantidad_transferir,
                    ubicacion_destino=ubicacion_destino,
                    lote_content_type=content_type,
                    lote_object_id=nuevo_lote.id,
                    observaciones=f"Transferencia parcial desde lote {lote.lote_id}: {observaciones}",
                    usuario=self.request.user,
                    unidad_medida=lote.unidad_medida_lote
                )
                
                # Actualizar cantidad del lote original
                lote.cantidad_actual = cantidad_restante
                lote.save()
            
            messages.success(
                self.request, 
                f'Transferencia parcial exitosa: {cantidad_transferir} {lote.unidad_medida_lote.codigo} ' +
                f'del lote {lote.lote_id} transferidos a {ubicacion_destino.nombre} como nuevo lote {nuevo_lote.lote_id}'
            )
        
        return super().form_valid(form)


class ConsumirPTView(LoginRequiredMixin, FormView):
    """Vista para consumir un lote PT."""
    template_name = 'inventario/producto_terminado_consumir.html'
    form_class = ConsumirPTForm
    
    def get_success_url(self):
        return reverse('inventario_web:pt-detail', kwargs={'pk': self.kwargs['pk']})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'lote_id': self.kwargs['pk']}
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        context['lote'] = lote
        context['titulo'] = f'Consumir Lote PT: {lote.lote_id}'
        return context
    
    def form_valid(self, form):
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        cantidad = form.cleaned_data['cantidad']
        documento_referencia = form.cleaned_data['documento_referencia']
        observaciones = form.cleaned_data['observaciones']
        
        # Crear movimiento de inventario
        content_type = ContentType.objects.get_for_model(LoteProductoTerminado)
        
        MovimientoInventario.objects.create(
            tipo_movimiento='CONSUMO',
            cantidad=cantidad,
            ubicacion_origen=lote.ubicacion,
            content_type=content_type,
            object_id=lote.id,
            documento_referencia=documento_referencia,
            observaciones=observaciones,
            usuario=self.request.user
        )
        
        # Actualizar cantidad del lote
        cantidad_anterior = lote.cantidad_actual
        lote.cantidad_actual -= cantidad
        
        # Si la cantidad llega a cero, marcar como consumido
        if lote.cantidad_actual <= 0:
            lote.estado = 'CONSUMIDO'
            lote.cantidad_actual = 0
        
        lote.save()
        
        messages.success(
            self.request, 
            f'Consumo de {cantidad} {lote.unidad_medida_primaria.codigo} del lote {lote.lote_id} registrado exitosamente'
        )
        
        return super().form_valid(form)


class AjustarStockPTView(LoginRequiredMixin, FormView):
    """Vista para ajustar el stock de un lote PT."""
    template_name = 'inventario/producto_terminado_ajustar.html'
    form_class = AjustarStockPTForm
    
    def get_success_url(self):
        return reverse('inventario_web:pt-detail', kwargs={'pk': self.kwargs['pk']})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'lote_id': self.kwargs['pk']}
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        context['lote'] = lote
        context['titulo'] = f'Ajustar Stock Lote PT: {lote.lote_id}'
        return context
    
    def form_valid(self, form):
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        tipo_ajuste = form.cleaned_data['tipo_ajuste']
        cantidad = form.cleaned_data['cantidad']
        observaciones = form.cleaned_data['observaciones']
        
        # Crear movimiento de inventario
        content_type = ContentType.objects.get_for_model(LoteProductoTerminado)
        
        MovimientoInventario.objects.create(
            tipo_movimiento='AJUSTE',
            cantidad=cantidad,
            ubicacion_origen=lote.ubicacion if tipo_ajuste == 'AJUSTE_NEGATIVO' else None,
            ubicacion_destino=lote.ubicacion if tipo_ajuste == 'AJUSTE_POSITIVO' else None,
            lote_content_type=content_type,
            lote_object_id=lote.id,
            observaciones=observaciones,
            usuario=self.request.user,
            unidad_medida=lote.unidad_medida_lote
        )
        
        # Actualizar cantidad del lote
        if tipo_ajuste == 'AJUSTE_POSITIVO':
            lote.cantidad_actual += cantidad
            messages.success(
                self.request, 
                f'Ajuste positivo de {cantidad} {lote.unidad_medida_lote.codigo} aplicado al lote {lote.lote_id}'
            )
        else:  # AJUSTE_NEGATIVO
            lote.cantidad_actual -= cantidad
            if lote.cantidad_actual <= 0:
                lote.estado = 'CONSUMIDO'
                lote.cantidad_actual = 0
            messages.success(
                self.request, 
                f'Ajuste negativo de {cantidad} {lote.unidad_medida_lote.codigo} aplicado al lote {lote.lote_id}'
            )
        
        lote.save()
        
        return super().form_valid(form)


class DespacharPTView(LoginRequiredMixin, FormView):
    """Vista para despachar un lote PT a un cliente."""
    template_name = 'inventario/producto_terminado_despachar.html'
    form_class = DespacharPTForm
    
    def get_success_url(self):
        return reverse_lazy('inventario_web:pt-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        context['lote'] = lote
        context['titulo'] = f'Despachar Lote PT: {lote.lote_id}'
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        
        # Asegurarse de que initial sea un diccionario
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
            
        # Pasar el lote_id a través de initial
        kwargs['initial']['lote_id'] = lote.id
        return kwargs
    
    def form_valid(self, form):
        lote = get_object_or_404(LoteProductoTerminado, pk=self.kwargs['pk'])
        tipo_despacho = form.cleaned_data['tipo_despacho']
        cliente = form.cleaned_data['cliente']
        numero_guia = form.cleaned_data['numero_guia']
        observaciones = form.cleaned_data['observaciones']
        
        # Obtener el content type para LoteProductoTerminado
        content_type = ContentType.objects.get_for_model(LoteProductoTerminado)
        
        if tipo_despacho == 'TOTAL':
            # Despacho total del lote
            cantidad_despachar = lote.cantidad_actual
            
            # Crear movimiento de inventario
            MovimientoInventario.objects.create(
                tipo_movimiento='DESPACHO',
                cantidad=cantidad_despachar,
                ubicacion_origen=lote.ubicacion,
                lote_content_type=content_type,
                lote_object_id=lote.id,
                observaciones=f"Cliente: {cliente.razon_social} (NIT: {cliente.nit}), Guía: {numero_guia}. {observaciones}",
                usuario=self.request.user,
                unidad_medida=lote.unidad_medida_lote
            )
            
            # Actualizar estado del lote
            lote.estado = 'DESPACHADO'
            lote.save()
            
            messages.success(
                self.request, 
                f'Lote {lote.lote_id} despachado completamente al cliente {cliente.razon_social} con guía {numero_guia}'
            )
        else:  # PARCIAL
            # Despacho parcial - crear un nuevo lote para la cantidad restante
            cantidad_despachar = form.cleaned_data['cantidad']
            cantidad_restante = lote.cantidad_actual - cantidad_despachar
            
            with transaction.atomic():
                # Registrar movimiento de despacho
                MovimientoInventario.objects.create(
                    tipo_movimiento='DESPACHO',
                    cantidad=cantidad_despachar,
                    ubicacion_origen=lote.ubicacion,
                    lote_content_type=content_type,
                    lote_object_id=lote.id,
                    observaciones=f"Despacho parcial. Cliente: {cliente.razon_social} (NIT: {cliente.nit}), Guía: {numero_guia}. {observaciones}",
                    usuario=self.request.user,
                    unidad_medida=lote.unidad_medida_lote
                )
                
                if cantidad_restante > 0:
                    # Actualizar cantidad del lote original
                    lote.cantidad_actual = cantidad_restante
                    lote.save()
                    
                    messages.success(
                        self.request, 
                        f'Despacho parcial: {cantidad_despachar} {lote.unidad_medida_lote.codigo} ' +
                        f'del lote {lote.lote_id} despachados al cliente {cliente.razon_social} con guía {numero_guia}. ' +
                        f'Quedan {cantidad_restante} {lote.unidad_medida_lote.codigo} en inventario.'
                    )
                else:
                    # Si no queda nada, marcar como despachado
                    lote.cantidad_actual = 0
                    lote.estado = 'DESPACHADO'
                    lote.save()
                    
                    messages.success(
                        self.request, 
                        f'Lote {lote.lote_id} despachado completamente al cliente {cliente.razon_social} con guía {numero_guia}'
                    )
        
        return super().form_valid(form)


class DespachosListView(LoginRequiredMixin, ListView):
    template_name = 'inventario/despachos_list.html'
    context_object_name = 'despachos'
    paginate_by = 20
    
    def get_queryset(self):
        # Filtrar movimientos de inventario de tipo DESPACHO
        queryset = MovimientoInventario.objects.filter(tipo_movimiento='DESPACHO').order_by('-timestamp')
        
        # Aplicar filtros de búsqueda si existen
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(observaciones__icontains=q) |
                Q(lote_object_id__icontains=q)
            )
        
        # Filtro por fecha
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        
        if fecha_desde:
            fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            queryset = queryset.filter(timestamp__date__gte=fecha_desde)
        
        if fecha_hasta:
            fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            queryset = queryset.filter(timestamp__date__lte=fecha_hasta)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Gestión de Despachos'
        
        # Agregar parámetros de filtrado al contexto
        context['q'] = self.request.GET.get('q', '')
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        
        return context
