# pedidos/forms.py
from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from django.db import models
from .models import Pedido, LineaPedido
from clientes.models import Cliente
from productos.models import ProductoTerminado


class PedidoForm(forms.ModelForm):
    """Formulario para crear/editar pedidos"""
    
    def clean(self):
        """Validar que la fecha de compromiso sea posterior a la fecha de pedido"""
        cleaned_data = super().clean()
        fecha_pedido = cleaned_data.get('fecha_pedido')
        fecha_compromiso = cleaned_data.get('fecha_compromiso')
        
        if fecha_pedido and fecha_compromiso and fecha_compromiso < fecha_pedido:
            self.add_error('fecha_compromiso', 'La fecha de compromiso debe ser igual o posterior a la fecha del pedido')
            
        return cleaned_data
    
    class Meta:
        model = Pedido
        fields = [
            'cliente', 'pedido_cliente_referencia', 'fecha_pedido', 'fecha_compromiso',
            'prioridad', 'condiciones_pago', 'observaciones'
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'pedido_cliente_referencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Referencia del cliente (opcional)'
            }),
            'fecha_pedido': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'fecha_compromiso': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'condiciones_pago': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 30 días, Contado, etc.'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones generales del pedido...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar clientes por razón social - CORREGIDO: usar is_active
        self.fields['cliente'].queryset = Cliente.objects.filter(is_active=True).order_by('razon_social')
        
        # Hacer campos requeridos
        self.fields['cliente'].required = True
        self.fields['fecha_pedido'].required = True
        self.fields['fecha_compromiso'].required = True


class LineaPedidoForm(forms.ModelForm):
    """Formulario para líneas de pedido"""
    
    class Meta:
        model = LineaPedido
        fields = [
            'orden_linea', 'producto', 'cantidad', 'precio_unitario', 
            'descuento_porcentaje', 'especificaciones_tecnicas'
        ]
        widgets = {
            'orden_linea': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': 1,
                'placeholder': '#'
            }),
            'producto': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': 0.01,
                'step': 0.001,
                'placeholder': '0.000'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': 0,
                'step': 0.0001,
                'placeholder': '0.0000'
            }),
            'descuento_porcentaje': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': 0,
                'max': 100,
                'step': 0.01,
                'placeholder': '0.00'
            }),
            'especificaciones_tecnicas': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
                'placeholder': 'Especificaciones técnicas específicas para esta línea...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar productos activos - CORREGIDO: usar is_active en lugar de activo
        self.fields['producto'].queryset = ProductoTerminado.objects.filter(is_active=True).order_by('codigo')
        
        # Hacer campos requeridos
        self.fields['producto'].required = True
        self.fields['cantidad'].required = True
        self.fields['precio_unitario'].required = True
        
        # Hacer descuento_porcentaje opcional y asegurar valor por defecto
        self.fields['descuento_porcentaje'].required = False
        self.fields['descuento_porcentaje'].initial = 0.00
        
        # Hacer orden_linea opcional y asegurar valor por defecto
        self.fields['orden_linea'].required = False
        self.fields['orden_linea'].initial = 1

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        producto = self.cleaned_data.get('producto')
        
        if not cantidad:
            return cantidad
            
        # Validar que la cantidad sea positiva
        if cantidad <= 0:
            raise forms.ValidationError('La cantidad debe ser mayor que cero')
        
        # Verificar disponibilidad del producto si es posible
        if producto and hasattr(producto, 'verificar_disponibilidad'):
            disponible = producto.verificar_disponibilidad(cantidad)
            if not disponible:
                raise forms.ValidationError(
                    f'No hay suficiente stock disponible. Stock actual: {producto.stock_actual}'
                )
        
        return cantidad

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get('precio_unitario')
        if precio and precio < 0:
            raise forms.ValidationError('El precio unitario no puede ser negativo')
        return precio

    def clean_descuento_porcentaje(self):
        descuento = self.cleaned_data.get('descuento_porcentaje')
        if descuento and (descuento < 0 or descuento > 100):
            raise forms.ValidationError('El descuento debe estar entre 0% y 100%')
        return descuento


# Formset para manejar múltiples líneas de pedido
LineaPedidoFormSet = inlineformset_factory(
    Pedido,
    LineaPedido,
    form=LineaPedidoForm,
    extra=0,  # No mostrar líneas extra vacías automáticamente
    min_num=1,  # Mínimo una línea
    validate_min=True,
    can_delete=True
)


