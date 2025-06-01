from django import forms
from .models import ProductoTerminado
from configuracion.models import (
    CategoriaProducto, SubLinea, EstadoProducto, UnidadMedida,
    TipoMateriaPrima, TipoMaterial, Tratamiento, TipoTinta,
    TipoSellado, TipoTroquel, TipoZipper, TipoValvula,
    TipoImpresion, CuentaContable, Servicio
)
from clientes.models import Cliente


class ProductoSearchForm(forms.Form):
    q = forms.CharField(label='Buscar', required=False,
                        widget=forms.TextInput(attrs={'class': 'form-control',
                                                      'placeholder': 'Código o nombre'}))


class ProductoTerminadoForm(forms.ModelForm):
    """
    Formulario completo para ProductoTerminado que replica la funcionalidad
    del admin de Django con fieldsets organizados por secciones.
    """
    
    class Meta:
        model = ProductoTerminado
        exclude = ['creado_en', 'actualizado_en', 'creado_por', 'actualizado_por']
        widgets = {
            # Información Principal
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código único del producto'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre descriptivo del producto'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'linea': forms.Select(attrs={'class': 'form-select'}),
            'sublinea': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'archivo_adjunto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            
            # Material Base y Dimensiones
            'tipo_materia_prima': forms.Select(attrs={'class': 'form-select'}),
            'tipo_material': forms.Select(attrs={'class': 'form-select'}),
            'calibre_um': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Calibre en micrones'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Color del material'}),
            'medida_en': forms.Select(attrs={'class': 'form-select'}),
            'largo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Largo'}),
            'ancho': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ancho'}),
            'ancho_rollo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ancho del rollo'}),
            'metros_lineales': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Metros lineales'}),
            'largo_material': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Largo del material'}),
            'factor_decimal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': 'Factor decimal'}),
            
            # Especificaciones Adicionales
            'tratamiento': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_xml': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad XML'}),
            
            # Doblado
            'dob_medida_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Medida de doblado en cm'}),
            
            # Impresión
            'imp_tipo_impresion': forms.Select(attrs={'class': 'form-select'}),
            'imp_repeticiones': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número de repeticiones'}),
            'tipo_tinta': forms.Select(attrs={'class': 'form-select'}),
            'pistas': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número de pistas'}),
            
            # Sellado: General y Fuelles
            'sellado_tipo': forms.Select(attrs={'class': 'form-select'}),
            'sellado_peso_millar': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Peso por millar'}),
            'sellado_fuelle_fondo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Fuelle de fondo'}),
            'sellado_fuelle_lateral': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Fuelle lateral'}),
            'sellado_fuelle_superior': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Fuelle superior'}),
            'sellado_solapa_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Solapa en cm'}),
            
            # Sellado: Features Adicionales
            'sellado_troquel_tipo': forms.Select(attrs={'class': 'form-select'}),
            'sellado_troquel_medida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Medida del troquel'}),
            'sellado_zipper_tipo': forms.Select(attrs={'class': 'form-select'}),
            'sellado_zipper_medida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Medida del zipper'}),
            'sellado_valvula_tipo': forms.Select(attrs={'class': 'form-select'}),
            'sellado_valvula_medida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Medida de la válvula'}),
            'sellado_ultrasonido': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sellado_ultrasonido_pos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Posición del ultrasonido'}),
            'sellado_precorte': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sellado_precorte_medida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Medida del precorte'}),
            
            # Otros / Contabilidad
            'cuenta_contable': forms.Select(attrs={'class': 'form-select'}),
            'servicio': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar queryset para campos ForeignKey para optimizar consultas
        # Solo filtrar por is_active en modelos que tienen este campo
        self.fields['cliente'].queryset = Cliente.objects.filter(is_active=True).order_by('razon_social')
        self.fields['linea'].queryset = CategoriaProducto.objects.all().order_by('nombre')
        self.fields['sublinea'].queryset = SubLinea.objects.all().order_by('nombre')
        self.fields['estado'].queryset = EstadoProducto.objects.all().order_by('nombre')
        self.fields['unidad_medida'].queryset = UnidadMedida.objects.all().order_by('nombre')
        self.fields['tipo_materia_prima'].queryset = TipoMateriaPrima.objects.all().order_by('nombre')
        self.fields['tipo_material'].queryset = TipoMaterial.objects.all().order_by('nombre')
        self.fields['tratamiento'].queryset = Tratamiento.objects.all().order_by('nombre')
        self.fields['tipo_tinta'].queryset = TipoTinta.objects.all().order_by('nombre')
        self.fields['sellado_tipo'].queryset = TipoSellado.objects.all().order_by('nombre')
        self.fields['sellado_troquel_tipo'].queryset = TipoTroquel.objects.all().order_by('nombre')
        self.fields['sellado_zipper_tipo'].queryset = TipoZipper.objects.all().order_by('nombre')
        self.fields['sellado_valvula_tipo'].queryset = TipoValvula.objects.all().order_by('nombre')
        self.fields['imp_tipo_impresion'].queryset = TipoImpresion.objects.all().order_by('nombre')
        self.fields['cuenta_contable'].queryset = CuentaContable.objects.all().order_by('codigo')
        self.fields['servicio'].queryset = Servicio.objects.all().order_by('nombre')
        
        # Configurar labels más descriptivos
        self.fields['codigo'].label = 'Código del Producto'
        self.fields['nombre'].label = 'Nombre del Producto'
        self.fields['cliente'].label = 'Cliente'
        self.fields['linea'].label = 'Línea de Producto'
        self.fields['sublinea'].label = 'Sublínea'
        self.fields['estado'].label = 'Estado'
        self.fields['unidad_medida'].label = 'Unidad de Medida'
        self.fields['is_active'].label = 'Producto Activo'
        self.fields['archivo_adjunto'].label = 'Archivo Adjunto'
        
        # Material Base y Dimensiones
        self.fields['tipo_materia_prima'].label = 'Tipo de Materia Prima'
        self.fields['tipo_material'].label = 'Tipo de Material'
        self.fields['calibre_um'].label = 'Calibre (μm)'
        self.fields['color'].label = 'Color'
        self.fields['medida_en'].label = 'Medida en'
        self.fields['largo'].label = 'Largo'
        self.fields['ancho'].label = 'Ancho'
        self.fields['ancho_rollo'].label = 'Ancho del Rollo'
        self.fields['metros_lineales'].label = 'Metros Lineales'
        self.fields['largo_material'].label = 'Largo del Material'
        self.fields['factor_decimal'].label = 'Factor Decimal'
        
        # Hacer algunos campos opcionales más evidentes
        self.fields['sublinea'].required = False
        self.fields['archivo_adjunto'].required = False
        self.fields['tratamiento'].required = False
        self.fields['tipo_tinta'].required = False
        self.fields['sellado_tipo'].required = False
        self.fields['cuenta_contable'].required = False
        self.fields['servicio'].required = False

    def clean_codigo(self):
        """Validar que el código sea único"""
        codigo = self.cleaned_data['codigo']
        if ProductoTerminado.objects.filter(codigo=codigo).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe un producto con este código.')
        return codigo

    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        
        # Validar que si se especifica zipper, tenga medida
        if cleaned_data.get('sellado_zipper_tipo') and not cleaned_data.get('sellado_zipper_medida'):
            self.add_error('sellado_zipper_medida', 'La medida del zipper es requerida cuando se especifica el tipo.')
        
        # Validar que si se especifica válvula, tenga medida
        if cleaned_data.get('sellado_valvula_tipo') and not cleaned_data.get('sellado_valvula_medida'):
            self.add_error('sellado_valvula_medida', 'La medida de la válvula es requerida cuando se especifica el tipo.')
        
        # Validar que si se especifica troquel, tenga medida
        if cleaned_data.get('sellado_troquel_tipo') and not cleaned_data.get('sellado_troquel_medida'):
            self.add_error('sellado_troquel_medida', 'La medida del troquel es requerida cuando se especifica el tipo.')
        
        return cleaned_data

