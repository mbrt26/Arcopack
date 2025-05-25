from django.contrib import admin
from django import forms
from django.apps import apps
from django.urls import path
from django.http import JsonResponse
from django.db.models.functions import Concat
from django.db.models import Value, CharField, Q
from django.views.decorators.csrf import csrf_exempt
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import (
    # Modelo Principal de Producción
    OrdenProduccion,
    OrdenProduccionProceso,
    # Modelos de Registro de Procesos
    RegistroImpresion, Refilado, Sellado, Doblado,
    # Modelos de Detalles de Procesos
    ParoImpresion, DesperdicioImpresion, ConsumoTintaImpresion, ConsumoSustratoImpresion,
    ParoRefilado, DesperdicioRefilado, ConsumoWipRefilado, ConsumoMpRefilado,
    ParoSellado, DesperdicioSellado, ConsumoWipSellado, ConsumoMpSellado,
    ParoDoblado, DesperdicioDoblado, ConsumoWipDoblado, ConsumoMpDoblado,
)
from inventario.models import LoteProductoEnProceso, LoteProductoTerminado
from configuracion.models import Proceso

class ProduccionLoteInline(GenericTabularInline):
    model = LoteProductoEnProceso
    ct_field = 'proceso_origen_content_type'
    ct_fk_field = 'proceso_origen_object_id'
    fields = ('lote_id', 'cantidad_producida_primaria', 'unidad_medida_primaria', 'ubicacion', 'estado', 'observaciones')
    extra = 1
    verbose_name = "Lote Producido (WIP)"
    verbose_name_plural = "Lotes Producidos (WIP)"
    show_change_link = True

class ProduccionLoteTerminadoInline(GenericTabularInline):
    model = LoteProductoTerminado
    ct_field = 'proceso_final_content_type'
    ct_fk_field = 'proceso_final_object_id'
    fields = ('lote_id', 'cantidad_producida', 'cantidad_actual', 'ubicacion', 'estado', 'observaciones')
    extra = 1
    verbose_name = "Lote Producido (PT)"
    verbose_name_plural = "Lotes Producidos (PT)"
    show_change_link = True

# === Formularios personalizados para Consumos ===
class ConsumoBaseMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance:
            return

        # Determinar el campo registro y la orden de producción según el modelo
        registro = None
        if hasattr(self.instance, 'registro_impresion'):
            registro = self.instance.registro_impresion
        elif hasattr(self.instance, 'registro_refilado'):
            registro = self.instance.registro_refilado
        elif hasattr(self.instance, 'registro_sellado'):
            registro = self.instance.registro_sellado
        elif hasattr(self.instance, 'registro_doblado'):
            registro = self.instance.registro_doblado

        if registro and registro.orden_produccion:
            op = registro.orden_produccion
            
            # Determinar si es consumo de WIP o MP basado en el modelo
            if isinstance(self.instance, (ConsumoWipRefilado, ConsumoWipSellado, ConsumoWipDoblado)):
                # Para consumos WIP, filtrar por orden de producción
                self.fields['lote_consumido'].queryset = self.fields['lote_consumido'].queryset.filter(
                    orden_produccion=op,
                    estado='DISPONIBLE'
                )
            elif isinstance(self.instance, ConsumoSustratoImpresion):
                # Para consumo de sustrato, filtrar por materia prima específica
                self.fields['lote_consumido'].queryset = self.fields['lote_consumido'].queryset.filter(
                    materia_prima=op.sustrato,
                    estado='DISPONIBLE'
                )
            elif isinstance(self.instance, (ConsumoMpRefilado, ConsumoMpSellado, ConsumoMpDoblado)):
                # Para consumos MP, filtrar solo por estado disponible (ya que pueden ser materiales auxiliares)
                self.fields['lote_consumido'].queryset = self.fields['lote_consumido'].queryset.filter(
                    estado='DISPONIBLE'
                )

