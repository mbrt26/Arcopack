from django import forms
from .models import MateriaPrima, LoteProductoEnProceso, LoteProductoTerminado, Ubicacion, MovimientoInventario
from configuracion.models import CategoriaMateriaPrima, UnidadMedida, Proveedor
from clientes.models import Cliente

class MateriaPrimaForm(forms.ModelForm):
    """Formulario personalizado para la creación y edición de materias primas."""
    
    class Meta:
        model = MateriaPrima
        fields = [
            'codigo', 'nombre', 'descripcion', 'categoria', 'unidad_medida', 
            'stock_minimo', 'stock_maximo', 'tiempo_entrega_std_dias', 'proveedor_preferido', 'requiere_lote', 'is_active'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. MP-001',
                'autocomplete': 'off'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la materia prima',
                'autocomplete': 'off'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción detallada de la materia prima'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'unidad_medida': forms.Select(attrs={
                'class': 'form-select'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'stock_maximo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'tiempo_entrega_std_dias': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Días de lead time'
            }),
            'proveedor_preferido': forms.Select(attrs={
                'class': 'form-select'
            }),
            'requiere_lote': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ordenar las opciones de los campos de selección
        self.fields['categoria'].queryset = CategoriaMateriaPrima.objects.order_by('nombre')
        self.fields['unidad_medida'].queryset = UnidadMedida.objects.order_by('nombre')
        self.fields['proveedor_preferido'].queryset = Proveedor.objects.filter(is_active=True).order_by('razon_social')
        
        # Marcar campos requeridos
        for field_name in ['codigo', 'nombre', 'categoria', 'unidad_medida']:
            self.fields[field_name].required = True
            
        # Añadir ayuda contextual
        self.fields['stock_minimo'].help_text = 'Cantidad mínima recomendada en inventario'
        self.fields['stock_maximo'].help_text = 'Cantidad máxima recomendada en inventario'
        self.fields['tiempo_entrega_std_dias'].help_text = 'Tiempo promedio de entrega por parte del proveedor (en días)'
        self.fields['proveedor_preferido'].help_text = 'Proveedor preferido para esta materia prima'
        self.fields['is_active'].help_text = 'Desactive esta opción para ocultar esta materia prima en las listas de selección'
        
    def clean(self):
        cleaned_data = super().clean()
        stock_minimo = cleaned_data.get('stock_minimo')
        stock_maximo = cleaned_data.get('stock_maximo')
        
        if stock_minimo is not None and stock_maximo is not None:
            if stock_maximo <= stock_minimo:
                self.add_error('stock_maximo', 'El stock máximo debe ser mayor al stock mínimo')
                
        return cleaned_data


