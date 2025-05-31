from django import forms
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.forms import BaseInlineFormSet
from django.contrib.contenttypes.models import ContentType
from .models import (
    RegistroImpresion, OrdenProduccion, ParoImpresion,
    DesperdicioImpresion, ConsumoTintaImpresion, ConsumoSustratoImpresion,
    Refilado, ParoRefilado, ConsumoWipRefilado,
    Sellado, ParoSellado, ConsumoWipSellado,
    Doblado, ParoDoblado, ConsumoWipDoblado
)
from configuracion.models import Maquina, RodilloAnilox, CausaParo, Ubicacion
from inventario.models import Tinta, LoteProductoTerminado, LoteProductoEnProceso
from personal.models import Colaborador


class OrdenProduccionForm(forms.ModelForm):
    class Meta:
        model = OrdenProduccion
        fields = [
            'producto', 'cantidad_solicitada_kg', 'fecha_compromiso_entrega',
            'fecha_estimada_inicio', 'observaciones'
        ]
        widgets = {
            'fecha_compromiso_entrega': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'fecha_estimada_inicio': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'observaciones': forms.Textarea(
                attrs={
                    'rows': 3
                }
            )
        }


class DesperdicioImpresionForm(forms.ModelForm):
    class Meta:
        model = DesperdicioImpresion
        fields = ['tipo_desperdicio', 'cantidad_kg', 'observaciones']


class ConsumoTintaImpresionForm(forms.ModelForm):
    class Meta:
        model = ConsumoTintaImpresion
        fields = ['tinta', 'cantidad_kg', 'lote_tinta']


class ConsumoSustratoImpresionForm(forms.ModelForm):
    class Meta:
        model = ConsumoSustratoImpresion
        fields = ['lote_consumido', 'cantidad_kg_consumida']


