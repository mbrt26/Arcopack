from django import forms
from .models import ProductoTerminado

class ProductoTerminadoForm(forms.ModelForm):
    class Meta:
        model = ProductoTerminado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = widget.attrs.get('class', '')
            if widget.__class__.__name__ == 'Select' or isinstance(widget, forms.Select):
                widget.attrs['class'] = f'{css} form-select'.strip()
            else:
                widget.attrs['class'] = f'{css} form-control'.strip()