class CambiarEstadoPedidoForm(forms.Form):
    """Formulario para cambiar el estado de un pedido"""
    
    nuevo_estado = forms.ChoiceField(
        choices=Pedido.ESTADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    numero_factura = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Número de factura'
        })
    )
    
    fecha_facturacion = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date'
        })
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm',
            'rows': 2,
            'placeholder': 'Comentarios sobre el cambio de estado...'
        })
    )

    def __init__(self, pedido, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pedido = pedido
        
        # Configurar estado inicial
        self.fields['nuevo_estado'].initial = pedido.estado
        
        # Configurar campos de facturación según el estado
        if pedido.estado in ['PRODUCIDO', 'PENDIENTE_FACTURAR', 'FACTURADO']:
            self.fields['numero_factura'].widget.attrs['style'] = 'display: block;'
            self.fields['fecha_facturacion'].widget.attrs['style'] = 'display: block;'
        else:
            self.fields['numero_factura'].widget.attrs['style'] = 'display: none;'
            self.fields['fecha_facturacion'].widget.attrs['style'] = 'display: none;'

    def clean(self):
        cleaned_data = super().clean()
        nuevo_estado = cleaned_data.get('nuevo_estado')
        numero_factura = cleaned_data.get('numero_factura')
        fecha_facturacion = cleaned_data.get('fecha_facturacion')

        # Validar campos requeridos para facturación
        if nuevo_estado == 'FACTURADO':
            if not numero_factura:
                raise forms.ValidationError('El número de factura es requerido para el estado "Facturado"')
            if not fecha_facturacion:
                raise forms.ValidationError('La fecha de facturación es requerida para el estado "Facturado"')

        return cleaned_data


class FiltrosPedidoForm(forms.Form):
    """Formulario para filtrar pedidos en la lista"""
    
    ESTADO_CHOICES = [('', 'Todos los estados')] + list(Pedido.ESTADO_CHOICES)
    PRIORIDAD_CHOICES = [('', 'Todas las prioridades')] + list(Pedido.PRIORIDAD_CHOICES)
    
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(is_active=True).order_by('razon_social'),  # CORREGIDO
        required=False,
        empty_label="Todos los clientes",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    prioridad = forms.ChoiceField(
        choices=PRIORIDAD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    numero_pedido = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Número de pedido'
        })
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date'
        })
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        fecha_desde = cleaned_data.get('fecha_desde')
        fecha_hasta = cleaned_data.get('fecha_hasta')

        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise forms.ValidationError('La fecha desde no puede ser mayor que la fecha hasta')

        return cleaned_data


class CrearOrdenProduccionForm(forms.Form):
    """Formulario para crear órdenes de producción desde un pedido"""
    
    TIPO_ORDEN_CHOICES = [
        ('individual', 'Órdenes Individuales'),
        ('consolidada', 'Orden Consolidada'),
    ]
    
    lineas_seleccionadas = forms.ModelMultipleChoiceField(
        queryset=LineaPedido.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        error_messages={'required': 'Debe seleccionar al menos una línea del pedido'}
    )
    
    fecha_compromiso = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Fecha compromiso de entrega para la(s) orden(es) de producción'
    )
    
    prioridad = forms.ChoiceField(
        choices=Pedido.PRIORIDAD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_orden = forms.ChoiceField(
        choices=TIPO_ORDEN_CHOICES,
        initial='individual',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Instrucciones especiales para producción...'
        })
    )

    def __init__(self, pedido, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pedido = pedido
        
        # Filtrar líneas disponibles (que no estén completamente producidas)
        lineas_disponibles = pedido.lineas.filter(
            cantidad_producida__lt=models.F('cantidad')
        ).order_by('orden_linea')
        
        self.fields['lineas_seleccionadas'].queryset = lineas_disponibles
        
        # Valores por defecto
        self.fields['fecha_compromiso'].initial = pedido.fecha_compromiso
        self.fields['prioridad'].initial = pedido.prioridad

    def clean_lineas_seleccionadas(self):
        lineas = self.cleaned_data.get('lineas_seleccionadas')
        if not lineas:
            raise forms.ValidationError('Debe seleccionar al menos una línea del pedido')
        
        # Validar que las líneas pertenecen al pedido
        for linea in lineas:
            if linea.pedido != self.pedido:
                raise forms.ValidationError('Línea no válida para este pedido')
                
        return lineas

    def clean_fecha_compromiso(self):
        fecha = self.cleaned_data.get('fecha_compromiso')
        if fecha and fecha < timezone.now().date():
            raise forms.ValidationError('La fecha de compromiso no puede ser anterior a hoy')
        return fecha