class TransferirWIPForm(forms.Form):
    """Formulario para transferir un lote WIP a otra ubicación."""
    ubicacion_destino = forms.ModelChoiceField(
        queryset=Ubicacion.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Ubicación Destino',
        help_text='Seleccione la ubicación a la que desea transferir este lote'
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Observaciones',
        required=False,
        help_text='Observaciones sobre la transferencia (opcional)'
    )
    
    def __init__(self, lote_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lote_id = lote_id
        
        if lote_id:
            lote = LoteProductoEnProceso.objects.get(pk=lote_id)
            # Excluir la ubicación actual del lote
            self.fields['ubicacion_destino'].queryset = Ubicacion.objects.filter(
                is_active=True
            ).exclude(pk=lote.ubicacion.pk)


class ConsumirWIPForm(forms.Form):
    """Formulario para consumir un lote WIP."""
    cantidad = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
        label='Cantidad a Consumir',
        help_text='Cantidad a consumir del lote (debe ser menor o igual a la cantidad actual)'
    )
    documento_referencia = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Documento de Referencia',
        required=False,
        help_text='Número de orden de producción, requisición, etc. (opcional)'
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Observaciones',
        required=False,
        help_text='Motivo del consumo u observaciones adicionales (opcional)'
    )
    
    def __init__(self, lote_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lote_id = lote_id
        
        if lote_id:
            lote = LoteProductoEnProceso.objects.get(pk=lote_id)
            self.fields['cantidad'].initial = lote.cantidad_actual
            self.fields['cantidad'].max_value = lote.cantidad_actual
            self.fields['cantidad'].widget.attrs['max'] = float(lote.cantidad_actual)
            self.fields['cantidad'].help_text = f'Máximo disponible: {lote.cantidad_actual} {lote.unidad_medida_primaria.codigo}'


class AjustarStockWIPForm(forms.Form):
    """Formulario para ajustar el stock de un lote WIP."""
    tipo_ajuste = forms.ChoiceField(
        choices=[
            ('AJUSTE_POSITIVO', 'Incrementar Stock'),
            ('AJUSTE_NEGATIVO', 'Reducir Stock'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de Ajuste'
    )
    cantidad = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
        label='Cantidad a Ajustar',
        help_text='Cantidad a ajustar (positiva)'
    )
    motivo = forms.CharField(
        max_length=100,
        label="Motivo del Ajuste",
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Error de conteo, Merma, etc.'})
    )
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
        label="Observaciones"
    )
    
    def __init__(self, lote_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lote_id = lote_id
        
        if lote_id:
            lote = LoteProductoEnProceso.objects.get(pk=lote_id)
            self.fields['cantidad'].help_text = f'Stock actual: {lote.cantidad_actual} {lote.unidad_medida_primaria.codigo}'
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_ajuste = cleaned_data.get('tipo_ajuste')
        cantidad = cleaned_data.get('cantidad')
        
        if not cantidad:
            return cleaned_data
            
        lote_id = self.initial.get('lote_id')
        if not lote_id:
            raise forms.ValidationError("No se especificó el lote a ajustar")
            
        lote = LoteProductoEnProceso.objects.get(id=lote_id)
        
        if tipo_ajuste == 'AJUSTE_NEGATIVO' and cantidad > lote.cantidad_actual:
            self.add_error('cantidad', f"La cantidad a reducir no puede ser mayor que el stock actual ({lote.cantidad_actual})")
            
        return cleaned_data


# Forms for Producto Terminado actions
class TransferirPTForm(forms.Form):
    TIPO_TRANSFERENCIA_CHOICES = [
        ('TOTAL', 'Transferir todo el lote'),
        ('PARCIAL', 'Transferir cantidad parcial')
    ]
    
    tipo_transferencia = forms.ChoiceField(
        choices=TIPO_TRANSFERENCIA_CHOICES,
        initial='TOTAL',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Tipo de Transferencia"
    )
    
    cantidad = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Cantidad a Transferir",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )
    
    ubicacion_destino = forms.ModelChoiceField(
        queryset=Ubicacion.objects.all(),
        label="Ubicación Destino",
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Seleccione una ubicación"
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
        label="Observaciones"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lote_id = kwargs.get('initial', {}).get('lote_id')
        
        if lote_id:
            try:
                lote = LoteProductoTerminado.objects.get(id=lote_id)
                self.fields['cantidad'].widget.attrs['max'] = float(lote.cantidad_actual)
                self.fields['cantidad'].help_text = f'Máximo disponible: {lote.cantidad_actual} {lote.unidad_medida_lote.codigo}'
            except LoteProductoTerminado.DoesNotExist:
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_transferencia = cleaned_data.get('tipo_transferencia')
        cantidad = cleaned_data.get('cantidad')
        lote_id = self.initial.get('lote_id')
        
        if not lote_id:
            raise forms.ValidationError("No se especificó el lote a transferir")
        
        try:
            lote = LoteProductoTerminado.objects.get(id=lote_id)
        except LoteProductoTerminado.DoesNotExist:
            raise forms.ValidationError("El lote especificado no existe")
        
        if tipo_transferencia == 'PARCIAL':
            if not cantidad:
                self.add_error('cantidad', "Debe especificar la cantidad a transferir para una transferencia parcial")
            elif cantidad <= 0:
                self.add_error('cantidad', "La cantidad a transferir debe ser mayor que cero")
            elif cantidad > lote.cantidad_actual:
                self.add_error('cantidad', f"La cantidad a transferir no puede ser mayor que el stock actual ({lote.cantidad_actual})")
        
        return cleaned_data
    
    def clean_ubicacion_destino(self):
        ubicacion_destino = self.cleaned_data.get('ubicacion_destino')
        lote_id = self.initial.get('lote_id')
        
        if not lote_id:
            raise forms.ValidationError("No se especificó el lote a transferir")
            
        try:
            lote = LoteProductoTerminado.objects.get(id=lote_id)
            
            if ubicacion_destino == lote.ubicacion:
                raise forms.ValidationError("La ubicación destino debe ser diferente a la ubicación actual")
        except LoteProductoTerminado.DoesNotExist:
            pass
            
        return ubicacion_destino


class DespacharPTForm(forms.Form):
    TIPO_DESPACHO_CHOICES = [
        ('TOTAL', 'Despachar todo el lote'),
        ('PARCIAL', 'Despachar cantidad parcial')
    ]
    
    tipo_despacho = forms.ChoiceField(
        choices=TIPO_DESPACHO_CHOICES,
        initial='TOTAL',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Tipo de Despacho"
    )
    
    cantidad = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Cantidad a Despachar",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )
    
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(is_active=True),
        label="Cliente",
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Seleccione un cliente"
    )
    
    numero_guia = forms.CharField(
        max_length=50,
        label="Número de Guía/Referencia",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de guía o referencia'})
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
        label="Observaciones"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lote_id = kwargs.get('initial', {}).get('lote_id')
        
        if lote_id:
            try:
                lote = LoteProductoTerminado.objects.get(id=lote_id)
                self.fields['cantidad'].widget.attrs['max'] = float(lote.cantidad_actual)
                self.fields['cantidad'].help_text = f'Máximo disponible: {lote.cantidad_actual} {lote.unidad_medida_lote.codigo}'
            except LoteProductoTerminado.DoesNotExist:
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_despacho = cleaned_data.get('tipo_despacho')
        cantidad = cleaned_data.get('cantidad')
        lote_id = self.initial.get('lote_id')
        
        if not lote_id:
            raise forms.ValidationError("No se especificó el lote a despachar")
        
        try:
            lote = LoteProductoTerminado.objects.get(id=lote_id)
        except LoteProductoTerminado.DoesNotExist:
            raise forms.ValidationError("El lote especificado no existe")
        
        if tipo_despacho == 'PARCIAL':
            if not cantidad:
                self.add_error('cantidad', "Debe especificar la cantidad a despachar para un despacho parcial")
            elif cantidad <= 0:
                self.add_error('cantidad', "La cantidad a despachar debe ser mayor que cero")
            elif cantidad > lote.cantidad_actual:
                self.add_error('cantidad', f"La cantidad a despachar no puede ser mayor que el stock actual ({lote.cantidad_actual})")
        
        return cleaned_data


class ConsumirPTForm(forms.Form):
    cantidad = forms.DecimalField(
        min_value=0.01, 
        max_digits=10, 
        decimal_places=2,
        label="Cantidad a Consumir",
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'})
    )
    documento_referencia = forms.CharField(
        max_length=50,
        required=False,
        label="Documento de Referencia",
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Orden #123, Factura #456, etc.'})
    )
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
        label="Observaciones"
    )
    
    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        lote_id = self.initial.get('lote_id')
        
        if not lote_id:
            raise forms.ValidationError("No se especificó el lote a consumir")
            
        lote = LoteProductoTerminado.objects.get(id=lote_id)
        
        if cantidad > lote.cantidad_actual:
            raise forms.ValidationError(f"La cantidad a consumir no puede ser mayor que el stock actual ({lote.cantidad_actual})")
            
        return cantidad


class AjustarStockPTForm(forms.Form):
    TIPO_AJUSTE_CHOICES = [
        ('AJUSTE_POSITIVO', 'Incrementar Stock'),
        ('AJUSTE_NEGATIVO', 'Reducir Stock'),
    ]
    
    tipo_ajuste = forms.ChoiceField(
        choices=TIPO_AJUSTE_CHOICES,
        widget=forms.RadioSelect,
        label="Tipo de Ajuste"
    )
    cantidad = forms.DecimalField(
        min_value=0.01, 
        max_digits=10, 
        decimal_places=2,
        label="Cantidad",
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'})
    )
    motivo = forms.CharField(
        max_length=100,
        label="Motivo del Ajuste",
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Error de conteo, Merma, etc.'})
    )
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
        label="Observaciones"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_ajuste = cleaned_data.get('tipo_ajuste')
        cantidad = cleaned_data.get('cantidad')
        
        if not cantidad:
            return cleaned_data
            
        lote_id = self.initial.get('lote_id')
        if not lote_id:
            raise forms.ValidationError("No se especificó el lote a ajustar")
            
        lote = LoteProductoTerminado.objects.get(id=lote_id)
        
        if tipo_ajuste == 'AJUSTE_NEGATIVO' and cantidad > lote.cantidad_actual:
            self.add_error('cantidad', f"La cantidad a reducir no puede ser mayor que el stock actual ({lote.cantidad_actual})")
            
        return cleaned_data
