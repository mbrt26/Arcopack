from django import forms
from .models import ProductoTerminado

class ProductoTerminadoForm(forms.ModelForm):
    class Meta:
        model = ProductoTerminado
        fields = [
            'codigo', 'nombre', 'cliente', 'linea', 'sublinea',
            'tipo_materia_prima', 'unidad_medida', 'estado',
            'medida_en', 'largo', 'ancho', 'ancho_rollo',
            'metros_lineales', 'calibre_um', 'factor_decimal',
            'tipo_material', 'servicio', 'archivo_adjunto',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')
