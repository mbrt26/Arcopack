# pedidos/filters.py
"""
Filtros personalizados para el módulo de pedidos
"""

import django_filters
from django import forms
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta

from .models import Pedido, LineaPedido
from clientes.models import Cliente
from productos.models import ProductoTerminado as Producto
from .config import ESTADOS_PEDIDO, PRIORIDADES_PEDIDO


class PedidoFilter(django_filters.FilterSet):
    """Filtros para la lista de pedidos"""
    
    numero_pedido = django_filters.CharFilter(
        field_name='numero_pedido',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por número de pedido...'
        })
    )
    
    cliente = django_filters.ModelChoiceFilter(
        field_name='cliente',
        queryset=Cliente.objects.filter(is_active=True),
        empty_label="Todos los clientes",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    cliente_busqueda = django_filters.CharFilter(
        method='filtrar_por_cliente',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar cliente por nombre...'
        })
    )
    
    estado = django_filters.MultipleChoiceFilter(
        field_name='estado',
        choices=ESTADOS_PEDIDO,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    prioridad = django_filters.MultipleChoiceFilter(
        field_name='prioridad',
        choices=PRIORIDADES_PEDIDO,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    fecha_pedido_desde = django_filters.DateFilter(
        field_name='fecha_pedido',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_pedido_hasta = django_filters.DateFilter(
        field_name='fecha_pedido',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_compromiso_desde = django_filters.DateFilter(
        field_name='fecha_compromiso',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_compromiso_hasta = django_filters.DateFilter(
        field_name='fecha_compromiso',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    valor_minimo = django_filters.NumberFilter(
        field_name='valor_total',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Valor mínimo'
        })
    )
    
    valor_maximo = django_filters.NumberFilter(
        field_name='valor_total',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Valor máximo'
        })
    )
    
    # Filtros especiales
    vencidos = django_filters.BooleanFilter(
        method='filtrar_vencidos',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    proximos_vencer = django_filters.NumberFilter(
        method='filtrar_proximos_vencer',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Días'
        })
    )
    
    sin_avance = django_filters.BooleanFilter(
        method='filtrar_sin_avance',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    creado_por = django_filters.CharFilter(
        method='filtrar_por_creador',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por creador...'
        })
    )
    
    tiene_observaciones = django_filters.BooleanFilter(
        method='filtrar_con_observaciones',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Pedido
        fields = []

    def filtrar_por_cliente(self, queryset, name, value):
        """Filtrar por nombre o razón social del cliente"""
        if value:
            return queryset.filter(
                Q(cliente__razon_social__icontains=value) |
                Q(cliente__nombre_comercial__icontains=value) |
                Q(cliente__nit__icontains=value)
            )
        return queryset

    def filtrar_vencidos(self, queryset, name, value):
        """Filtrar pedidos vencidos"""
        if value:
            return queryset.filter(
                fecha_compromiso__lt=date.today(),
                estado__in=['CONFIRMADO', 'EN_PRODUCCION']
            )
        return queryset

    def filtrar_proximos_vencer(self, queryset, name, value):
        """Filtrar pedidos próximos a vencer"""
        if value:
            fecha_limite = date.today() + timedelta(days=value)
            return queryset.filter(
                fecha_compromiso__lte=fecha_limite,
                fecha_compromiso__gte=date.today(),
                estado__in=['CONFIRMADO', 'EN_PRODUCCION']
            )
        return queryset

    def filtrar_sin_avance(self, queryset, name, value):
        """Filtrar pedidos sin avance significativo"""
        if value:
            return queryset.filter(
                porcentaje_completado__lte=10,
                estado__in=['CONFIRMADO', 'EN_PRODUCCION']
            )
        return queryset

    def filtrar_por_creador(self, queryset, name, value):
        """Filtrar por usuario creador"""
        if value:
            return queryset.filter(
                Q(creado_por__username__icontains=value) |
                Q(creado_por__first_name__icontains=value) |
                Q(creado_por__last_name__icontains=value)
            )
        return queryset

    def filtrar_con_observaciones(self, queryset, name, value):
        """Filtrar pedidos que tienen observaciones"""
        if value:
            return queryset.exclude(observaciones__isnull=True).exclude(observaciones='')
        return queryset


class LineaPedidoFilter(django_filters.FilterSet):
    """Filtros para las líneas de pedido"""
    
    producto = django_filters.ModelChoiceFilter(
        field_name='producto',
        queryset=Producto.objects.filter(activo=True),
        empty_label="Todos los productos",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    producto_busqueda = django_filters.CharFilter(
        method='filtrar_por_producto',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar producto...'
        })
    )
    
    cantidad_minima = django_filters.NumberFilter(
        field_name='cantidad',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cantidad mínima'
        })
    )
    
    cantidad_maxima = django_filters.NumberFilter(
        field_name='cantidad',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cantidad máxima'
        })
    )
    
    precio_minimo = django_filters.NumberFilter(
        field_name='precio_unitario',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Precio mínimo'
        })
    )
    
    precio_maximo = django_filters.NumberFilter(
        field_name='precio_unitario',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Precio máximo'
        })
    )
    
    con_especificaciones = django_filters.BooleanFilter(
        method='filtrar_con_especificaciones',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = LineaPedido
        fields = []

    def filtrar_por_producto(self, queryset, name, value):
        """Filtrar por nombre, código o descripción del producto"""
        if value:
            return queryset.filter(
                Q(producto__nombre__icontains=value) |
                Q(producto__codigo__icontains=value) |
                Q(producto__descripcion__icontains=value)
            )
        return queryset

    def filtrar_con_especificaciones(self, queryset, name, value):
        """Filtrar líneas que tienen especificaciones técnicas"""
        if value:
            return queryset.exclude(
                especificaciones_tecnicas__isnull=True
            ).exclude(especificaciones_tecnicas='')
        return queryset


class PedidoDashboardFilter(django_filters.FilterSet):
    """Filtros específicos para el dashboard de pedidos"""
    
    periodo = django_filters.ChoiceFilter(
        method='filtrar_por_periodo',
        choices=[
            ('hoy', 'Hoy'),
            ('semana', 'Esta semana'),
            ('mes', 'Este mes'),
            ('trimestre', 'Este trimestre'),
            ('año', 'Este año'),
            ('personalizado', 'Período personalizado')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_desde = django_filters.DateFilter(
        field_name='fecha_pedido',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_hasta = django_filters.DateFilter(
        field_name='fecha_pedido',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    solo_activos = django_filters.BooleanFilter(
        method='filtrar_solo_activos',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Pedido
        fields = []

    def filtrar_por_periodo(self, queryset, name, value):
        """Filtrar por período predefinido"""
        hoy = date.today()
        
        if value == 'hoy':
            return queryset.filter(fecha_pedido=hoy)
        elif value == 'semana':
            inicio_semana = hoy - timedelta(days=hoy.weekday())
            return queryset.filter(fecha_pedido__gte=inicio_semana)
        elif value == 'mes':
            inicio_mes = hoy.replace(day=1)
            return queryset.filter(fecha_pedido__gte=inicio_mes)
        elif value == 'trimestre':
            mes_trimestre = ((hoy.month - 1) // 3) * 3 + 1
            inicio_trimestre = hoy.replace(month=mes_trimestre, day=1)
            return queryset.filter(fecha_pedido__gte=inicio_trimestre)
        elif value == 'año':
            inicio_año = hoy.replace(month=1, day=1)
            return queryset.filter(fecha_pedido__gte=inicio_año)
        
        return queryset

    def filtrar_solo_activos(self, queryset, name, value):
        """Filtrar solo pedidos activos (no cancelados ni entregados)"""
        if value:
            return queryset.exclude(estado__in=['CANCELADO', 'ENTREGADO'])
        return queryset


class PedidoReporteFilter(django_filters.FilterSet):
    """Filtros específicos para reportes de pedidos"""
    
    tipo_reporte = django_filters.ChoiceFilter(
        choices=[
            ('resumen', 'Resumen General'),
            ('detallado', 'Reporte Detallado'),
            ('por_cliente', 'Por Cliente'),
            ('por_producto', 'Por Producto'),
            ('por_vendedor', 'Por Vendedor'),
            ('vencimientos', 'Vencimientos'),
            ('produccion', 'Estado de Producción')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    agrupar_por = django_filters.ChoiceFilter(
        choices=[
            ('dia', 'Por Día'),
            ('semana', 'Por Semana'),
            ('mes', 'Por Mes'),
            ('trimestre', 'Por Trimestre'),
            ('año', 'Por Año'),
            ('cliente', 'Por Cliente'),
            ('estado', 'Por Estado'),
            ('prioridad', 'Por Prioridad')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    incluir_cancelados = django_filters.BooleanFilter(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    incluir_entregados = django_filters.BooleanFilter(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    formato_exportacion = django_filters.ChoiceFilter(
        choices=[
            ('csv', 'CSV'),
            ('xlsx', 'Excel'),
            ('pdf', 'PDF')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Pedido
        fields = []


# Funciones de filtrado rápido para vistas
def obtener_pedidos_urgentes():
    """Obtiene pedidos con prioridad urgente"""
    return Pedido.objects.filter(
        prioridad='URGENTE',
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    )


def obtener_pedidos_vencidos():
    """Obtiene pedidos vencidos"""
    return Pedido.objects.filter(
        fecha_compromiso__lt=date.today(),
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    )


def obtener_pedidos_proximos_vencer(dias=7):
    """Obtiene pedidos próximos a vencer"""
    fecha_limite = date.today() + timedelta(days=dias)
    return Pedido.objects.filter(
        fecha_compromiso__lte=fecha_limite,
        fecha_compromiso__gte=date.today(),
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    )


def obtener_pedidos_sin_avance():
    """Obtiene pedidos sin avance significativo"""
    return Pedido.objects.filter(
        porcentaje_completado__lte=10,
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    )


def obtener_pedidos_alto_valor(valor_minimo=10000000):
    """Obtiene pedidos de alto valor"""
    return Pedido.objects.filter(
        valor_total__gte=valor_minimo,
        estado__in=['CONFIRMADO', 'EN_PRODUCCION', 'PRODUCIDO']
    )


def obtener_pedidos_cliente(cliente_id):
    """Obtiene pedidos de un cliente específico"""
    return Pedido.objects.filter(cliente_id=cliente_id)


def obtener_pedidos_vendedor(vendedor_id):
    """Obtiene pedidos de un vendedor específico"""
    return Pedido.objects.filter(creado_por_id=vendedor_id)


def obtener_pedidos_periodo(fecha_inicio, fecha_fin):
    """Obtiene pedidos en un período específico"""
    return Pedido.objects.filter(
        fecha_pedido__range=[fecha_inicio, fecha_fin]
    )