from django import forms
from .models import ProductoTerminado


class ProductoSearchForm(forms.Form):
    q = forms.CharField(label='Buscar', required=False,
                        widget=forms.TextInput(attrs={'class': 'form-control',
                                                      'placeholder': 'Código o nombre'}))


class ProductoTerminadoForm(forms.ModelForm):
    class Meta:
        model = ProductoTerminado
        exclude = ['creado_en', 'actualizado_en', 'creado_por', 'actualizado_por']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            elif not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control')

