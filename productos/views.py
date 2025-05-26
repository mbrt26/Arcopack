# productos/views.py

import logging
from rest_framework import viewsets, permissions, status # Importar componentes DRF
from rest_framework.response import Response # Para respuestas API personalizadas
from rest_framework.exceptions import ValidationError # Para errores de validación API

from .models import ProductoTerminado # Importar el modelo de esta app
from .serializers import ProductoTerminadoSerializer # Importar el serializer que creamos
from produccion.models import OrdenProduccion # Importar para validar cambio de código

logger = logging.getLogger(__name__)

# Opcional: Para filtros y búsqueda en la API
# from rest_framework import filters
# from django_filters.rest_framework import DjangoFilterBackend

class ProductoTerminadoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para ver y editar Productos Terminados vía API.

    Proporciona acciones `list`, `create`, `retrieve`, `update`,
    `partial_update`, y `destroy` (implementado como soft-delete).
    """
    # 1. Queryset Base: Define qué objetos estarán disponibles.
    #    Filtramos por activos por defecto.
    queryset = ProductoTerminado.objects.filter(is_active=True)

    # 2. Serializer Class: Indica qué serializer usar para este modelo.
    serializer_class = ProductoTerminadoSerializer

    # 3. Permisos: Define quién puede acceder a esta API.
    #    IsAuthenticated requiere que el usuario haya iniciado sesión.
    #    Podemos crear permisos más específicos luego (ej. solo lectura para algunos).
    permission_classes = [permissions.IsAuthenticated]

    # --- Opcional: Habilitar Filtros/Búsqueda/Ordenación en API ---
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['codigo', 'nombre', 'categoria', 'estado'] # Campos para filtro exacto ?categoria=1
    # search_fields = ['codigo', 'nombre'] # Campos para búsqueda ?search=texto
    # ordering_fields = ['codigo', 'nombre', 'actualizado_en'] # Campos para ordenar ?ordering=nombre
    # ordering = ['codigo'] # Orden por defecto

    # --- Sobrescribir Métodos para Añadir Lógica ---

    def perform_create(self, serializer):
        """Asigna el usuario creador al guardar un nuevo producto."""
        # Guarda la instancia pasando el usuario logueado como creador
        serializer.save(creado_por=self.request.user, actualizado_por=self.request.user)
        # Nota: serializer.save() llamará al método save() del modelo ProductoTerminado

    def perform_update(self, serializer):
        """
        Asigna el usuario que actualiza y valida reglas de negocio
        antes de guardar la actualización.
        """
        instance = serializer.instance # El producto existente antes del cambio
        validated_data = serializer.validated_data # Los datos nuevos validados

        # --- VALIDACIÓN: Prevenir cambio de código si hay OPs ---
        # Este es el lugar ideal para esta regla de negocio en la API
        nuevo_codigo = validated_data.get('codigo', instance.codigo)
        if instance.codigo != nuevo_codigo:
             # Usar el método helper del modelo para chequear OPs
             if OrdenProduccion.objects.filter(producto=instance).exists():
                  # Lanzar un error de validación específico de DRF
                  raise ValidationError({
                      'codigo': "No se puede cambiar el código de un producto con Órdenes de Producción asociadas."
                  })
        # ----------------------------------------------------

        # Guarda la instancia pasando el usuario logueado como actualizador
        serializer.save(actualizado_por=self.request.user)

    def perform_destroy(self, instance: ProductoTerminado):
        """Realiza un borrado lógico (soft-delete) en lugar de borrar físicamente."""
        if instance.is_active:
            instance.is_active = False
            instance.save(user=self.request.user) # Pasar usuario para actualizar 'actualizado_por'
            logger.info(f"Producto Terminado '{instance.codigo}' desactivado por usuario '{self.request.user}'.")
        # Si ya está inactivo, no hacemos nada o podríamos devolver un error diferente
        # Por defecto, DRF devolverá 204 No Content igualmente.

    # Opcional: Si quisiéramos manejar la reactivación, podríamos añadir una acción personalizada
    # from rest_framework.decorators import action
    # @action(detail=True, methods=['post'])
    # def reactivar(self, request, pk=None):
    #    instance = self.get_object()
    #    instance.is_active = True
    #    instance.save(user=request.user)
    #    serializer = self.get_serializer(instance)


from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .forms import ProductoTerminadoForm, ProductoSearchForm


class ProductoListView(LoginRequiredMixin, ListView):
    model = ProductoTerminado
    template_name = 'productos/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by('codigo')
        self.search_form = ProductoSearchForm(self.request.GET)
        if self.search_form.is_valid():
            q = self.search_form.cleaned_data.get('q')
            if q:
                qs = qs.filter(Q(codigo__icontains=q) | Q(nombre__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = []
        for obj in context['productos']:
            items.append({
                'id': obj.id,
                'name': obj.nombre,
                'is_active': obj.is_active,
                'fields': [
                    {'value': obj.codigo, 'type': 'code'},
                    {'value': obj.nombre},
                    {'value': obj.cliente.razon_social if obj.cliente else '-', 'type': 'text'},
                    {'value': obj.get_estado_display(), 'type': 'badge', 'class': 'bg-success' if obj.is_active else 'bg-danger'},
                ]
            })
        context.update({
            'producto_headers': ['Código', 'Nombre', 'Cliente', 'Estado'],
            'producto_actions': {
                'view': 'productos_web:producto_detail',
                'edit': 'productos_web:producto_update',
                'duplicate': 'productos_web:producto_duplicate',
                'delete': 'productos_web:producto_delete',
            },
            'productos': items,
            'filter': self.search_form,
        })
        return context


class ProductoDetailView(LoginRequiredMixin, DetailView):
    model = ProductoTerminado
    template_name = 'productos/producto_detail.html'
    context_object_name = 'producto'


class ProductoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ProductoTerminado
    form_class = ProductoTerminadoForm
    template_name = 'productos/producto_form.html'
    permission_required = 'productos.add_productoterminado'

    def form_valid(self, form):
        messages.success(self.request, 'Producto creado correctamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('productos_web:producto_detail', kwargs={'pk': self.object.pk})


class ProductoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = ProductoTerminado
    form_class = ProductoTerminadoForm
    template_name = 'productos/producto_form.html'
    permission_required = 'productos.change_productoterminado'

    def form_valid(self, form):
        messages.success(self.request, 'Producto actualizado correctamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('productos_web:producto_detail', kwargs={'pk': self.object.pk})


class ProductoDuplicateView(ProductoCreateView):
    permission_required = 'productos.add_productoterminado'

    def get_initial(self):
        original = get_object_or_404(ProductoTerminado, pk=self.kwargs['pk'])
        initial = {f.name: getattr(original, f.name) for f in ProductoTerminado._meta.fields
                    if f.name not in ('id', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por')}
        initial['codigo'] = ''
        return initial


class ProductoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ProductoTerminado
    permission_required = 'productos.delete_productoterminado'
    success_url = reverse_lazy('productos_web:producto_list')
    template_name = 'productos/confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Producto eliminado correctamente.')
        return super().delete(request, *args, **kwargs)
