from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Cliente


class ClienteListView(LoginRequiredMixin, ListView):
    """Vista para listar todos los clientes."""
    model = Cliente
    context_object_name = 'clientes'
    template_name = 'clientes/cliente_list.html'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Aplicar filtros de búsqueda si existen
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(nit__icontains=search_query) |
                Q(razon_social__icontains=search_query) |
                Q(nombre_comercial__icontains=search_query) |
                Q(ciudad__icontains=search_query)
            )
        return queryset.order_by('razon_social')


class ClienteDetailView(LoginRequiredMixin, DetailView):
    """Vista para ver los detalles de un cliente específico."""
    model = Cliente
    context_object_name = 'cliente'
    template_name = 'clientes/cliente_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar datos adicionales al contexto si es necesario
        # context['pedidos'] = self.object.pedido_set.all()[:5]  # Ejemplo: últimos 5 pedidos
        return context


class ClienteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un nuevo cliente."""
    model = Cliente
    fields = [
        'nit', 'razon_social', 'nombre_comercial',
        'direccion_principal', 'ciudad', 'departamento', 'pais',
        'telefono_principal', 'email_principal',
        'nombre_contacto_principal', 'email_contacto_principal',
        'condiciones_pago', 'cupo_credito', 'activo'
    ]
    template_name = 'clientes/cliente_form.html'
    permission_required = 'clientes.add_cliente'
    
    def form_valid(self, form):
        messages.success(self.request, 'Cliente creado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('clientes:cliente_detail', kwargs={'pk': self.object.pk})


class ClienteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para editar un cliente existente."""
    model = Cliente
    fields = [
        'nit', 'razon_social', 'nombre_comercial',
        'direccion_principal', 'ciudad', 'departamento', 'pais',
        'telefono_principal', 'email_principal',
        'nombre_contacto_principal', 'email_contacto_principal',
        'condiciones_pago', 'cupo_credito', 'activo'
    ]
    template_name = 'clientes/cliente_form.html'
    permission_required = 'clientes.change_cliente'
    
    def form_valid(self, form):
        messages.success(self.request, 'Cliente actualizado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('clientes:cliente_detail', kwargs={'pk': self.object.pk})


class ClienteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar un cliente."""
    model = Cliente
    template_name = 'clientes/confirm_delete.html'
    success_url = reverse_lazy('clientes:cliente_list')
    permission_required = 'clientes.delete_cliente'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Cliente eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)
