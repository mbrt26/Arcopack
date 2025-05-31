from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import (
    UnidadMedida, CategoriaMateriaPrima, Ubicacion, 
    Proceso, Maquina
)

class UnidadMedidaListView(LoginRequiredMixin, ListView):
    model = UnidadMedida
    template_name = 'configuracion/unidadmedida_list.html'
    context_object_name = 'unidades'
    
    def get_queryset(self):
        return UnidadMedida.objects.all().order_by('codigo')


class UnidadMedidaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = UnidadMedida
    fields = ['codigo', 'nombre']
    template_name = 'configuracion/unidadmedida_form.html'
    permission_required = 'configuracion.add_unidadmedida'
    success_url = reverse_lazy('configuracion_web:unidad-medida-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Unidad de medida creada exitosamente.')
        return super().form_valid(form)


class UnidadMedidaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = UnidadMedida
    fields = ['codigo', 'nombre']
    template_name = 'configuracion/unidadmedida_form.html'
    permission_required = 'configuracion.change_unidadmedida'
    success_url = reverse_lazy('configuracion_web:unidad-medida-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Unidad de medida actualizada exitosamente.')
        return super().form_valid(form)


class CategoriaMPListView(LoginRequiredMixin, ListView):
    model = CategoriaMateriaPrima
    template_name = 'configuracion/categoria_mp_list.html'
    context_object_name = 'categorias'
    
    def get_queryset(self):
        return CategoriaMateriaPrima.objects.all().order_by('nombre')


class CategoriaMPCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CategoriaMateriaPrima
    fields = ['nombre', 'descripcion']
    template_name = 'configuracion/categoria_mp_form.html'
    permission_required = 'configuracion.add_categoriamateriaprima'
    success_url = reverse_lazy('configuracion_web:categoria-mp-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Categoría de materia prima creada exitosamente.')
        return super().form_valid(form)


class CategoriaMPUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CategoriaMateriaPrima
    fields = ['nombre', 'descripcion']
    template_name = 'configuracion/categoria_mp_form.html'
    permission_required = 'configuracion.change_categoriamateriaprima'
    success_url = reverse_lazy('configuracion_web:categoria-mp-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Categoría de materia prima actualizada exitosamente.')
        return super().form_valid(form)


class UbicacionListView(LoginRequiredMixin, ListView):
    model = Ubicacion
    template_name = 'configuracion/ubicacion_list.html'
    context_object_name = 'object_list'
    paginate_by = 20
    
    def get_queryset(self):
        return Ubicacion.objects.all().order_by('codigo')

class UbicacionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Ubicacion
    template_name = 'configuracion/ubicacion_form.html'
    fields = ['codigo', 'nombre', 'descripcion', 'is_active']
    success_url = reverse_lazy('configuracion_web:ubicacion-list')
    permission_required = 'configuracion.add_ubicacion'
    
    def form_valid(self, form):
        messages.success(self.request, 'Ubicación creada exitosamente.')
        return super().form_valid(form)

class UbicacionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Ubicacion
    template_name = 'configuracion/ubicacion_form.html'
    fields = ['codigo', 'nombre', 'descripcion', 'is_active']
    success_url = reverse_lazy('configuracion_web:ubicacion-list')
    permission_required = 'configuracion.change_ubicacion'
    
    def form_valid(self, form):
        messages.success(self.request, 'Ubicación actualizada exitosamente.')
        return super().form_valid(form)


class ProcesoListView(LoginRequiredMixin, ListView):
    model = Proceso
    template_name = 'configuracion/proceso_list.html'
    context_object_name = 'object_list'
    paginate_by = 20
    
    def get_queryset(self):
        return Proceso.objects.all().order_by('orden_flujo')

class ProcesoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Proceso
    template_name = 'configuracion/proceso_form.html'
    fields = ['nombre', 'descripcion', 'orden_flujo']
    success_url = reverse_lazy('configuracion_web:proceso-list')
    permission_required = 'configuracion.add_proceso'
    
    def form_valid(self, form):
        messages.success(self.request, 'Proceso creado exitosamente.')
        return super().form_valid(form)

class ProcesoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Proceso
    template_name = 'configuracion/proceso_form.html'
    fields = ['nombre', 'descripcion', 'orden_flujo']
    success_url = reverse_lazy('configuracion_web:proceso-list')
    permission_required = 'configuracion.change_proceso'
    
    def form_valid(self, form):
        messages.success(self.request, 'Proceso actualizado exitosamente.')
        return super().form_valid(form)


class MaquinaListView(LoginRequiredMixin, ListView):
    model = Maquina
    template_name = 'configuracion/maquina_list.html'
    context_object_name = 'object_list'
    paginate_by = 20
    
    def get_queryset(self):
        return Maquina.objects.all().order_by('codigo')

class MaquinaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Maquina
    template_name = 'configuracion/maquina_form.html'
    fields = ['codigo', 'nombre', 'tipo', 'marca', 'modelo', 'ubicacion_planta', 'is_active']
    success_url = reverse_lazy('configuracion_web:maquina-list')
    permission_required = 'configuracion.add_maquina'
    
    def form_valid(self, form):
        messages.success(self.request, 'Máquina creada exitosamente.')
        return super().form_valid(form)

class MaquinaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Maquina
    template_name = 'configuracion/maquina_form.html'
    fields = ['codigo', 'nombre', 'tipo', 'marca', 'modelo', 'ubicacion_planta', 'is_active']
    success_url = reverse_lazy('configuracion_web:maquina-list')
    permission_required = 'configuracion.change_maquina'
    
    def form_valid(self, form):
        messages.success(self.request, 'Máquina actualizada exitosamente.')
        return super().form_valid(form)
