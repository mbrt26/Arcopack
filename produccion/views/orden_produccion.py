# produccion/views/orden_produccion.py
"""
Vistas específicas para la gestión de Órdenes de Producción.
Incluye vistas HTML y ViewSets para la API REST.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from rest_framework.exceptions import ValidationError as DRFValidationError

from .base import BaseProduccionViewSet, logger
from ..models import OrdenProduccion
from ..serializers import OrdenProduccionSerializer
from ..forms import OrdenProduccionForm


# =============================================
# === VISTAS HTML PARA ORDEN DE PRODUCCIÓN ===
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
    return redirect('produccion_web:orden-produccion-list')


class OrdenProduccionCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear una nueva Orden de Producción."""
    model = OrdenProduccion
    form_class = OrdenProduccionForm
    template_name = 'produccion/orden_produccion_form.html'
    success_url = reverse_lazy('produccion_web:orden-produccion-list')
    
    def form_valid(self, form):
        """Asigna el usuario creador."""
        form.instance.creado_por = self.request.user
        form.instance.actualizado_por = self.request.user
        messages.success(
            self.request, 
            f'Orden de Producción {form.instance.op_numero} creada exitosamente.'
        )
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Nueva Orden de Producción'
        context['form_action'] = 'Crear'
        return context


class OrdenProduccionUpdateView(LoginRequiredMixin, UpdateView):
    """Vista para actualizar una Orden de Producción existente."""
    model = OrdenProduccion
    form_class = OrdenProduccionForm
    template_name = 'produccion/orden_produccion_form.html'
    success_url = reverse_lazy('produccion_web:orden-produccion-list')
    
    def get_queryset(self):
        return OrdenProduccion.objects.filter(is_active=True)
    
    def form_valid(self, form):
        """Actualiza el usuario modificador."""
        form.instance.actualizado_por = self.request.user
        messages.success(
            self.request, 
            f'Orden de Producción {form.instance.op_numero} actualizada exitosamente.'
        )
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Editar OP: {self.object.op_numero}'
        context['form_action'] = 'Actualizar'
        return context


# =============================================
# === VIEWSET PARA ORDEN DE PRODUCCIÓN ===
# =============================================

class OrdenProduccionViewSet(BaseProduccionViewSet):
    """ViewSet CRUD básico para Ordenes de Producción."""
    queryset = OrdenProduccion.objects.filter(is_active=True).select_related(
        'cliente', 'producto', 'sustrato', 'creado_por', 'actualizado_por'
    ).prefetch_related('procesos')
    serializer_class = OrdenProduccionSerializer

    # Opcional: Filtros/Búsqueda/Ordenación
    # filter_backends = [...]
    # filterset_fields = [...]
    # search_fields = [...]
    # ordering_fields = [...]
    # ordering = [...]

    def perform_update(self, serializer):
        """Asigna usuario actualizador y valida cambio de código."""
        instance = serializer.instance
        validated_data = serializer.validated_data
        nuevo_codigo = validated_data.get('codigo', instance.codigo)
        
        # Validar cambio de código (aunque también está en Serializer/Modelo)
        if instance.codigo != nuevo_codigo and instance._has_related_orders():
            raise DRFValidationError({
                'codigo': "No se puede cambiar código si OP tiene registros asociados."
            })
        
        serializer.save(actualizado_por=self.request.user)

    def perform_destroy(self, instance: OrdenProduccion):
        """Soft delete: Marca como Anulada e inactiva."""
        if instance.is_active:
            instance.is_active = False
            instance.etapa_actual = 'ANUL'
            instance.save(user=self.request.user)
            logger.info(f"Orden Producción '{instance.op_numero}' anulada por usuario '{self.request.user}'.")