class ProduccionImpresionForm(forms.ModelForm):
    """Form for production quantities (PT lots) in impresion process."""
    class Meta:
        model = LoteProductoTerminado
        fields = ['lote_id', 'cantidad_producida', 'ubicacion', 'observaciones']
        widgets = {
            'lote_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: PT-2025-001'
            }),
            'cantidad_producida': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'ubicacion': forms.Select(attrs={
                'class': 'form-control'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones del lote producido'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter ubicaciones to only active ones
        self.fields['ubicacion'].queryset = Ubicacion.objects.filter(is_active=True)

    def clean_cantidad_producida(self):
        cantidad = self.cleaned_data.get('cantidad_producida')
        if cantidad and cantidad <= 0:
            raise forms.ValidationError('La cantidad producida debe ser mayor a 0')
        return cantidad


class BaseProduccionImpresionFormSet(forms.BaseFormSet):
    """Custom formset for production quantities with GenericForeignKey support."""
    
    def __init__(self, *args, **kwargs):
        self.registro_impresion = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Save the formset instances with proper GenericForeignKey setup."""
        instances = []
        
        for form in self.forms:
            if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data:  # Only process forms with data
                    instance = form.save(commit=False)
                    
                    if commit and self.registro_impresion:
                        # Set up the GenericForeignKey relationship
                        content_type = ContentType.objects.get_for_model(RegistroImpresion)
                        instance.proceso_final_content_type = content_type
                        instance.proceso_final_object_id = self.registro_impresion.pk
                        instance.producto_terminado = self.registro_impresion.orden_produccion.producto
                        instance.orden_produccion = self.registro_impresion.orden_produccion
                        instance.fecha_produccion = self.registro_impresion.fecha
                        instance.cantidad_actual = instance.cantidad_producida
                        instance.estado = 'DISPONIBLE'
                        instance.save()
                    
                    instances.append(instance)
        
        return instances


DesperdicioImpresionFormset = forms.inlineformset_factory(
    RegistroImpresion, DesperdicioImpresion,
    form=DesperdicioImpresionForm,
    extra=1,
    can_delete=True
)

ConsumoTintaImpresionFormset = forms.inlineformset_factory(
    RegistroImpresion, ConsumoTintaImpresion,
    form=ConsumoTintaImpresionForm,
    extra=1,
    can_delete=True
)

ConsumoSustratoImpresionFormset = forms.inlineformset_factory(
    RegistroImpresion, ConsumoSustratoImpresion,
    form=ConsumoSustratoImpresionForm,
    extra=1,
    can_delete=True
)

ProduccionImpresionFormset = forms.formset_factory(
    ProduccionImpresionForm,
    formset=BaseProduccionImpresionFormSet,
    extra=1,
    can_delete=True
)


class RegistroImpresionForm(forms.ModelForm):
    class Meta:
        model = RegistroImpresion
        fields = [
            'orden_produccion', 'maquina', 'operario_principal',
            'fecha', 'hora_inicio', 'hora_final', 'anilox',
            'repeticion_mm', 'pistas', 'tipo_tinta_principal',
            'embobinado', 'tipo_montaje', 'usa_retal', 'pistas_retal',
            'aprobado_por'
        ]

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_final = cleaned_data.get('hora_final')

        if hora_inicio and hora_final and hora_final <= hora_inicio:
            self.add_error('hora_final', 'La hora final debe ser posterior a la hora de inicio')

        usa_retal = cleaned_data.get('usa_retal')
        pistas = cleaned_data.get('pistas')
        pistas_retal = cleaned_data.get('pistas_retal')
        if usa_retal and pistas and pistas_retal and pistas_retal > pistas:
            self.add_error('pistas_retal', 'El número de pistas en retal no puede ser mayor al número total de pistas')

        return cleaned_data


class ParoImpresionForm(forms.ModelForm):
    class Meta:
        model = ParoImpresion
        fields = ['causa_paro', 'hora_inicio_paro', 'hora_final_paro', 'observaciones']


ParoImpresionFormset = forms.inlineformset_factory(
    RegistroImpresion, ParoImpresion,
    form=ParoImpresionForm,
    extra=1,
    can_delete=True
)


class RegistroRefiladoForm(forms.ModelForm):
    class Meta:
        model = Refilado
        fields = [
            'orden_produccion', 'maquina', 'operario_principal',
            'fecha', 'hora_inicio', 'hora_final'
        ]

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_final = cleaned_data.get('hora_final')

        if hora_inicio and hora_final and hora_final <= hora_inicio:
            self.add_error('hora_final', 'La hora final debe ser posterior a la hora de inicio')

        return cleaned_data


class ParoRefiladoForm(forms.ModelForm):
    class Meta:
        model = ParoRefilado
        fields = ['causa_paro', 'hora_inicio_paro', 'hora_final_paro', 'observaciones']


class ConsumoWipRefiladoForm(forms.ModelForm):
    class Meta:
        model = ConsumoWipRefilado
        fields = ['lote_consumido', 'cantidad_kg_consumida']


ParoRefiladoFormset = forms.inlineformset_factory(
    Refilado, ParoRefilado,
    form=ParoRefiladoForm,
    extra=1,
    can_delete=True
)

ConsumoWipRefiladoFormset = forms.inlineformset_factory(
    Refilado, ConsumoWipRefilado,
    form=ConsumoWipRefiladoForm,
    extra=1,
    can_delete=True
)


# Formulario para registrar cantidades producidas en Refilado
class ProduccionRefiladoForm(forms.ModelForm):
    class Meta:
        model = LoteProductoEnProceso
        fields = ['lote_id', 'cantidad_producida_primaria', 'cantidad_producida_secundaria', 'ubicacion', 'observaciones']
        widgets = {
            'lote_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID del lote'}),
            'cantidad_producida_primaria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'cantidad_producida_secundaria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'ubicacion': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'lote_id': 'ID Lote',
            'cantidad_producida_primaria': 'Cantidad (Kg)',
            'cantidad_producida_secundaria': 'Cantidad (m)',
            'ubicacion': 'Ubicación',
            'observaciones': 'Observaciones',
        }

    def __init__(self, *args, **kwargs):
        self.orden_produccion = kwargs.pop('orden_produccion', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar ubicaciones activas
        from configuracion.models import Ubicacion
        self.fields['ubicacion'].queryset = Ubicacion.objects.filter(is_active=True)

    def clean_cantidad_producida_primaria(self):
        cantidad = self.cleaned_data.get('cantidad_producida_primaria')
        if cantidad and cantidad <= 0:
            raise forms.ValidationError('La cantidad producida debe ser mayor a 0')
        return cantidad


class BaseProduccionRefiladoFormSet(forms.BaseFormSet):
    """Custom formset for refilado production quantities with GenericForeignKey support."""
    
    def __init__(self, *args, **kwargs):
        self.registro_refilado = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Save the formset instances with proper GenericForeignKey setup."""
        instances = []
        
        for form in self.forms:
            if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data and any(form.cleaned_data.values()):  # Only process forms with data
                    instance = form.save(commit=False)
                    
                    if commit and self.registro_refilado:
                        # Set up the GenericForeignKey relationship
                        content_type = ContentType.objects.get_for_model(Refilado)
                        instance.proceso_origen_content_type = content_type
                        instance.proceso_origen_object_id = self.registro_refilado.pk
                        instance.producto_terminado = self.registro_refilado.orden_produccion.producto
                        instance.orden_produccion = self.registro_refilado.orden_produccion
                        instance.fecha_produccion = self.registro_refilado.fecha
                        instance.cantidad_actual = instance.cantidad_producida_primaria
                        instance.estado = 'DISPONIBLE'
                        
                        # Set unidad_medida_primaria based on the product
                        from configuracion.models import UnidadMedida
                        try:
                            kg_unit = UnidadMedida.objects.get(codigo='Kg')
                            instance.unidad_medida_primaria = kg_unit
                        except UnidadMedida.DoesNotExist:
                            pass
                        
                        if instance.cantidad_producida_secundaria:
                            try:
                                m_unit = UnidadMedida.objects.get(codigo='m')
                                instance.unidad_medida_secundaria = m_unit
                            except UnidadMedida.DoesNotExist:
                                pass
                        
                        instance.save()
                    
                    instances.append(instance)
        
        return instances


# Formset para múltiples registros de producción en Refilado
ProduccionRefiladoFormSet = forms.formset_factory(
    ProduccionRefiladoForm,
    formset=BaseProduccionRefiladoFormSet,
    extra=1,
    can_delete=True
)


class ConsumoWipSelladoForm(forms.ModelForm):
    class Meta:
        model = ConsumoWipSellado
        fields = ['lote_consumido', 'cantidad_kg_consumida']


class ParoSelladoForm(forms.ModelForm):
    class Meta:
        model = ParoSellado
        fields = ['causa_paro', 'hora_inicio_paro', 'hora_final_paro', 'observaciones']


class RegistroSelladoForm(forms.ModelForm):
    class Meta:
        model = Sellado
        fields = [
            'orden_produccion', 'maquina', 'operario_principal',
            'fecha', 'hora_inicio', 'hora_final'
        ]

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_final = cleaned_data.get('hora_final')

        if hora_inicio and hora_final and hora_final <= hora_inicio:
            self.add_error('hora_final', 'La hora final debe ser posterior a la hora de inicio')

        return cleaned_data


# Formset para ParoSellado
ParoSelladoFormset = forms.inlineformset_factory(
    Sellado, ParoSellado,
    form=ParoSelladoForm,
    extra=1,
    can_delete=True
)

# Formset para ConsumoWipSellado
ConsumoWipSelladoFormset = forms.inlineformset_factory(
    Sellado, ConsumoWipSellado,
    form=ConsumoWipSelladoForm,
    extra=1,
    can_delete=True
)


# Formulario para registrar cantidades producidas en Sellado
class ProduccionSelladoForm(forms.ModelForm):
    class Meta:
        model = LoteProductoEnProceso
        fields = ['lote_id', 'cantidad_producida_primaria', 'cantidad_producida_secundaria', 'ubicacion', 'observaciones']
        widgets = {
            'lote_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID del lote'}),
            'cantidad_producida_primaria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'cantidad_producida_secundaria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'ubicacion': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'lote_id': 'ID Lote',
            'cantidad_producida_primaria': 'Cantidad (Kg)',
            'cantidad_producida_secundaria': 'Cantidad (m)',
            'ubicacion': 'Ubicación',
            'observaciones': 'Observaciones',
        }

    def __init__(self, *args, **kwargs):
        self.orden_produccion = kwargs.pop('orden_produccion', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar ubicaciones activas
        from configuracion.models import Ubicacion
        self.fields['ubicacion'].queryset = Ubicacion.objects.filter(is_active=True)

    def clean_cantidad_producida_primaria(self):
        cantidad = self.cleaned_data.get('cantidad_producida_primaria')
        if cantidad and cantidad <= 0:
            raise forms.ValidationError('La cantidad producida debe ser mayor a 0')
        return cantidad


class BaseProduccionSelladoFormSet(forms.BaseFormSet):
    """Custom formset for sellado production quantities with GenericForeignKey support."""
    
    def __init__(self, *args, **kwargs):
        self.registro_sellado = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Save the formset instances with proper GenericForeignKey setup."""
        instances = []
        
        for form in self.forms:
            if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data and any(form.cleaned_data.values()):  # Only process forms with data
                    instance = form.save(commit=False)
                    
                    if commit and self.registro_sellado:
                        # Set up the GenericForeignKey relationship
                        content_type = ContentType.objects.get_for_model(Sellado)
                        instance.proceso_origen_content_type = content_type
                        instance.proceso_origen_object_id = self.registro_sellado.pk
                        instance.producto_terminado = self.registro_sellado.orden_produccion.producto
                        instance.orden_produccion = self.registro_sellado.orden_produccion
                        instance.fecha_produccion = self.registro_sellado.fecha
                        instance.cantidad_actual = instance.cantidad_producida_primaria
                        instance.estado = 'DISPONIBLE'
                        
                        # Set unidad_medida_primaria based on the product
                        from configuracion.models import UnidadMedida
                        try:
                            kg_unit = UnidadMedida.objects.get(codigo='Kg')
                            instance.unidad_medida_primaria = kg_unit
                        except UnidadMedida.DoesNotExist:
                            pass
                        
                        if instance.cantidad_producida_secundaria:
                            try:
                                m_unit = UnidadMedida.objects.get(codigo='m')
                                instance.unidad_medida_secundaria = m_unit
                            except UnidadMedida.DoesNotExist:
                                pass
                        
                        instance.save()
                    
                    instances.append(instance)
        
        return instances


# Formset para múltiples registros de producción en Sellado
ProduccionSelladoFormSet = forms.formset_factory(
    ProduccionSelladoForm,
    formset=BaseProduccionSelladoFormSet,
    extra=1,
    can_delete=True
)


class ConsumoWipDobladoForm(forms.ModelForm):
    class Meta:
        model = ConsumoWipDoblado
        fields = ['lote_consumido', 'cantidad_kg_consumida']


class ParoDobladoForm(forms.ModelForm):
    class Meta:
        model = ParoDoblado
        fields = ['causa_paro', 'hora_inicio_paro', 'hora_final_paro', 'observaciones']


class RegistroDobladoForm(forms.ModelForm):
    class Meta:
        model = Doblado
        fields = [
            'orden_produccion', 'maquina', 'operario_principal',
            'fecha', 'hora_inicio', 'hora_final'
        ]

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_final = cleaned_data.get('hora_final')

        if hora_inicio and hora_final and hora_final <= hora_inicio:
            self.add_error('hora_final', 'La hora final debe ser posterior a la hora de inicio')

        return cleaned_data


# Formset para ParoDoblado
ParoDobladoFormset = forms.inlineformset_factory(
    Doblado, ParoDoblado,
    form=ParoDobladoForm,
    extra=1,
    can_delete=True
)

# Formset para ConsumoWipDoblado
ConsumoWipDobladoFormset = forms.inlineformset_factory(
    Doblado, ConsumoWipDoblado,
    form=ConsumoWipDobladoForm,
    extra=1,
    can_delete=True
)


# Formulario para registrar cantidades producidas en Doblado
class ProduccionDobladoForm(forms.ModelForm):
    class Meta:
        model = LoteProductoEnProceso
        fields = ['lote_id', 'cantidad_producida_primaria', 'cantidad_producida_secundaria', 'ubicacion', 'observaciones']
        widgets = {
            'lote_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID del lote'}),
            'cantidad_producida_primaria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'cantidad_producida_secundaria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'ubicacion': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'lote_id': 'ID Lote',
            'cantidad_producida_primaria': 'Cantidad (Kg)',
            'cantidad_producida_secundaria': 'Cantidad (m)',
            'ubicacion': 'Ubicación',
            'observaciones': 'Observaciones',
        }

    def __init__(self, *args, **kwargs):
        self.orden_produccion = kwargs.pop('orden_produccion', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar ubicaciones activas
        from configuracion.models import Ubicacion
        self.fields['ubicacion'].queryset = Ubicacion.objects.filter(is_active=True)

    def clean_cantidad_producida_primaria(self):
        cantidad = self.cleaned_data.get('cantidad_producida_primaria')
        if cantidad and cantidad <= 0:
            raise forms.ValidationError('La cantidad producida debe ser mayor a 0')
        return cantidad


class BaseProduccionDobladoFormSet(forms.BaseFormSet):
    """Custom formset for doblado production quantities with GenericForeignKey support."""
    
    def __init__(self, *args, **kwargs):
        self.registro_doblado = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Save the formset instances with proper GenericForeignKey setup."""
        instances = []
        
        for form in self.forms:
            if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data and any(form.cleaned_data.values()):  # Only process forms with data
                    instance = form.save(commit=False)
                    
                    if commit and self.registro_doblado:
                        # Set up the GenericForeignKey relationship
                        content_type = ContentType.objects.get_for_model(Doblado)
                        instance.proceso_origen_content_type = content_type
                        instance.proceso_origen_object_id = self.registro_doblado.pk
                        instance.producto_terminado = self.registro_doblado.orden_produccion.producto
                        instance.orden_produccion = self.registro_doblado.orden_produccion
                        instance.fecha_produccion = self.registro_doblado.fecha
                        instance.cantidad_actual = instance.cantidad_producida_primaria
                        instance.estado = 'DISPONIBLE'
                        
                        # Set unidad_medida_primaria based on the product
                        from configuracion.models import UnidadMedida
                        try:
                            kg_unit = UnidadMedida.objects.get(codigo='Kg')
                            instance.unidad_medida_primaria = kg_unit
                        except UnidadMedida.DoesNotExist:
                            pass
                        
                        if instance.cantidad_producida_secundaria:
                            try:
                                m_unit = UnidadMedida.objects.get(codigo='m')
                                instance.unidad_medida_secundaria = m_unit
                            except UnidadMedida.DoesNotExist:
                                pass
                        
                        instance.save()
                    
                    instances.append(instance)
        
        return instances


# Formset para múltiples registros de producción en Doblado
ProduccionDobladoFormSet = forms.formset_factory(
    ProduccionDobladoForm,
    formset=BaseProduccionDobladoFormSet,
    extra=1,
    can_delete=True
)
