# produccion/serializers.py

from rest_framework import serializers
from decimal import Decimal

# Importar modelos de esta app
from .models import (
    OrdenProduccion, RegistroImpresion, Refilado, Sellado, Doblado, OrdenProduccionProceso,
    # Los modelos de detalle como Paro*, Desperdicio*, Consumo* no suelen
    # necesitar serializers propios si se manejan vía inlines o acciones,
    # a menos que quieras endpoints específicos para ellos.
)
# Importar modelos relacionados de otras apps (solo si se usan aquí para validación o representación)
from configuracion.models import Proceso
from inventario.models import LoteMateriaPrima, LoteProductoEnProceso, LoteProductoTerminado
# from clientes.models import Cliente # Necesario para validación o representación profunda
# from productos.models import ProductoTerminado # Necesario para validación o representación profunda
# from inventario.models import MateriaPrima, Tinta # Necesario para validación o representación profunda

# =============================================
# === SERIALIZER PARA ORDEN DE PRODUCCIÓN ===
# =============================================

class LoteProductoEnProcesoSerializer(serializers.ModelSerializer):
    """Serializer básico para LoteProductoEnProceso (WIP)."""
    producto_terminado_nombre = serializers.CharField(source='producto_terminado.nombre', read_only=True)
    ubicacion_nombre = serializers.CharField(source='ubicacion.nombre', read_only=True)
    orden_produccion_numero = serializers.CharField(source='orden_produccion.op_numero', read_only=True)

    class Meta:
        model = LoteProductoEnProceso
        fields = [
            'id', 'lote_id', 'producto_terminado', 'producto_terminado_nombre',
            'orden_produccion', 'orden_produccion_numero',
            'cantidad_actual', 'unidad_medida_lote',
            'estado', 'ubicacion', 'ubicacion_nombre', 'fecha_produccion'
        ]
        read_only_fields = (
            'id', 'producto_terminado_nombre', 'ubicacion_nombre', 'orden_produccion_numero',
        )

class LoteMateriaPrimaSerializer(serializers.ModelSerializer):
    """Serializer básico para LoteMateriaPrima."""
    materia_prima_nombre = serializers.CharField(source='materia_prima.nombre', read_only=True)
    ubicacion_nombre = serializers.CharField(source='ubicacion.nombre', read_only=True)

    class Meta:
        model = LoteMateriaPrima
        fields = [
            'id', 'lote_id', 'materia_prima', 'materia_prima_nombre',
            'cantidad_actual', 'cantidad_recibida', 'unidad_medida_lote',
            'estado', 'ubicacion', 'ubicacion_nombre', 'fecha_recepcion', 'fecha_vencimiento'
        ]
        read_only_fields = (
            'id', 'materia_prima_nombre', 'ubicacion_nombre',
        )

class OrdenProduccionProcesoSerializer(serializers.ModelSerializer):
    """Serializer para mostrar la secuencia de procesos de la OP."""
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True)

    class Meta:
        model = OrdenProduccionProceso
        fields = ['id', 'proceso', 'proceso_nombre', 'secuencia']
        read_only_fields = ['id', 'proceso_nombre']

class OrdenProduccionSerializer(serializers.ModelSerializer):
    """Serializer para Ordenes de Producción."""

    # --- Representación para Lectura (Opcional) ---
    cliente_nombre = serializers.CharField(source='cliente.razon_social', read_only=True)
    producto_info = serializers.StringRelatedField(source='producto', read_only=True)
    sustrato_nombre = serializers.CharField(source='sustrato.nombre', read_only=True)
    procesos_nombres = serializers.StringRelatedField(many=True, read_only=True, source='procesos')
    etapa_actual_display = serializers.CharField(source='get_etapa_actual_display', read_only=True)

    # --- Campo para Escritura de ManyToMany ---
    procesos = serializers.PrimaryKeyRelatedField(
        queryset=Proceso.objects.all(), # Busca entre todos los procesos disponibles
        many=True, write_only=True # write_only=True si ya muestras 'procesos_nombres' para lectura
    )

    # --- Secuencia de procesos (lectura anidada) ---
    procesos_secuencia = OrdenProduccionProcesoSerializer(many=True, read_only=True)

    class Meta:
        model = OrdenProduccion
        # Listar campos explícitamente, incluyendo los read_only para lectura
        fields = [
            'id', 'op_numero', 'pedido_cliente', 'id_pedido_contable',
            'cliente', 'cliente_nombre', # ID para escritura, Nombre para lectura
            'producto', 'producto_info', # ID para escritura, Info para lectura
            'cantidad_solicitada_kg', 'cantidad_producida_kg',
            'fecha_creacion', 'fecha_compromiso_entrega', 'fecha_estimada_inicio',
            'fecha_real_inicio', 'fecha_real_terminacion', 'fecha_real_entrega',
            'sustrato', 'sustrato_nombre', # ID para escritura, Nombre para lectura
            'ancho_sustrato_mm', 'calibre_sustrato_um', 'tratamiento_sustrato', 'color_sustrato',
            'procesos', 'procesos_nombres', 'procesos_secuencia', 'etapa_actual', 'etapa_actual_display',
            'codigo_barras_op', 'observaciones_generales', 'observaciones_produccion',
            'is_active', 'actualizado_en', 'creado_por', 'actualizado_por',
        ]
        read_only_fields = (
            'id', 'fecha_creacion', 'actualizado_en', 'creado_por', 'actualizado_por',
            'cantidad_producida_kg', 'fecha_real_inicio', 'fecha_real_terminacion',
            'fecha_real_entrega', 'is_active',
            'cliente_nombre', 'producto_info', 'sustrato_nombre',
            'procesos_nombres', 'procesos_secuencia', 'etapa_actual_display',
        )

