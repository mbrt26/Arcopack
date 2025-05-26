# pedidos/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Pedido, LineaPedido, SeguimientoPedido
from clientes.models import Cliente
from productos.models import ProductoTerminado


class ClienteBasicSerializer(serializers.ModelSerializer):
    """Serializer básico para cliente en pedidos"""
    class Meta:
        model = Cliente
        fields = ['id', 'razon_social', 'nit', 'email']


class ProductoBasicSerializer(serializers.ModelSerializer):
    """Serializer básico para producto en líneas de pedido"""
    class Meta:
        model = ProductoTerminado
        fields = ['id', 'codigo', 'nombre', 'precio_venta', 'unidad_medida']


class LineaPedidoSerializer(serializers.ModelSerializer):
    """Serializer para líneas de pedido"""
    producto = ProductoBasicSerializer(read_only=True)
    producto_id = serializers.IntegerField(write_only=True)
    subtotal = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    porcentaje_completado = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = LineaPedido
        fields = [
            'id', 'orden_linea', 'producto', 'producto_id', 'cantidad', 
            'precio_unitario', 'descuento_porcentaje', 'subtotal', 
            'cantidad_producida', 'porcentaje_completado', 
            'fecha_entrega_requerida', 'especificaciones_tecnicas'
        ]

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value

    def validate_precio_unitario(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio unitario no puede ser negativo")
        return value

    def validate_descuento_porcentaje(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("El descuento debe estar entre 0% y 100%")
        return value


class SeguimientoPedidoSerializer(serializers.ModelSerializer):
    """Serializer para seguimiento de pedidos"""
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    
    class Meta:
        model = SeguimientoPedido
        fields = [
            'id', 'fecha_cambio', 'estado_anterior', 'estado_nuevo',
            'usuario_nombre', 'observaciones'
        ]


class PedidoListSerializer(serializers.ModelSerializer):
    """Serializer para listado de pedidos"""
    cliente = ClienteBasicSerializer(read_only=True)
    total_lineas = serializers.IntegerField(read_only=True)
    porcentaje_completado = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    tiene_orden_produccion = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Pedido
        fields = [
            'id', 'numero_pedido', 'cliente', 'estado', 'prioridad',
            'fecha_pedido', 'fecha_compromiso', 'valor_total',
            'total_lineas', 'porcentaje_completado', 'tiene_orden_produccion',
            'creado_en', 'actualizado_en'
        ]


class PedidoDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para pedidos"""
    cliente = ClienteBasicSerializer(read_only=True)
    cliente_id = serializers.IntegerField(write_only=True)
    lineas = LineaPedidoSerializer(many=True, read_only=True)
    seguimientos = SeguimientoPedidoSerializer(many=True, read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.username', read_only=True)
    actualizado_por_nombre = serializers.CharField(source='actualizado_por.username', read_only=True)
    porcentaje_completado = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    tiene_orden_produccion = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Pedido
        fields = [
            'id', 'numero_pedido', 'cliente', 'cliente_id', 'estado', 'prioridad',
            'fecha_pedido', 'fecha_compromiso', 'fecha_entrega_estimada', 'fecha_entrega_real',
            'pedido_cliente_referencia', 'condiciones_pago', 'observaciones',
            'numero_factura', 'fecha_facturacion', 'valor_total',
            'lineas', 'seguimientos', 'porcentaje_completado', 'tiene_orden_produccion',
            'creado_en', 'actualizado_en', 'creado_por_nombre', 'actualizado_por_nombre'
        ]
        read_only_fields = ['numero_pedido', 'valor_total', 'creado_en', 'actualizado_en']

    def validate(self, data):
        # Validar fechas
        fecha_pedido = data.get('fecha_pedido')
        fecha_compromiso = data.get('fecha_compromiso')
        
        if fecha_pedido and fecha_compromiso and fecha_compromiso < fecha_pedido:
            raise serializers.ValidationError({
                'fecha_compromiso': 'La fecha de compromiso no puede ser anterior a la fecha del pedido'
            })
        
        # Validar estado vs campos de facturación
        estado = data.get('estado')
        numero_factura = data.get('numero_factura')
        fecha_facturacion = data.get('fecha_facturacion')
        
        if estado == 'FACTURADO':
            if not numero_factura:
                raise serializers.ValidationError({
                    'numero_factura': 'El número de factura es requerido para el estado "Facturado"'
                })
            if not fecha_facturacion:
                raise serializers.ValidationError({
                    'fecha_facturacion': 'La fecha de facturación es requerida para el estado "Facturado"'
                })
        
        return data


class PedidoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear pedidos con líneas"""
    cliente_id = serializers.IntegerField()
    lineas = LineaPedidoSerializer(many=True, write_only=True)
    
    class Meta:
        model = Pedido
        fields = [
            'cliente_id', 'fecha_pedido', 'fecha_compromiso', 'prioridad',
            'pedido_cliente_referencia', 'condiciones_pago', 'observaciones',
            'lineas'
        ]

    def validate_lineas(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos una línea en el pedido")
        return value

    def create(self, validated_data):
        lineas_data = validated_data.pop('lineas')
        pedido = Pedido.objects.create(**validated_data)
        
        for linea_data in lineas_data:
            LineaPedido.objects.create(pedido=pedido, **linea_data)
        
        # Calcular total
        pedido.calcular_total()
        pedido.save()
        
        return pedido


class CambiarEstadoPedidoSerializer(serializers.Serializer):
    """Serializer para cambiar estado de pedidos"""
    nuevo_estado = serializers.ChoiceField(choices=Pedido.ESTADO_CHOICES)
    numero_factura = serializers.CharField(max_length=50, required=False, allow_blank=True)
    fecha_facturacion = serializers.DateField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        nuevo_estado = data.get('nuevo_estado')
        numero_factura = data.get('numero_factura')
        fecha_facturacion = data.get('fecha_facturacion')

        if nuevo_estado == 'FACTURADO':
            if not numero_factura:
                raise serializers.ValidationError({
                    'numero_factura': 'El número de factura es requerido para el estado "Facturado"'
                })
            if not fecha_facturacion:
                raise serializers.ValidationError({
                    'fecha_facturacion': 'La fecha de facturación es requerida para el estado "Facturado"'
                })

        return data


class EstadisticasPedidosSerializer(serializers.Serializer):
    """Serializer para estadísticas de pedidos"""
    total_pedidos = serializers.IntegerField()
    valor_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    promedio_por_pedido = serializers.DecimalField(max_digits=15, decimal_places=2)
    pedidos_por_estado = serializers.DictField()
    pedidos_por_prioridad = serializers.DictField()
    clientes_top = serializers.ListField()
    productos_mas_pedidos = serializers.ListField()


class ResumenPedidoSerializer(serializers.Serializer):
    """Serializer para resumen ejecutivo de pedidos"""
    periodo = serializers.CharField()
    total_pedidos = serializers.IntegerField()
    valor_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    pedidos_confirmados = serializers.IntegerField()
    pedidos_en_produccion = serializers.IntegerField()
    pedidos_pendientes_facturar = serializers.IntegerField()
    pedidos_facturados = serializers.IntegerField()
    crecimiento_porcentual = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)