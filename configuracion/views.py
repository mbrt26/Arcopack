from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.core.paginator import Paginator
from .models import (
    UnidadMedida, CategoriaMateriaPrima, Ubicacion, 
    Proceso, Maquina, RodilloAnilox, CausaParo, TipoDesperdicio,
    Proveedor, Lamina, Tratamiento, TipoTinta, ProgramaLamina,
    TipoSellado, TipoTroquel, TipoZipper, TipoValvula, 
    TipoImpresion, CuentaContable, Servicio, SubLinea,
    EstadoProducto, CategoriaProducto, SubcategoriaProducto,
    TipoMateriaPrima, TipoMaterial
)

# ===== VISTA PRINCIPAL DE ADMINISTRACIÓN =====
class AdministracionDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Dashboard principal de administración del sistema"""
    template_name = 'configuracion/administracion_dashboard.html'
    permission_required = 'configuracion.view_unidadmedida'  # Permiso básico para ver configuración
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas generales
        context.update({
            'total_unidades_medida': UnidadMedida.objects.count(),
            'total_maquinas': Maquina.objects.count(),
            'maquinas_activas': Maquina.objects.filter(is_active=True).count(),
            'total_ubicaciones': Ubicacion.objects.count(),
            'ubicaciones_activas': Ubicacion.objects.filter(is_active=True).count(),
            'total_proveedores': Proveedor.objects.count(),
            'proveedores_activos': Proveedor.objects.filter(is_active=True).count(),
            'total_procesos': Proceso.objects.count(),
            'total_causas_paro': CausaParo.objects.count(),
            'total_tipos_desperdicio': TipoDesperdicio.objects.count(),
        })
        
        return context

# ===== VISTAS EXISTENTES MEJORADAS =====
class UnidadMedidaListView(LoginRequiredMixin, ListView):
    model = UnidadMedida
    template_name = 'configuracion/unidadmedida_list.html'
    context_object_name = 'unidades'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = UnidadMedida.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) | Q(nombre__icontains=search)
            )
        return queryset.order_by('codigo')

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

class UnidadMedidaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = UnidadMedida
    template_name = 'configuracion/unidadmedida_confirm_delete.html'
    permission_required = 'configuracion.delete_unidadmedida'
    success_url = reverse_lazy('configuracion_web:unidad-medida-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Unidad de medida eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)

# ===== CATEGORÍAS DE MATERIA PRIMA =====
class CategoriaMPListView(LoginRequiredMixin, ListView):
    model = CategoriaMateriaPrima
    template_name = 'configuracion/categoria_mp_list.html'
    context_object_name = 'categorias'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CategoriaMateriaPrima.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | Q(descripcion__icontains=search)
            )
        return queryset.order_by('nombre')

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

class CategoriaMPDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = CategoriaMateriaPrima
    template_name = 'configuracion/categoria_mp_confirm_delete.html'
    permission_required = 'configuracion.delete_categoriamateriaprima'
    success_url = reverse_lazy('configuracion_web:categoria-mp-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Categoría de materia prima eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)

# ===== UBICACIONES =====
class UbicacionListView(LoginRequiredMixin, ListView):
    model = Ubicacion
    template_name = 'configuracion/ubicacion_list.html'
    context_object_name = 'object_list'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Ubicacion.objects.all()
        search = self.request.GET.get('search')
        tipo = self.request.GET.get('tipo')
        activo = self.request.GET.get('activo')
        
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) | Q(nombre__icontains=search) | Q(descripcion__icontains=search)
            )
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if activo:
            queryset = queryset.filter(is_active=activo == 'true')
            
        return queryset.order_by('codigo')

class UbicacionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Ubicacion
    template_name = 'configuracion/ubicacion_form.html'
    fields = ['codigo', 'nombre', 'tipo', 'descripcion', 'is_active']
    success_url = reverse_lazy('configuracion_web:ubicacion-list')
    permission_required = 'configuracion.add_ubicacion'
    
    def form_valid(self, form):
        messages.success(self.request, 'Ubicación creada exitosamente.')
        return super().form_valid(form)

class UbicacionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Ubicacion
    template_name = 'configuracion/ubicacion_form.html'
    fields = ['codigo', 'nombre', 'tipo', 'descripcion', 'is_active']
    success_url = reverse_lazy('configuracion_web:ubicacion-list')
    permission_required = 'configuracion.change_ubicacion'
    
    def form_valid(self, form):
        messages.success(self.request, 'Ubicación actualizada exitosamente.')
        return super().form_valid(form)

class UbicacionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Ubicacion
    template_name = 'configuracion/ubicacion_confirm_delete.html'
    permission_required = 'configuracion.delete_ubicacion'
    success_url = reverse_lazy('configuracion_web:ubicacion-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Ubicación eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)

# ===== PROCESOS =====
class ProcesoListView(LoginRequiredMixin, ListView):
    model = Proceso
    template_name = 'configuracion/proceso_list.html'
    context_object_name = 'object_list'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Proceso.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | Q(descripcion__icontains=search)
            )
        return queryset.order_by('orden_flujo')

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

class ProcesoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Proceso
    template_name = 'configuracion/proceso_confirm_delete.html'
    permission_required = 'configuracion.delete_proceso'
    success_url = reverse_lazy('configuracion_web:proceso-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Proceso eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)

# ===== MÁQUINAS =====
class MaquinaListView(LoginRequiredMixin, ListView):
    model = Maquina
    template_name = 'configuracion/maquina_list.html'
    context_object_name = 'object_list'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Maquina.objects.all()
        search = self.request.GET.get('search')
        tipo = self.request.GET.get('tipo')
        activo = self.request.GET.get('activo')
        
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) | Q(nombre__icontains=search) | 
                Q(marca__icontains=search) | Q(modelo__icontains=search)
            )
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if activo:
            queryset = queryset.filter(is_active=activo == 'true')
            
        return queryset.order_by('codigo')

class MaquinaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Maquina
    template_name = 'configuracion/maquina_form.html'
    fields = ['codigo', 'nombre', 'tipo', 'marca', 'modelo', 'ubicacion_planta', 'is_active'
    ]
    success_url = reverse_lazy('configuracion_web:maquina-list')
    permission_required = 'configuracion.add_maquina'
    
    def form_valid(self, form):
        messages.success(self.request, 'Máquina creada exitosamente.')
        return super().form_valid(form)

class MaquinaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Maquina
    template_name = 'configuracion/maquina_form.html'
    fields = ['codigo', 'nombre', 'tipo', 'marca', 'modelo', 'ubicacion_planta', 'is_active'
    ]
    success_url = reverse_lazy('configuracion_web:maquina-list')
    permission_required = 'configuracion.change_maquina'
    
    def form_valid(self, form):
        messages.success(self.request, 'Máquina actualizada exitosamente.')
        return super().form_valid(form)

class MaquinaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Maquina
    template_name = 'configuracion/maquina_confirm_delete.html'
    permission_required = 'configuracion.delete_maquina'
    success_url = reverse_lazy('configuracion_web:maquina-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Máquina eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)

# ===== PROVEEDORES =====
class ProveedorListView(LoginRequiredMixin, ListView):
    model = Proveedor
    template_name = 'configuracion/proveedor_list.html'
    context_object_name = 'proveedores'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Proveedor.objects.all()
        search = self.request.GET.get('search')
        activo = self.request.GET.get('activo')
        
        if search:
            queryset = queryset.filter(
                Q(nit__icontains=search) | Q(razon_social__icontains=search) | 
                Q(nombre_comercial__icontains=search) | Q(ciudad__icontains=search)
            )
        if activo:
            queryset = queryset.filter(is_active=activo == 'true')
            
        return queryset.order_by('razon_social')

class ProveedorCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Proveedor
    template_name = 'configuracion/proveedor_form.html'
    fields = ['nit', 'razon_social', 'nombre_comercial', 'direccion', 'ciudad', 
              'telefono', 'email', 'contacto_principal', 'dias_credito', 'is_active']
    success_url = reverse_lazy('configuracion_web:proveedor-list')
    permission_required = 'configuracion.add_proveedor'
    
    def form_valid(self, form):
        messages.success(self.request, 'Proveedor creado exitosamente.')
        return super().form_valid(form)

class ProveedorUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Proveedor
    template_name = 'configuracion/proveedor_form.html'
    fields = ['nit', 'razon_social', 'nombre_comercial', 'direccion', 'ciudad', 
              'telefono', 'email', 'contacto_principal', 'dias_credito', 'is_active']
    success_url = reverse_lazy('configuracion_web:proveedor-list')
    permission_required = 'configuracion.change_proveedor'
    
    def form_valid(self, form):
        messages.success(self.request, 'Proveedor actualizado exitosamente.')
        return super().form_valid(form)

class ProveedorDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Proveedor
    template_name = 'configuracion/proveedor_confirm_delete.html'
    permission_required = 'configuracion.delete_proveedor'
    success_url = reverse_lazy('configuracion_web:proveedor-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Proveedor eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)

# ===== NUEVAS VISTAS PARA OTROS MODELOS =====

# Rodillos Anilox
class RodilloAniloxListView(LoginRequiredMixin, ListView):
    model = RodilloAnilox
    template_name = 'configuracion/rodillo_anilox_list.html'
    context_object_name = 'rodillos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = RodilloAnilox.objects.all()
        search = self.request.GET.get('search')
        activo = self.request.GET.get('activo')
        
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) | Q(descripcion__icontains=search)
            )
        if activo:
            queryset = queryset.filter(is_active=activo == 'true')
            
        return queryset.order_by('codigo')

class RodilloAniloxCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = RodilloAnilox
    template_name = 'configuracion/rodillo_anilox_form.html'
    fields = ['codigo', 'lineatura', 'volumen', 'descripcion', 'estado', 'is_active']
    success_url = reverse_lazy('configuracion_web:rodillo-anilox-list')
    permission_required = 'configuracion.add_rodilloanilox'
    
    def form_valid(self, form):
        messages.success(self.request, 'Rodillo Anilox creado exitosamente.')
        return super().form_valid(form)

class RodilloAniloxUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = RodilloAnilox
    template_name = 'configuracion/rodillo_anilox_form.html'
    fields = ['codigo', 'lineatura', 'volumen', 'descripcion', 'estado', 'is_active']
    success_url = reverse_lazy('configuracion_web:rodillo-anilox-list')
    permission_required = 'configuracion.change_rodilloanilox'
    
    def form_valid(self, form):
        messages.success(self.request, 'Rodillo Anilox actualizado exitosamente.')
        return super().form_valid(form)

# Causas de Paro
class CausaParoListView(LoginRequiredMixin, ListView):
    model = CausaParo
    template_name = 'configuracion/causa_paro_list.html'
    context_object_name = 'causas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CausaParo.objects.all()
        search = self.request.GET.get('search')
        tipo = self.request.GET.get('tipo')
        
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) | Q(descripcion__icontains=search)
            )
        if tipo:
            queryset = queryset.filter(tipo=tipo)
            
        return queryset.order_by('tipo', 'codigo')

class CausaParoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CausaParo
    template_name = 'configuracion/causa_paro_form.html'
    fields = ['codigo', 'descripcion', 'tipo', 'aplica_a', 'requiere_observacion']
    success_url = reverse_lazy('configuracion_web:causa-paro-list')
    permission_required = 'configuracion.add_causaparo'
    
    def form_valid(self, form):
        messages.success(self.request, 'Causa de paro creada exitosamente.')
        return super().form_valid(form)

class CausaParoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CausaParo
    template_name = 'configuracion/causa_paro_form.html'
    fields = ['codigo', 'descripcion', 'tipo', 'aplica_a', 'requiere_observacion']
    success_url = reverse_lazy('configuracion_web:causa-paro-list')
    permission_required = 'configuracion.change_causaparo'
    
    def form_valid(self, form):
        messages.success(self.request, 'Causa de paro actualizada exitosamente.')
        return super().form_valid(form)

# Tipos de Desperdicio
class TipoDesperdicioListView(LoginRequiredMixin, ListView):
    model = TipoDesperdicio
    template_name = 'configuracion/tipo_desperdicio_list.html'
    context_object_name = 'tipos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = TipoDesperdicio.objects.all()
        search = self.request.GET.get('search')
        
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) | Q(descripcion__icontains=search)
            )
            
        return queryset.order_by('codigo')

class TipoDesperdicioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = TipoDesperdicio
    template_name = 'configuracion/tipo_desperdicio_form.html'
    fields = ['codigo', 'descripcion', 'es_recuperable']
    success_url = reverse_lazy('configuracion_web:tipo-desperdicio-list')
    permission_required = 'configuracion.add_tipodesperdicio'
    
    def form_valid(self, form):
        messages.success(self.request, 'Tipo de desperdicio creado exitosamente.')
        return super().form_valid(form)

class TipoDesperdicioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = TipoDesperdicio
    template_name = 'configuracion/tipo_desperdicio_form.html'
    fields = ['codigo', 'descripcion', 'es_recuperable']
    success_url = reverse_lazy('configuracion_web:tipo-desperdicio-list')
    permission_required = 'configuracion.change_tipodesperdicio'
    
    def form_valid(self, form):
        messages.success(self.request, 'Tipo de desperdicio actualizado exitosamente.')
        return super().form_valid(form)

# ===== VISTAS GENÉRICAS PARA MODELOS SIMPLES =====

def create_simple_model_views(model_class, template_prefix, url_prefix, permission_prefix):
    """Factory function para crear vistas CRUD para modelos simples"""
    
    class SimpleListView(LoginRequiredMixin, ListView):
        model = model_class
        template_name = f'configuracion/{template_prefix}_list.html'
        context_object_name = 'objects'
        paginate_by = 20
        
        def get_queryset(self):
            queryset = model_class.objects.all()
            search = self.request.GET.get('search')
            if search and hasattr(model_class, 'nombre'):
                queryset = queryset.filter(nombre__icontains=search)
            return queryset.order_by('nombre')
    
    class SimpleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
        model = model_class
        template_name = f'configuracion/{template_prefix}_form.html'
        fields = '__all__'
        success_url = reverse_lazy(f'configuracion_web:{url_prefix}-list')
        permission_required = f'configuracion.add_{permission_prefix}'
        
        def form_valid(self, form):
            messages.success(self.request, f'{model_class._meta.verbose_name} creado exitosamente.')
            return super().form_valid(form)
    
    class SimpleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
        model = model_class
        template_name = f'configuracion/{template_prefix}_form.html'
        fields = '__all__'
        success_url = reverse_lazy(f'configuracion_web:{url_prefix}-list')
        permission_required = f'configuracion.change_{permission_prefix}'
        
        def form_valid(self, form):
            messages.success(self.request, f'{model_class._meta.verbose_name} actualizado exitosamente.')
            return super().form_valid(form)
    
    return SimpleListView, SimpleCreateView, SimpleUpdateView

# Crear vistas para modelos simples
LaminaListView, LaminaCreateView, LaminaUpdateView = create_simple_model_views(
    Lamina, 'lamina', 'lamina', 'lamina'
)

TratamientoListView, TratamientoCreateView, TratamientoUpdateView = create_simple_model_views(
    Tratamiento, 'tratamiento', 'tratamiento', 'tratamiento'
)

TipoTintaListView, TipoTintaCreateView, TipoTintaUpdateView = create_simple_model_views(
    TipoTinta, 'tipo_tinta', 'tipo-tinta', 'tipotinta'
)

ProgramaLaminaListView, ProgramaLaminaCreateView, ProgramaLaminaUpdateView = create_simple_model_views(
    ProgramaLamina, 'programa_lamina', 'programa-lamina', 'programalamina'
)

TipoSelladoListView, TipoSelladoCreateView, TipoSelladoUpdateView = create_simple_model_views(
    TipoSellado, 'tipo_sellado', 'tipo-sellado', 'tiposellado'
)

TipoTroquelListView, TipoTroquelCreateView, TipoTroquelUpdateView = create_simple_model_views(
    TipoTroquel, 'tipo_troquel', 'tipo-troquel', 'tipotroquel'
)

TipoZipperListView, TipoZipperCreateView, TipoZipperUpdateView = create_simple_model_views(
    TipoZipper, 'tipo_zipper', 'tipo-zipper', 'tipozipper'
)

TipoValvulaListView, TipoValvulaCreateView, TipoValvulaUpdateView = create_simple_model_views(
    TipoValvula, 'tipo_valvula', 'tipo-valvula', 'tipovalvula'
)

TipoImpresionListView, TipoImpresionCreateView, TipoImpresionUpdateView = create_simple_model_views(
    TipoImpresion, 'tipo_impresion', 'tipo-impresion', 'tipoimpresion'
)

ServicioListView, ServicioCreateView, ServicioUpdateView = create_simple_model_views(
    Servicio, 'servicio', 'servicio', 'servicio'
)

SubLineaListView, SubLineaCreateView, SubLineaUpdateView = create_simple_model_views(
    SubLinea, 'sublinea', 'sublinea', 'sublinea'
)

EstadoProductoListView, EstadoProductoCreateView, EstadoProductoUpdateView = create_simple_model_views(
    EstadoProducto, 'estado_producto', 'estado-producto', 'estadoproducto'
)

CategoriaProductoListView, CategoriaProductoCreateView, CategoriaProductoUpdateView = create_simple_model_views(
    CategoriaProducto, 'categoria_producto', 'categoria-producto', 'categoriaproducto'
)

TipoMateriaPrimaListView, TipoMateriaPrimaCreateView, TipoMateriaPrimaUpdateView = create_simple_model_views(
    TipoMateriaPrima, 'tipo_materia_prima', 'tipo-materia-prima', 'tipomateriaprima'
)

TipoMaterialListView, TipoMaterialCreateView, TipoMaterialUpdateView = create_simple_model_views(
    TipoMaterial, 'tipo_material', 'tipo-material', 'tipomaterial'
)

# Cuenta Contable
class CuentaContableListView(LoginRequiredMixin, ListView):
    model = CuentaContable
    template_name = 'configuracion/cuenta_contable_list.html'
    context_object_name = 'cuentas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CuentaContable.objects.all()
        search = self.request.GET.get('search')
        naturaleza = self.request.GET.get('naturaleza')
        
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) | Q(nombre__icontains=search)
            )
        if naturaleza:
            queryset = queryset.filter(naturaleza=naturaleza)
            
        return queryset.order_by('codigo')

class CuentaContableCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CuentaContable
    template_name = 'configuracion/cuenta_contable_form.html'
    fields = ['codigo', 'nombre', 'naturaleza']
    success_url = reverse_lazy('configuracion_web:cuenta-contable-list')
    permission_required = 'configuracion.add_cuentacontable'
    
    def form_valid(self, form):
        messages.success(self.request, 'Cuenta contable creada exitosamente.')
        return super().form_valid(form)

class CuentaContableUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CuentaContable
    template_name = 'configuracion/cuenta_contable_form.html'
    fields = ['codigo', 'nombre', 'naturaleza']
    success_url = reverse_lazy('configuracion_web:cuenta-contable-list')
    permission_required = 'configuracion.change_cuentacontable'
    
    def form_valid(self, form):
        messages.success(self.request, 'Cuenta contable actualizada exitosamente.')
        return super().form_valid(form)
