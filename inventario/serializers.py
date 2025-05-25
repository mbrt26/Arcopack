# inventario/serializers.py

from rest_framework import serializers
from decimal import Decimal

# Importar modelos de esta app
from .models import MateriaPrima, Tinta
# Importar modelos relacionados si se usan para representación anidada
# from configuracion.models import CategoriaMateriaPrima, UnidadMedida, TipoTinta

class StockItemSerializer(serializers.Serializer):
    """Serializer para mostrar stock agregado."""
    tipo_item = serializers.CharField(read_only=True)
    # --- Usar source='agg_...' ---
    item_id = serializers.IntegerField(read_only=True, source='agg_item_id')
    item_codigo = serializers.CharField(read_only=True, source='agg_item_codigo')
    item_nombre = serializers.CharField(read_only=True, source='agg_item_nombre')
    ubicacion_id = serializers.IntegerField(read_only=True, source='agg_ubicacion_id')
    ubicacion_codigo = serializers.CharField(read_only=True, source='agg_ubicacion_codigo')
    ubicacion_nombre = serializers.CharField(read_only=True, source='agg_ubicacion_nombre')
    unidad_medida_codigo = serializers.CharField(read_only=True, source='agg_unidad_medida_codigo')
    # --- Campos calculados (ya tienen nombres únicos) ---
    cantidad_total = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    numero_lotes = serializers.IntegerField(read_only=True)

# =============================================
# === SERIALIZER PARA MATERIA PRIMA ===
# =============================================
class MateriaPrimaSerializer(serializers.ModelSerializer):
    """Serializer CRUD básico para Materia Prima."""
    # Campos de solo lectura para mostrar nombres/códigos relacionados
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    unidad_medida_codigo = serializers.CharField(source='unidad_medida.codigo', read_only=True)
    proveedor_preferido_nombre = serializers.CharField(source='proveedor_preferido.razon_social', read_only=True, allow_null=True)

    class Meta:
        model = MateriaPrima
        # Listar campos explícitamente
        fields = [
            'id', 'url', # DRF puede añadir 'url' con routers
            'codigo', 'nombre', 'descripcion', 'categoria', 'categoria_nombre',
            'unidad_medida', 'unidad_medida_codigo', 'proveedor_preferido',
            'proveedor_preferido_nombre', 'stock_minimo', 'stock_maximo',
            'tiempo_entrega_std_dias', 'requiere_lote', 'is_active',
            'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',
        ]
        read_only_fields = (
            'id', 'url', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',
            'categoria_nombre', 'unidad_medida_codigo', 'proveedor_preferido_nombre',
        )

# =============================================
# === SERIALIZER PARA TINTA ===
# =============================================
class TintaSerializer(serializers.ModelSerializer):
    """Serializer CRUD básico para Tinta."""
    tipo_tinta_nombre = serializers.CharField(source='tipo_tinta.nombre', read_only=True)
    unidad_medida_codigo = serializers.CharField(source='unidad_medida.codigo', read_only=True)

    class Meta:
        model = Tinta
        fields = [
            'id', 'url',
            'codigo', 'nombre', 'tipo_tinta', 'tipo_tinta_nombre', 'color_exacto',
            'fabricante', 'referencia_fabricante', 'unidad_medida',
            'unidad_medida_codigo', 'requiere_lote', 'is_active',
            'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',
        ]
        read_only_fields = (
            'id', 'url', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',
            'tipo_tinta_nombre', 'unidad_medida_codigo',
        )

# =============================================
# === SERIALIZER PARA CONSULTA DE STOCK ===
# =============================================
class StockItemSerializer(serializers.Serializer):
    """
    Serializer para mostrar el stock agregado de un item en una ubicación.
    Es de solo lectura ya que representa un resultado calculado.
    """
    tipo_item = serializers.CharField(read_only=True, help_text="MP, WIP, o PT")
    item_id = serializers.IntegerField(read_only=True, help_text="ID de MateriaPrima o ProductoTerminado")
    item_codigo = serializers.CharField(read_only=True, help_text="Código de MateriaPrima o ProductoTerminado")
    item_nombre = serializers.CharField(read_only=True, help_text="Nombre de MateriaPrima o ProductoTerminado")
    ubicacion_id = serializers.IntegerField(read_only=True, help_text="ID de la Ubicación")
    ubicacion_codigo = serializers.CharField(read_only=True, help_text="Código de la Ubicación")
    ubicacion_nombre = serializers.CharField(read_only=True, help_text="Nombre de la Ubicación")
    unidad_medida_codigo = serializers.CharField(read_only=True, help_text="Unidad de Medida del stock")
    cantidad_total = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True, help_text="Stock total actual del item en la ubicación")
    numero_lotes = serializers.IntegerField(read_only=True, help_text="Número de lotes distintos que componen el stock")


# Nota: No solemos necesitar serializers para Lote* o Movimiento* a menos que
# vayamos a exponer endpoints CRUD directos para ellos, lo cual no es común.
# Se gestionan a través de las acciones (Recepcion, Consumo, Produccion, Ajuste...).