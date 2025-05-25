from django.shortcuts import render
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import (
    UnidadMedida, CategoriaMateriaPrima, Ubicacion, 
    Proceso, Maquina
)

class UnidadMedidaListView(LoginRequiredMixin, ListView):
    model = UnidadMedida
    template_name = 'configuracion/unidad_medida_list.html'
    context_object_name = 'unidades'
    
    def get_queryset(self):
        return UnidadMedida.objects.all().order_by('codigo')

class CategoriaMPListView(LoginRequiredMixin, ListView):
    model = CategoriaMateriaPrima
    template_name = 'configuracion/categoria_mp_list.html'
    context_object_name = 'categorias'
    
    def get_queryset(self):
        return CategoriaMateriaPrima.objects.all().order_by('nombre')

class UbicacionListView(LoginRequiredMixin, ListView):
    model = Ubicacion
    template_name = 'configuracion/ubicacion_list.html'
    context_object_name = 'ubicaciones'
    
    def get_queryset(self):
        return Ubicacion.objects.filter(is_active=True).order_by('codigo')

class ProcesoListView(LoginRequiredMixin, ListView):
    model = Proceso
    template_name = 'configuracion/proceso_list.html'
    context_object_name = 'procesos'
    
    def get_queryset(self):
        return Proceso.objects.all().order_by('orden_flujo', 'nombre')

class MaquinaListView(LoginRequiredMixin, ListView):
    model = Maquina
    template_name = 'configuracion/maquina_list.html'
    context_object_name = 'maquinas'
    
    def get_queryset(self):
        return Maquina.objects.filter(is_active=True).order_by('codigo')
