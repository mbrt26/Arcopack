from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q

from .models import Colaborador


class ColaboradorListView(LoginRequiredMixin, ListView):
    """Vista para listar todos los colaboradores."""
    model = Colaborador
    context_object_name = 'colaboradores'
    template_name = 'personal/lists/colaborador_list.html'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Aplicar filtros de búsqueda si existen
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(cedula__icontains=search_query) |
                Q(nombres__icontains=search_query) |
                Q(apellidos__icontains=search_query) |
                Q(cargo__icontains=search_query)
            )
        return queryset.order_by('apellidos', 'nombres')


class ColaboradorDetailView(LoginRequiredMixin, DetailView):
    """Vista para ver los detalles de un colaborador específico."""
    model = Colaborador
    context_object_name = 'colaborador'
    template_name = 'personal/details/colaborador_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar datos adicionales al contexto si es necesario
        return context


class ColaboradorCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un nuevo colaborador."""
    model = Colaborador
    fields = [
        'nombres', 'apellidos', 'cedula', 'codigo_empleado',
        'cargo', 'area', 'fecha_ingreso', 'fecha_retiro',
        'usuario_sistema', 'is_active'
    ]
    template_name = 'personal/forms/colaborador_form.html'
    permission_required = 'personal.add_colaborador'
    
    def form_valid(self, form):
        messages.success(self.request, 'Colaborador creado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('personal:colaborador_detail', kwargs={'pk': self.object.pk})


class ColaboradorUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para editar un colaborador existente."""
    model = Colaborador
    fields = [
        'nombres', 'apellidos', 'cedula', 'codigo_empleado',
        'cargo', 'area', 'fecha_ingreso', 'fecha_retiro',
        'usuario_sistema', 'is_active'
    ]
    template_name = 'personal/forms/colaborador_form.html'
    permission_required = 'personal.change_colaborador'
    
    def form_valid(self, form):
        messages.success(self.request, 'Colaborador actualizado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('personal:colaborador_detail', kwargs={'pk': self.object.pk})


class ColaboradorDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar un colaborador."""
    model = Colaborador
    template_name = 'personal/confirm_delete.html'
    success_url = reverse_lazy('personal:colaborador_list')
    permission_required = 'personal.delete_colaborador'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Colaborador eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)