# =============================================
# === SERIALIZERS PARA IMPRESIÓN ===
# =============================================

class ConsumoImpresionSerializer(serializers.Serializer):
    """Valida datos para consumir sustrato en Impresión."""
    lote_sustrato_id = serializers.PrimaryKeyRelatedField(
        queryset=LoteMateriaPrima.objects.filter(estado='DISPONIBLE'),
        source='lote_consumido',
        required=True,
        help_text="ID Lote MP (sustrato) a consumir."
    )
    cantidad_kg = serializers.DecimalField(
        max_digits=12, decimal_places=3,
        required=True,
        min_value=Decimal('0.001'),
        help_text="Cantidad en Kg a consumir."
    )

    def __init__(self, *args, **kwargs):
        registro_impresion = kwargs.pop('registro_impresion', None)
        super().__init__(*args, **kwargs)
        if (registro_impresion):
            # Filtrar lotes por materia prima de la OP
            self.fields['lote_sustrato_id'].queryset = (
                self.fields['lote_sustrato_id'].queryset
                .filter(materia_prima=registro_impresion.orden_produccion.sustrato)
            )

class ProduccionImpresionSerializer(serializers.Serializer):
    """Valida datos para registrar producción WIP/PT desde Impresión."""
    lote_salida_id = serializers.CharField(max_length=100, required=True, help_text="ID único a asignar al nuevo Lote WIP/PT.")
    kg_producidos = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=Decimal('0.01'), help_text="Kg producidos para este rollo.")
    metros_producidos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0.0'), help_text="Metros (opcional).")
    ubicacion_destino_codigo = serializers.CharField(max_length=50, required=True, help_text="Código Ubicación destino (ej: BODEGA_WIP).")
    observaciones_lote = serializers.CharField(required=False, allow_blank=True, help_text="Observaciones (opcional).")

class RegistroImpresionSerializer(serializers.ModelSerializer):
    """Serializer CRUD para RegistroImpresion."""
    operario_principal_nombre = serializers.CharField(source='operario_principal.nombre_completo', read_only=True)
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    orden_produccion_numero = serializers.CharField(source='orden_produccion.op_numero', read_only=True)

    class Meta:
        model = RegistroImpresion
        fields = '__all__'
        read_only_fields = (
            'id', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',
            'produccion_registrada_en_inventario',
            'operario_principal_nombre', 'maquina_nombre', 'orden_produccion_numero',
        )

# =============================================
# === SERIALIZERS PARA REFILADO ===
# =============================================

class ConsumoWipRefiladoSerializer(serializers.Serializer):
    """Valida datos para consumir WIP en Refilado."""
    lote_entrada_id = serializers.PrimaryKeyRelatedField(
        queryset=LoteProductoEnProceso.objects.filter(estado='DISPONIBLE'),
        source='lote_consumido',
        required=True,
        help_text="ID Lote WIP (rollo impreso?) a consumir."
    )
    cantidad_kg = serializers.DecimalField(
        max_digits=12, decimal_places=3,
        required=True,
        min_value=Decimal('0.001'),
        help_text="Cantidad en Kg a consumir."
    )

    def __init__(self, *args, **kwargs):
        registro_refilado = kwargs.pop('registro_refilado', None)
        super().__init__(*args, **kwargs)
        if registro_refilado:
            # Filtrar lotes por OP
            self.fields['lote_entrada_id'].queryset = (
                self.fields['lote_entrada_id'].queryset
                .filter(orden_produccion=registro_refilado.orden_produccion)
            )

class ConsumoMpRefiladoSerializer(serializers.Serializer):
    """Valida datos para consumir MP (ej: core) en Refilado."""
    lote_mp_id = serializers.CharField(max_length=100, required=True, help_text="ID Lote MP (ej: core) a consumir.")
    cantidad_consumida = serializers.DecimalField(max_digits=12, decimal_places=3, required=True, min_value=Decimal('0.001'), help_text="Cantidad a consumir (en unidad del MP).")

class ProduccionRefiladoSerializer(serializers.Serializer):
    """Valida datos para registrar producción (rollo refilado WIP/PT) desde Refilado."""
    lote_salida_id = serializers.CharField(max_length=100, required=True, help_text="ID único a asignar al nuevo Lote.")
    kg_producidos = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=Decimal('0.01'), help_text="Kg producidos para este rollo.")
    metros_producidos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0.0'), help_text="Metros (opcional).")
    ubicacion_destino_codigo = serializers.CharField(max_length=50, required=True, help_text="Código Ubicación destino.")
    observaciones_lote = serializers.CharField(required=False, allow_blank=True, help_text="Observaciones (opcional).")