class ConsumoSustratoImpresionForm(ConsumoBaseMixin):
    class Meta:
        model = ConsumoSustratoImpresion
        fields = '__all__'
        widgets = {'lote_consumido': forms.Select(attrs={'class': 'lote-mp-select'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.registro_impresion_id:
            op = self.instance.registro_impresion.orden_produccion
            self.fields['lote_consumido'].queryset = self.fields['lote_consumido'].queryset.filter(
                materia_prima=op.sustrato,
                estado='DISPONIBLE'
            )

class ConsumoWipRefiladoForm(forms.ModelForm):
    class Meta:
        model = ConsumoWipRefilado
        fields = '__all__'
        widgets = {
            'lote_consumido': forms.Select(attrs={
                'class': 'lote-wip-select',
                'data-op-field': 'id_orden_produccion'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Obtener queryset base
        queryset = LoteProductoEnProceso.objects.all()
        
        # Manejar tanto edición como creación
        if self.instance.pk:  # Edición de instancia existente
            if hasattr(self.instance, 'registro_refilado') and self.instance.registro_refilado:
                refilado = self.instance.registro_refilado
                if hasattr(refilado, 'orden_produccion_id') and refilado.orden_produccion_id:
                    op_id = refilado.orden_produccion_id
                    queryset = queryset.filter(
                        orden_produccion_id=op_id,
                        estado='DISPONIBLE'
                    )
                    print(f"DEBUG - Lotes WIP disponibles para OP {op_id}: {queryset.count()}")
        else:  # Nueva instancia
            # Obtener OP del request (para casos de creación desde Refilado)
            op_id = None
            if hasattr(self, 'initial') and 'registro_refilado' in self.initial:
                refilado_id = self.initial['registro_refilado']
                from .models import Refilado
                try:
                    refilado = Refilado.objects.get(pk=refilado_id)
                    op_id = refilado.orden_produccion_id
                    queryset = queryset.filter(
                        orden_produccion_id=op_id,
                        estado='DISPONIBLE'
                    )
                    print(f"DEBUG - Lotes WIP disponibles para nueva instancia (OP {op_id}): {queryset.count()}")
                except Refilado.DoesNotExist:
                    pass
        
        # Formatear visualización
        self.fields['lote_consumido'].label_from_instance = lambda obj: (
            f"{obj.lote_id} - {float(obj.cantidad_actual):.2f} Kg"
        )
        self.fields['lote_consumido'].queryset = queryset
        
        # Debug final
        print(f"DEBUG - Queryset final para lote_consumido: {list(queryset)}")

class ConsumoWipSelladoForm(forms.ModelForm):
    class Meta:
        model = ConsumoWipSellado
        fields = '__all__'
        widgets = {'lote_consumido': forms.Select(attrs={'class': 'lote-wip-select'})}

class ConsumoWipDobladoForm(forms.ModelForm):
    class Meta:
        model = ConsumoWipDoblado
        fields = '__all__'
        widgets = {'lote_consumido': forms.Select(attrs={'class': 'lote-wip-select'})}

class ConsumoMpRefiladoForm(ConsumoBaseMixin):
    class Meta:
        model = ConsumoMpRefilado
        fields = '__all__'
        widgets = {
            'lote_consumido': forms.Select(attrs={'class': 'lote-mp-select'})
        }

class ConsumoMpSelladoForm(ConsumoBaseMixin):
    class Meta:
        model = ConsumoMpSellado
        fields = '__all__'
        widgets = {
            'lote_consumido': forms.Select(attrs={'class': 'lote-mp-select'})
        }

class ConsumoMpDobladoForm(ConsumoBaseMixin):
    class Meta:
        model = ConsumoMpDoblado
        fields = '__all__'
        widgets = {
            'lote_consumido': forms.Select(attrs={'class': 'lote-mp-select'})
        }

# === Formularios personalizados para Refilado, Sellado y Doblado ===
class RefiladoForm(forms.ModelForm):
    class Meta:
        model = Refilado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            proc = Proceso.objects.get(nombre__iexact='Refilado')
            qs = OrdenProduccion.objects.filter(
                procesos_secuencia__proceso=proc,
                is_active=True
            ).distinct()
        except Proceso.DoesNotExist:
            qs = OrdenProduccion.objects.none()
        self.fields['orden_produccion'].queryset = qs

class SelladoForm(forms.ModelForm):
    class Meta:
        model = Sellado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            proc = Proceso.objects.get(nombre__iexact='Sellado')
            qs = OrdenProduccion.objects.filter(
                procesos_secuencia__proceso=proc,
                is_active=True
            ).distinct()
        except Proceso.DoesNotExist:
            qs = OrdenProduccion.objects.none()
        self.fields['orden_produccion'].queryset = qs

class DobladoForm(forms.ModelForm):
    class Meta:
        model = Doblado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            proc = Proceso.objects.get(nombre__iexact='Doblado')
            qs = OrdenProduccion.objects.filter(
                procesos_secuencia__proceso=proc,
                is_active=True
            ).distinct()
        except Proceso.DoesNotExist:
            qs = OrdenProduccion.objects.none()
        self.fields['orden_produccion'].queryset = qs

# === Inlines Base ===
class ParoBaseInline(admin.TabularInline):
    fields = ('causa_paro', 'hora_inicio_paro', 'hora_final_paro', 'observaciones', 'is_active')
    extra = 1
    classes = ['collapse']

class DesperdicioImpresionInline(admin.TabularInline):
    model = DesperdicioImpresion
    fields = ('tipo_desperdicio', 'cantidad_kg', 'cantidad_metros', 'observaciones', 'is_active')
    extra = 1
    classes = ['collapse']

class DesperdicioBaseInline(admin.TabularInline):
    fields = ('tipo_desperdicio', 'kg_desperdicio', 'observaciones', 'is_active')
    extra = 1
    classes = ['collapse']

class ConsumoWipInline(admin.TabularInline):
    fields = ('lote_consumido', 'cantidad_kg_consumida', 'registrado_en')
    readonly_fields = ('registrado_en',)
    extra = 1
    classes = ['collapse']

class ConsumoMpInline(admin.TabularInline):
    fields = ('lote_consumido', 'cantidad_consumida', 'registrado_en')
    readonly_fields = ('registrado_en',)
    extra = 1
    classes = ['collapse']

class ConsumoSustratoInline(admin.TabularInline):
    fields = ('lote_consumido', 'cantidad_kg_consumida', 'registrado_en')
    readonly_fields = ('registrado_en',)
    extra = 1
    classes = ['collapse']

# === Inlines genéricos para producción ===
class LoteWipInline(GenericTabularInline):
    model = LoteProductoEnProceso
    ct_field = 'proceso_origen_content_type'
    ct_fk_field = 'proceso_origen_object_id'
    extra = 1

class LotePtInline(GenericTabularInline):
    model = LoteProductoTerminado
    ct_field = 'proceso_final_content_type'
    ct_fk_field = 'proceso_final_object_id'
    extra = 1

class ProduccionInlineMixin:
    """Añade inline de producción WIP o PT según la secuencia en la OP."""
    PROCESS_NAME = None

    def get_inline_instances(self, request, obj=None):
        inlines = super().get_inline_instances(request, obj)
        if not self.PROCESS_NAME:
            return inlines
        try:
            proc = Proceso.objects.get(nombre__iexact=self.PROCESS_NAME)
        except Proceso.DoesNotExist:
            return inlines
        if obj and obj.orden_produccion:
            seqs = obj.orden_produccion.procesos_secuencia.all().order_by('secuencia')
            last = seqs.last()
            if last and last.proceso_id == proc.id:
                # usar inline amigable de producto terminado
                inline = ProduccionLoteTerminadoInline(self.model, self.admin_site)
            else:
                # usar inline amigable de WIP
                inline = ProduccionLoteInline(self.model, self.admin_site)
        else:
            inline = ProduccionLoteInline(self.model, self.admin_site)
        inlines.append(inline)
        return inlines

# === Inlines para cada proceso ===
# Impresión
class ParoImpresionInline(ParoBaseInline):
    model = ParoImpresion

class ConsumoSustratoImpresionInline(ConsumoSustratoInline):
    model = ConsumoSustratoImpresion
    form = ConsumoSustratoImpresionForm

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'produccion/js/dynamic_lotes.js',
        )

class ConsumoTintaImpresionInline(admin.TabularInline):
    model = ConsumoTintaImpresion
    fields = ('tinta', 'cantidad_kg', 'lote_tinta', 'is_active')
    extra = 1
    classes = ['collapse']
    autocomplete_fields = ['tinta']

# Refilado
class ParoRefiladoInline(ParoBaseInline):
    model = ParoRefilado

class DesperdicioRefiladoInline(DesperdicioBaseInline):
    model = DesperdicioRefilado

class ConsumoWipRefiladoInline(admin.TabularInline):
    model = ConsumoWipRefilado
    form = ConsumoWipRefiladoForm
    extra = 1
    
    class Media:
        js = (
            'admin/js/jquery.init.js',
            'produccion/js/dynamic_lotes.js',
        )

class ConsumoMpRefiladoInline(ConsumoMpInline):
    model = ConsumoMpRefilado
    form = ConsumoMpRefiladoForm

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'produccion/js/dynamic_lotes.js',
        )

# Sellado
class ParoSelladoInline(ParoBaseInline):
    model = ParoSellado

class DesperdicioSelladoInline(DesperdicioBaseInline):
    model = DesperdicioSellado

class ConsumoWipSelladoInline(ConsumoWipInline):
    model = ConsumoWipSellado
    form = ConsumoWipSelladoForm

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'produccion/js/dynamic_lotes.js',
        )

class ConsumoMpSelladoInline(ConsumoMpInline):
    model = ConsumoMpSellado
    form = ConsumoMpSelladoForm

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'produccion/js/dynamic_lotes.js',
        )

# Doblado
class ParoDobladoInline(ParoBaseInline):
    model = ParoDoblado

class DesperdicioDobladoInline(DesperdicioBaseInline):
    model = DesperdicioDoblado

class ConsumoWipDobladoInline(ConsumoWipInline):
    model = ConsumoWipDoblado
    form = ConsumoWipDobladoForm

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'produccion/js/dynamic_lotes.js',
        )

class ConsumoMpDobladoInline(ConsumoMpInline):
    model = ConsumoMpDoblado
    form = ConsumoMpDobladoForm

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'produccion/js/dynamic_lotes.js',
        )

