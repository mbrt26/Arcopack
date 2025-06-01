from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.forms import inlineformset_factory
from django.db import transaction

from .models import (
    Maquina, TipoMaquina, Anilox, TipoTinta, TipoSustrato,
    Proveedor, Cliente, Producto, ConfiguracionGeneral
)
from .forms import (
    MaquinaForm, TipoMaquinaForm, AniloxForm, TipoTintaForm,
    TipoSustratoForm, ProveedorForm, ClienteForm, ProductoForm,
    ConfiguracionGeneralForm
)


def is_admin_user(user):
    """Verificar si el usuario tiene permisos de administrador"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(is_admin_user)
def admin_dashboard(request):
    """Dashboard principal de administración"""
    context = {
        'title': 'Panel de Administración',
        'stats': {
            'maquinas': Maquina.objects.count(),
            'maquinas_activas': Maquina.objects.filter(is_active=True).count(),
            'proveedores': Proveedor.objects.count(),
            'productos': Producto.objects.count(),
            'clientes': Cliente.objects.count(),
        },
        'recent_activities': []  # Aquí se pueden agregar actividades recientes
    }
    return render(request, 'configuracion/admin_dashboard.html', context)


# ===========================================
# VISTAS PARA MÁQUINAS
# ===========================================

class AdminUserRequiredMixin(UserPassesTestMixin):
    """Mixin para requerir permisos de administrador"""
    def test_func(self):
        return is_admin_user(self.request.user)


class MaquinaListView(LoginRequiredMixin, AdminUserRequiredMixin, ListView):
    """Lista de máquinas con filtros y búsqueda"""
    model = Maquina
    template_name = 'configuracion/maquina_list.html'
    context_object_name = 'maquinas'
    paginate_by = 20

    def get_queryset(self):
        queryset = Maquina.objects.all().select_related('tipo')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(codigo__icontains=search) |
                Q(marca__icontains=search)
            )
        
        tipo_filter = self.request.GET.get('tipo')
        if tipo_filter:
            queryset = queryset.filter(tipo__codigo=tipo_filter)
        
        estado_filter = self.request.GET.get('estado')
        if estado_filter == 'activo':
            queryset = queryset.filter(is_active=True)
        elif estado_filter == 'inactivo':
            queryset = queryset.filter(is_active=False)
        
        # Ordenamiento
        order_by = self.request.GET.get('order_by', 'nombre')
        if order_by in ['nombre', 'codigo', 'tipo__nombre', 'created_at']:
            queryset = queryset.order_by(order_by)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Gestión de Máquinas'
        context['tipos_maquina'] = TipoMaquina.objects.all()
        context['search'] = self.request.GET.get('search', '')
        context['current_filters'] = {
            'tipo': self.request.GET.get('tipo', ''),
            'estado': self.request.GET.get('estado', ''),
            'order_by': self.request.GET.get('order_by', 'nombre'),
        }
        return context


class MaquinaCreateView(LoginRequiredMixin, AdminUserRequiredMixin, CreateView):
    """Crear nueva máquina"""
    model = Maquina
    form_class = MaquinaForm
    template_name = 'configuracion/maquina_form.html'
    success_url = reverse_lazy('configuracion_web:maquina-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Máquina'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Máquina "{form.instance.nombre}" creada exitosamente.')
        return super().form_valid(form)


class MaquinaUpdateView(LoginRequiredMixin, AdminUserRequiredMixin, UpdateView):
    """Editar máquina existente"""
    model = Maquina
    form_class = MaquinaForm
    template_name = 'configuracion/maquina_form.html'
    success_url = reverse_lazy('configuracion_web:maquina-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Máquina: {self.object.nombre}'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Máquina "{form.instance.nombre}" actualizada exitosamente.')
        return super().form_valid(form)


class MaquinaDeleteView(LoginRequiredMixin, AdminUserRequiredMixin, DeleteView):
    """Eliminar máquina"""
    model = Maquina
    template_name = 'configuracion/confirm_delete.html'
    success_url = reverse_lazy('configuracion_web:maquina-list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Máquina "{self.object.nombre}" eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)


# ===========================================
# VISTAS PARA TIPOS DE MÁQUINA
# ===========================================

class TipoMaquinaListView(LoginRequiredMixin, AdminUserRequiredMixin, ListView):
    """Lista de tipos de máquina"""
    model = TipoMaquina
    template_name = 'configuracion/tipo_maquina_list.html'
    context_object_name = 'tipos'
    paginate_by = 20

    def get_queryset(self):
        queryset = TipoMaquina.objects.annotate(maquinas_count=Count('maquina'))
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(codigo__icontains=search)
            )
        
        return queryset.order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Tipos de Máquina'
        context['search'] = self.request.GET.get('search', '')
        return context


class TipoMaquinaCreateView(LoginRequiredMixin, AdminUserRequiredMixin, CreateView):
    """Crear nuevo tipo de máquina"""
    model = TipoMaquina
    form_class = TipoMaquinaForm
    template_name = 'configuracion/tipo_maquina_form.html'
    success_url = reverse_lazy('configuracion_web:tipo-maquina-list')

    def form_valid(self, form):
        messages.success(self.request, f'Tipo de máquina "{form.instance.nombre}" creado exitosamente.')
        return super().form_valid(form)


# ===========================================
# VISTAS PARA ANILOX
# ===========================================

class AniloxListView(LoginRequiredMixin, AdminUserRequiredMixin, ListView):
    """Lista de anilox"""
    model = Anilox
    template_name = 'configuracion/anilox_list.html'
    context_object_name = 'anilox_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = Anilox.objects.all()
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(lineatura__icontains=search)
            )
        
        tipo_filter = self.request.GET.get('tipo')
        if tipo_filter:
            queryset = queryset.filter(tipo=tipo_filter)
        
        return queryset.order_by('codigo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Gestión de Anilox'
        context['search'] = self.request.GET.get('search', '')
        context['tipos_anilox'] = Anilox.TIPO_CHOICES
        return context


class AniloxCreateView(LoginRequiredMixin, AdminUserRequiredMixin, CreateView):
    """Crear nuevo anilox"""
    model = Anilox
    form_class = AniloxForm
    template_name = 'configuracion/anilox_form.html'
    success_url = reverse_lazy('configuracion_web:anilox-list')

    def form_valid(self, form):
        messages.success(self.request, f'Anilox "{form.instance.codigo}" creado exitosamente.')
        return super().form_valid(form)


# ===========================================
# VISTAS PARA PROVEEDORES
# ===========================================

class ProveedorListView(LoginRequiredMixin, AdminUserRequiredMixin, ListView):
    """Lista de proveedores"""
    model = Proveedor
    template_name = 'configuracion/proveedor_list.html'
    context_object_name = 'proveedores'
    paginate_by = 20

    def get_queryset(self):
        queryset = Proveedor.objects.all()
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(nit__icontains=search) |
                Q(contacto_principal__icontains=search)
            )
        
        categoria_filter = self.request.GET.get('categoria')
        if categoria_filter:
            queryset = queryset.filter(categoria=categoria_filter)
        
        estado_filter = self.request.GET.get('estado')
        if estado_filter == 'activo':
            queryset = queryset.filter(is_active=True)
        elif estado_filter == 'inactivo':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Gestión de Proveedores'
        context['search'] = self.request.GET.get('search', '')
        context['categorias'] = Proveedor.CATEGORIA_CHOICES if hasattr(Proveedor, 'CATEGORIA_CHOICES') else []
        return context


class ProveedorCreateView(LoginRequiredMixin, AdminUserRequiredMixin, CreateView):
    """Crear nuevo proveedor"""
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'configuracion/proveedor_form.html'
    success_url = reverse_lazy('configuracion_web:proveedor-list')

    def form_valid(self, form):
        messages.success(self.request, f'Proveedor "{form.instance.nombre}" creado exitosamente.')
        return super().form_valid(form)


# ===========================================
# VISTAS PARA PRODUCTOS
# ===========================================

class ProductoListView(LoginRequiredMixin, AdminUserRequiredMixin, ListView):
    """Lista de productos"""
    model = Producto
    template_name = 'configuracion/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 20

    def get_queryset(self):
        queryset = Producto.objects.select_related('categoria', 'cliente')
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(codigo__icontains=search) |
                Q(cliente__nombre__icontains=search)
            )
        
        categoria_filter = self.request.GET.get('categoria')
        if categoria_filter:
            queryset = queryset.filter(categoria_id=categoria_filter)
        
        cliente_filter = self.request.GET.get('cliente')
        if cliente_filter:
            queryset = queryset.filter(cliente_id=cliente_filter)
        
        return queryset.order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Gestión de Productos'
        context['search'] = self.request.GET.get('search', '')
        # context['categorias'] = CategoriaProducto.objects.all() if existe
        context['clientes'] = Cliente.objects.filter(is_active=True)
        return context


# ===========================================
# VISTAS AJAX Y UTILIDADES
# ===========================================

@login_required
@user_passes_test(is_admin_user)
def toggle_maquina_status(request, pk):
    """Cambiar estado activo/inactivo de una máquina via AJAX"""
    if request.method == 'POST':
        maquina = get_object_or_404(Maquina, pk=pk)
        maquina.is_active = not maquina.is_active
        maquina.save()
        
        return JsonResponse({
            'success': True,
            'new_status': maquina.is_active,
            'message': f'Máquina {"activada" if maquina.is_active else "desactivada"} exitosamente.'
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@login_required
@user_passes_test(is_admin_user)
def get_maquinas_by_tipo(request):
    """Obtener máquinas filtradas por tipo (para dropdowns dinámicos)"""
    tipo_id = request.GET.get('tipo_id')
    maquinas = Maquina.objects.filter(tipo_id=tipo_id, is_active=True)
    
    data = [{'id': m.id, 'nombre': m.nombre, 'codigo': m.codigo} for m in maquinas]
    return JsonResponse({'maquinas': data})


@login_required
@user_passes_test(is_admin_user)
def configuracion_general(request):
    """Vista para configuración general del sistema"""
    try:
        config = ConfiguracionGeneral.objects.first()
    except ConfiguracionGeneral.DoesNotExist:
        config = None
    
    if request.method == 'POST':
        form = ConfiguracionGeneralForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save()
            messages.success(request, 'Configuración general actualizada exitosamente.')
            return redirect('configuracion_web:configuracion-general')
    else:
        form = ConfiguracionGeneralForm(instance=config)
    
    context = {
        'title': 'Configuración General',
        'form': form,
        'config': config,
    }
    return render(request, 'configuracion/configuracion_general.html', context)


# ===========================================
# VISTAS DE REPORTES Y ESTADÍSTICAS
# ===========================================

@login_required
@user_passes_test(is_admin_user)
def reportes_configuracion(request):
    """Vista de reportes y estadísticas de configuración"""
    context = {
        'title': 'Reportes de Configuración',
        'stats': {
            'maquinas_por_tipo': TipoMaquina.objects.annotate(
                total=Count('maquina')
            ).values('nombre', 'total'),
            'maquinas_activas_inactivas': {
                'activas': Maquina.objects.filter(is_active=True).count(),
                'inactivas': Maquina.objects.filter(is_active=False).count(),
            },
            'proveedores_por_categoria': [],  # Implementar según modelo
            'productos_por_cliente': Cliente.objects.annotate(
                total_productos=Count('producto')
            ).values('nombre', 'total_productos')[:10],
        }
    }
    return render(request, 'configuracion/reportes.html', context)


# ===========================================
# VISTAS DE IMPORTACIÓN/EXPORTACIÓN
# ===========================================

@login_required
@user_passes_test(is_admin_user)
def importar_datos(request):
    """Vista para importar datos desde archivos CSV/Excel"""
    if request.method == 'POST':
        # Implementar lógica de importación
        pass
    
    context = {
        'title': 'Importar Datos',
    }
    return render(request, 'configuracion/importar_datos.html', context)


@login_required
@user_passes_test(is_admin_user)
def exportar_datos(request):
    """Vista para exportar datos a CSV/Excel"""
    tipo_export = request.GET.get('tipo', 'maquinas')
    
    # Implementar lógica de exportación según el tipo
    context = {
        'title': 'Exportar Datos',
        'tipos_disponibles': [
            ('maquinas', 'Máquinas'),
            ('proveedores', 'Proveedores'),
            ('productos', 'Productos'),
            ('anilox', 'Anilox'),
        ]
    }
    return render(request, 'configuracion/exportar_datos.html', context)