class RefiladoSerializer(serializers.ModelSerializer):
    """Serializer CRUD para Refilado."""
    operario_principal_nombre = serializers.CharField(source='operario_principal.nombre_completo', read_only=True)
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    orden_produccion_numero = serializers.CharField(source='orden_produccion.op_numero', read_only=True)

    class Meta:
        model = Refilado
        fields = '__all__'
        read_only_fields = ('id', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por', 'operario_principal_nombre', 'maquina_nombre', 'orden_produccion_numero',)

# =============================================
# === SERIALIZERS PARA SELLADO ===
# =============================================

class ConsumoWipSelladoSerializer(serializers.Serializer):
    """Valida datos para consumir WIP en Sellado."""
    lote_entrada_id = serializers.CharField(max_length=100, required=True, help_text="ID Lote WIP (rollo refilado?) a consumir.")
    cantidad_kg = serializers.DecimalField(max_digits=12, decimal_places=3, required=True, min_value=Decimal('0.001'), help_text="Cantidad en Kg a consumir.")

class ConsumoMpSelladoSerializer(serializers.Serializer):
    """Valida datos para consumir MP (ej: zipper) en Sellado."""
    lote_mp_id = serializers.CharField(max_length=100, required=True, help_text="ID Lote MP (ej: zipper) a consumir.")
    cantidad_consumida = serializers.DecimalField(max_digits=12, decimal_places=3, required=True, min_value=Decimal('0.001'), help_text="Cantidad a consumir (en unidad del MP).")

class ProduccionSelladoSerializer(serializers.Serializer):
    """Valida datos para registrar producción PT/WIP desde Sellado."""
    lote_salida_id = serializers.CharField(max_length=100, required=True, help_text="ID único a asignar a la nueva caja/paleta PT/WIP.")
    unidades_producidas = serializers.IntegerField(required=True, min_value=1, help_text="Unidades producidas para este lote.")
    ubicacion_destino_codigo = serializers.CharField(max_length=50, required=True, help_text="Código Ubicación destino (ej: BODEGA_PT).")
    observaciones_lote = serializers.CharField(required=False, allow_blank=True, help_text="Observaciones (opcional).")

class SelladoSerializer(serializers.ModelSerializer):
    """Serializer CRUD para Sellado."""
    operario_principal_nombre = serializers.CharField(source='operario_principal.nombre_completo', read_only=True)
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    orden_produccion_numero = serializers.CharField(source='orden_produccion.op_numero', read_only=True)

    class Meta:
        model = Sellado
        fields = '__all__'
        read_only_fields = ('id', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por', 'operario_principal_nombre', 'maquina_nombre', 'orden_produccion_numero',)

# =============================================
# === SERIALIZERS PARA DOBLADO ===
# =============================================

class ConsumoWipDobladoSerializer(serializers.Serializer):
    """Valida datos para consumir WIP en Doblado."""
    lote_entrada_id = serializers.CharField(max_length=100, required=True, help_text="ID Lote WIP (rollo impreso?) a consumir.")
    cantidad_kg = serializers.DecimalField(max_digits=12, decimal_places=3, required=True, min_value=Decimal('0.001'), help_text="Cantidad en Kg a consumir.")

class ConsumoMpDobladoSerializer(serializers.Serializer):
    """Valida datos para consumir MP en Doblado."""
    lote_mp_id = serializers.CharField(max_length=100, required=True, help_text="ID Lote MP a consumir.")
    cantidad_consumida = serializers.DecimalField(max_digits=12, decimal_places=3, required=True, min_value=Decimal('0.001'), help_text="Cantidad a consumir (en unidad del MP).")

class ProduccionDobladoSerializer(serializers.Serializer):
    """Valida datos para registrar producción WIP/PT desde Doblado."""
    lote_salida_id = serializers.CharField(max_length=100, required=True, help_text="ID único a asignar al nuevo Lote.")
    kg_producidos = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=Decimal('0.01'), help_text="Kg producidos para este rollo.")
    metros_producidos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0.0'), help_text="Metros (opcional).")
    ubicacion_destino_codigo = serializers.CharField(max_length=50, required=True, help_text="Código Ubicación destino.")
    observaciones_lote = serializers.CharField(required=False, allow_blank=True, help_text="Observaciones (opcional).")

class DobladoSerializer(serializers.ModelSerializer):
    """Serializer CRUD para Doblado."""
    operario_principal_nombre = serializers.CharField(source='operario_principal.nombre_completo', read_only=True)
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    orden_produccion_numero = serializers.CharField(source='orden_produccion.op_numero', read_only=True)

    class Meta:
        model = Doblado
        fields = '__all__'
        read_only_fields = ('id', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por', 'operario_principal_nombre', 'maquina_nombre', 'orden_produccion_numero',)