# === ModelAdmin para cada proceso ===
class OrdenProduccionProcesoInline(admin.TabularInline):
    """Inline para definir secuencia de procesos en la OP"""
    model = OrdenProduccionProceso
    extra = 1
    fields = ('proceso', 'secuencia')
    ordering = ('secuencia',)

@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(admin.ModelAdmin):
    inlines = [OrdenProduccionProcesoInline]
    list_display = ('op_numero', 'cliente', 'producto', 'cantidad_solicitada_kg', 'etapa_actual', 'is_active')
    list_filter = ('etapa_actual', 'is_active', 'fecha_creacion')
    search_fields = ('op_numero', 'cliente__razon_social', 'producto__codigo')
    readonly_fields = ('cantidad_producida_kg', 'fecha_creacion', 'creado_por', 'actualizado_por')
    fieldsets = (
        ('Identificación', {'fields': ('op_numero', 'cliente', 'producto')}),
        ('Cantidades y Fechas', {'fields': ('cantidad_solicitada_kg', 'cantidad_producida_kg', 'fecha_compromiso_entrega')}),
        ('Especificaciones', {'fields': ('sustrato', 'ancho_sustrato_mm')}),
        ('Estado', {'fields': ('etapa_actual', 'is_active')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)

class RegistroImpresionForm(forms.ModelForm):
    class Meta:
        model = RegistroImpresion
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sólo OP que tengan el proceso Impresion en su secuencia
        try:
            proc = Proceso.objects.get(nombre__iexact='Impresion')
            qs = OrdenProduccion.objects.filter(
                procesos_secuencia__proceso=proc,
                is_active=True
            ).distinct()
        except Proceso.DoesNotExist:
            qs = OrdenProduccion.objects.none()
        self.fields['orden_produccion'].queryset = qs

@admin.register(RegistroImpresion)
class RegistroImpresionAdmin(ProduccionInlineMixin, admin.ModelAdmin):
    form = RegistroImpresionForm
    PROCESS_NAME = 'Impresion'
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'lote_wip_asociado':
            LoteProductoEnProceso = apps.get_model('inventario', 'LoteProductoEnProceso')
            queryset = LoteProductoEnProceso.objects.all()
            try:
                op_id = None
                if request.resolver_match and request.resolver_match.kwargs.get('object_id'):
                    from .models import RegistroImpresion
                    obj = RegistroImpresion.objects.filter(pk=request.resolver_match.kwargs['object_id']).first()
                    if obj:
                        op_id = obj.orden_produccion_id
                if not op_id and request.POST.get('orden_produccion'):
                    op_id = request.POST.get('orden_produccion')
                if op_id:
                    queryset = queryset.filter(orden_produccion_id=op_id, estado='DISPONIBLE')
                else:
                    queryset = queryset.none()
            except Exception:
                queryset = queryset.none()
            kwargs['queryset'] = queryset
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    list_display = ('orden_produccion', 'fecha', 'maquina', 'operario_principal', 'is_active')
    list_filter = ('fecha', 'maquina', 'is_active')
    search_fields = ('orden_produccion__op_numero',)
    inlines = [
        ProduccionLoteTerminadoInline,
        ConsumoSustratoImpresionInline,
        ConsumoTintaImpresionInline,
        ParoImpresionInline,
        DesperdicioImpresionInline,
    ]
    fieldsets = (
        (None, {'fields': (
            'orden_produccion', 'fecha', 'is_active', 'lote_wip_asociado',
            'anilox', 'repeticion_mm', 'pistas', 'tipo_tinta_principal', 'aprobado_por',
            'usa_retal', 'pistas_retal'
        )}),
        ('Operación', {'fields': ('maquina', 'operario_principal', 'hora_inicio', 'hora_final')}),
    )

@admin.register(Refilado)
class RefiladoAdmin(ProduccionInlineMixin, admin.ModelAdmin):
    form = RefiladoForm
    PROCESS_NAME = 'Refilado'
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'orden_produccion':
            from .models import OrdenProduccion
            try:
                proc = Proceso.objects.get(nombre__iexact=self.PROCESS_NAME)
                kwargs['queryset'] = OrdenProduccion.objects.filter(procesos_secuencia__proceso=proc).distinct()
            except Proceso.DoesNotExist:
                kwargs['queryset'] = OrdenProduccion.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('lote-wip-json/', csrf_exempt(self.admin_site.admin_view(self.lote_wip_json)), name='lote-wip-json'),
        ]
        return custom_urls + urls
    
    def lote_wip_json(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        op_id = request.GET.get('op_id')
        if op_id:
            from django.db.models import CharField
            lotes = LoteProductoEnProceso.objects.filter(
                orden_produccion_id=op_id,
                estado='DISPONIBLE'
            ).annotate(
                text=Concat('lote_id', Value(' - '), 'cantidad_actual', output_field=CharField())
            ).values('id', 'text')
            return JsonResponse(list(lotes), safe=False)
        return JsonResponse([], safe=False)

    inlines = [
        ProduccionLoteTerminadoInline,
        ParoRefiladoInline, 
        DesperdicioRefiladoInline, 
        ConsumoWipRefiladoInline, 
        ConsumoMpRefiladoInline,
    ]

@admin.register(Sellado)
class SelladoAdmin(ProduccionInlineMixin, admin.ModelAdmin):
    form = SelladoForm
    PROCESS_NAME = 'Sellado'
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'orden_produccion':
            from .models import OrdenProduccion
            try:
                proc = Proceso.objects.get(nombre__iexact=self.PROCESS_NAME)
                kwargs['queryset'] = OrdenProduccion.objects.filter(procesos_secuencia__proceso=proc).distinct()
            except Proceso.DoesNotExist:
                kwargs['queryset'] = OrdenProduccion.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    list_display = ('orden_produccion', 'fecha', 'maquina', 'operario_principal', 'is_active')
    list_filter = ('fecha', 'maquina', 'is_active')
    search_fields = ('orden_produccion__op_numero',)
    inlines = [
        ProduccionLoteTerminadoInline,
        ConsumoWipSelladoInline,
        ConsumoMpSelladoInline,
        ParoSelladoInline,
        DesperdicioSelladoInline,
    ]
    fieldsets = (
        (None, {'fields': ('orden_produccion', 'fecha', 'is_active')}),
        ('Operación', {'fields': ('maquina', 'operario_principal', 'hora_inicio', 'hora_final')}),
    )

@admin.register(Doblado)
class DobladoAdmin(ProduccionInlineMixin, admin.ModelAdmin):
    form = DobladoForm
    PROCESS_NAME = 'Doblado'
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'orden_produccion':
            from .models import OrdenProduccion
            try:
                proc = Proceso.objects.get(nombre__iexact=self.PROCESS_NAME)
                kwargs['queryset'] = OrdenProduccion.objects.filter(procesos_secuencia__proceso=proc).distinct()
            except Proceso.DoesNotExist:
                kwargs['queryset'] = OrdenProduccion.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    list_display = ('orden_produccion', 'fecha', 'maquina', 'operario_principal', 'is_active')
    list_filter = ('fecha', 'maquina', 'is_active')
    search_fields = ('orden_produccion__op_numero',)
    inlines = [
        ProduccionLoteTerminadoInline,
        ConsumoWipDobladoInline,
        ConsumoMpDobladoInline,
        ParoDobladoInline,
        DesperdicioDobladoInline,
    ]
    fieldsets = (
        (None, {'fields': ('orden_produccion', 'fecha', 'is_active')}),
        ('Operación', {'fields': ('maquina', 'operario_principal', 'hora_inicio', 'hora_final')}),
    )

# =============================================
# === FIN REGISTROS DE PROCESO ===
# =============================================