"""
Archivo temporal con las actualizaciones para los formularios de Refilado, Sellado y Doblado
"""

# Actualización para RegistroRefiladoForm
def actualizar_refilado():
    """
    Código para actualizar el formulario RegistroRefiladoForm
    """
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        initial = kwargs.get('initial', {})
        
        # Si estamos editando un registro existente, inicializamos los campos auxiliares
        if instance:
            if instance.hora_inicio:
                initial['fecha_hora_inicio'] = instance.hora_inicio
            if instance.hora_final:
                initial['fecha_hora_final'] = instance.hora_final
            kwargs['initial'] = initial
            
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Procesamos los campos de fecha y hora
        fecha_hora_inicio = cleaned_data.get('fecha_hora_inicio')
        fecha_hora_final = cleaned_data.get('fecha_hora_final')
        
        # Si se proporcionaron los campos auxiliares, actualizamos los campos reales
        if fecha_hora_inicio:
            cleaned_data['hora_inicio'] = fecha_hora_inicio
        if fecha_hora_final:
            cleaned_data['hora_final'] = fecha_hora_final
        
        # Ahora validamos con los campos actualizados
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_final = cleaned_data.get('hora_final')

        if hora_inicio and hora_final and hora_final <= hora_inicio:
            self.add_error('fecha_hora_final', 'La hora final debe ser posterior a la hora de inicio')

        return cleaned_data

# Actualización para RegistroSelladoForm
def actualizar_sellado():
    """
    Código para actualizar el formulario RegistroSelladoForm
    """
    # Campos auxiliares para manejar la entrada de fecha y hora
    fecha_hora_inicio = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }
        )
    )
    fecha_hora_final = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }
        )
    )
    
    class Meta:
        model = Sellado
        fields = [
            'orden_produccion', 'maquina', 'operario_principal',
            'fecha', 'hora_inicio', 'hora_final'
        ]
        widgets = {
            'fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            # Ocultamos los campos originales
            'hora_inicio': forms.HiddenInput(),
            'hora_final': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        initial = kwargs.get('initial', {})
        
        # Si estamos editando un registro existente, inicializamos los campos auxiliares
        if instance:
            if instance.hora_inicio:
                initial['fecha_hora_inicio'] = instance.hora_inicio
            if instance.hora_final:
                initial['fecha_hora_final'] = instance.hora_final
            kwargs['initial'] = initial
            
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Procesamos los campos de fecha y hora
        fecha_hora_inicio = cleaned_data.get('fecha_hora_inicio')
        fecha_hora_final = cleaned_data.get('fecha_hora_final')
        
        # Si se proporcionaron los campos auxiliares, actualizamos los campos reales
        if fecha_hora_inicio:
            cleaned_data['hora_inicio'] = fecha_hora_inicio
        if fecha_hora_final:
            cleaned_data['hora_final'] = fecha_hora_final
        
        # Ahora validamos con los campos actualizados
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_final = cleaned_data.get('hora_final')

        if hora_inicio and hora_final and hora_final <= hora_inicio:
            self.add_error('fecha_hora_final', 'La hora final debe ser posterior a la hora de inicio')

        return cleaned_data

# Actualización para RegistroDobladoForm
def actualizar_doblado():
    """
    Código para actualizar el formulario RegistroDobladoForm
    """
    # Campos auxiliares para manejar la entrada de fecha y hora
    fecha_hora_inicio = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }
        )
    )
    fecha_hora_final = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }
        )
    )
    
    class Meta:
        model = Doblado
        fields = [
            'orden_produccion', 'maquina', 'operario_principal',
            'fecha', 'hora_inicio', 'hora_final'
        ]
        widgets = {
            'fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            # Ocultamos los campos originales
            'hora_inicio': forms.HiddenInput(),
            'hora_final': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        initial = kwargs.get('initial', {})
        
        # Si estamos editando un registro existente, inicializamos los campos auxiliares
        if instance:
            if instance.hora_inicio:
                initial['fecha_hora_inicio'] = instance.hora_inicio
            if instance.hora_final:
                initial['fecha_hora_final'] = instance.hora_final
            kwargs['initial'] = initial
            
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Procesamos los campos de fecha y hora
        fecha_hora_inicio = cleaned_data.get('fecha_hora_inicio')
        fecha_hora_final = cleaned_data.get('fecha_hora_final')
        
        # Si se proporcionaron los campos auxiliares, actualizamos los campos reales
        if fecha_hora_inicio:
            cleaned_data['hora_inicio'] = fecha_hora_inicio
        if fecha_hora_final:
            cleaned_data['hora_final'] = fecha_hora_final
        
        # Ahora validamos con los campos actualizados
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_final = cleaned_data.get('hora_final')

        if hora_inicio and hora_final and hora_final <= hora_inicio:
            self.add_error('fecha_hora_final', 'La hora final debe ser posterior a la hora de inicio')

        return cleaned_data
