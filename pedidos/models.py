# pedidos/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.urls import reverse

# Importar modelos de otras apps
from clientes.models import Cliente
from productos.models import ProductoTerminado


class Pedido(models.Model):
    """Modelo principal para gestionar pedidos de clientes."""
    
    @classmethod
    def generar_numero_pedido(cls):
        """Genera un número de pedido único basado en el año actual y un contador secuencial."""
        año_actual = timezone.now().year
        ultimo_pedido = cls.objects.filter(numero_pedido__startswith=f'P-{año_actual}-').order_by('-numero_pedido').first()
        
        if ultimo_pedido:
            # Extraer el número secuencial del último pedido
            try:
                ultimo_numero = int(ultimo_pedido.numero_pedido.split('-')[-1])
                nuevo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1
            
        # Formatear el número con ceros a la izquierda (4 dígitos)
        return f'P-{año_actual}-{nuevo_numero:04d}'
    
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('CONFIRMADO', 'Confirmado'),
        ('EN_PRODUCCION', 'En Producción'),
        ('PRODUCIDO', 'Producido'),
        ('PENDIENTE_FACTURAR', 'Pendiente por Facturar'),
        ('FACTURADO', 'Facturado'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('NORMAL', 'Normal'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    # Información básica del pedido
    numero_pedido = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name="Número de Pedido",
        help_text="Número único del pedido"
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        related_name='pedidos',
        verbose_name="Cliente"
    )
    
    # Fechas importantes
    fecha_pedido = models.DateField(
        default=timezone.now,
        verbose_name="Fecha del Pedido"
    )
    fecha_compromiso = models.DateField(
        verbose_name="Fecha Compromiso de Entrega",
        help_text="Fecha comprometida con el cliente"
    )
    fecha_entrega_estimada = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha Entrega Estimada",
        help_text="Fecha estimada interna de entrega"
    )
    fecha_entrega_real = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha Entrega Real"
    )
    
    # Estado y control
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='BORRADOR',
        db_index=True,
        verbose_name="Estado del Pedido"
    )
    prioridad = models.CharField(
        max_length=10, choices=PRIORIDAD_CHOICES,
        default='NORMAL',
        verbose_name="Prioridad"
    )
    
    # Información comercial
    pedido_cliente_referencia = models.CharField(
        max_length=100, blank=True,
        verbose_name="Referencia del Cliente",
        help_text="Número de pedido o referencia del cliente"
    )
    condiciones_pago = models.CharField(
        max_length=100, blank=True,
        verbose_name="Condiciones de Pago"
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones"
    )
    
    # Totales (calculados)
    valor_total = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Valor Total"
    )
    
    # Información de facturación
    numero_factura = models.CharField(
        max_length=50, blank=True,
        verbose_name="Número de Factura"
    )
    fecha_facturacion = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha de Facturación"
    )
    
    # Auditoría
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='pedidos_creados',
        null=True, blank=True, editable=False
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='pedidos_actualizados',
        null=True, blank=True, editable=False
    )

    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.cliente.razon_social}"

    def get_absolute_url(self):
        return reverse('pedidos_web:pedido_detail', kwargs={'pk': self.pk})

    @property
    def tiene_orden_produccion(self):
        """Verifica si el pedido tiene al menos una orden de producción asociada."""
        return self.ordenes_produccion.exists()
    
    @property
    def ordenes_produccion_asociadas(self):
        """Retorna las órdenes de producción asociadas a este pedido."""
        return self.ordenes_produccion.all()
    
    @property
    def porcentaje_completado(self):
        """Calcula el porcentaje de completado basado en las líneas del pedido."""
        lineas = self.lineas.all()
        if not lineas:
            return 0
        
        total_cantidad = sum(linea.cantidad for linea in lineas)
        total_producido = sum(linea.cantidad_producida for linea in lineas)
        
        if total_cantidad == 0:
            return 0
        
        return round((total_producido / total_cantidad) * 100, 2)
    
    def calcular_total(self):
        """Calcula el valor total del pedido basado en sus líneas.
        
        Este método actualiza el campo valor_total del pedido y retorna el valor calculado.
        """
        # Usar aggregate para optimizar la consulta a la base de datos
        from django.db.models import Sum, F, ExpressionWrapper, DecimalField
        from django.db.models.functions import Coalesce
        
        # Calcular el subtotal de cada línea: (cantidad * precio_unitario) * (1 - descuento_porcentaje/100)
        resultado = self.lineas.aggregate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('cantidad') * F('precio_unitario') * (1 - F('descuento_porcentaje') / 100),
                        output_field=DecimalField()
                    )
                ),
                0
            )
        )
        
        total = resultado['total']
        
        # Actualizar el campo valor_total
        if self.valor_total != total:
            self.valor_total = total
            # Guardar solo si el objeto ya existe en la base de datos
            if self.pk:
                from django.db import transaction
                with transaction.atomic():
                    # Usar update para evitar triggers y señales
                    type(self).objects.filter(pk=self.pk).update(valor_total=total)
        
        return total

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido', '-numero_pedido']
        indexes = [
            models.Index(fields=['estado', 'fecha_compromiso']),
            models.Index(fields=['cliente', 'estado']),
        ]


class LineaPedido(models.Model):
    """Líneas de detalle de cada pedido."""
    
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='lineas',
        verbose_name="Pedido"
    )
    producto = models.ForeignKey(
        ProductoTerminado, on_delete=models.PROTECT,
        verbose_name="Producto"
    )
    
    # Cantidades
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name="Cantidad Solicitada"
    )
    cantidad_producida = models.DecimalField(
        max_digits=12, decimal_places=3,
        default=Decimal('0.000'),
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name="Cantidad Producida"
    )
    
    # Precios
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name="Precio Unitario"
    )
    descuento_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Descuento (%)"
    )
    
    # Especificaciones técnicas
    especificaciones_tecnicas = models.TextField(
        blank=True,
        verbose_name="Especificaciones Técnicas",
        help_text="Detalles técnicos específicos para esta línea"
    )
    
    # Fechas específicas de la línea
    fecha_entrega_requerida = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha Entrega Requerida",
        help_text="Fecha específica requerida para esta línea"
    )
    
    # Orden en el pedido
    orden_linea = models.PositiveIntegerField(
        default=1,
        verbose_name="Orden en Pedido"
    )

    @property
    def subtotal_bruto(self):
        """Calcula el subtotal bruto (sin descuento)."""
        return self.cantidad * self.precio_unitario
    
    @property
    def valor_descuento(self):
        """Calcula el valor del descuento."""
        return (self.subtotal_bruto * self.descuento_porcentaje) / 100
    
    @property
    def subtotal(self):
        """Calcula el subtotal neto (con descuento aplicado)."""
        return self.subtotal_bruto - self.valor_descuento
    
    @property
    def porcentaje_completado(self):
        """Calcula el porcentaje de completado de esta línea."""
        if self.cantidad == 0:
            return 0
        return round((self.cantidad_producida / self.cantidad) * 100, 2)
    
    @property
    def ordenes_produccion_asociadas(self):
        """Retorna las órdenes de producción asociadas a esta línea específica."""
        # Importar aquí para evitar importación circular
        from produccion.models import OrdenProduccion
        return OrdenProduccion.objects.filter(
            pedido=self.pedido,
            producto=self.producto
        )

    def __str__(self):
        return f"{self.pedido.numero_pedido} - {self.producto.codigo} ({self.cantidad})"

    class Meta:
        verbose_name = "Línea de Pedido"
        verbose_name_plural = "Líneas de Pedido"
        ordering = ['pedido', 'orden_linea']
        unique_together = ('pedido', 'producto', 'orden_linea')


class SeguimientoPedido(models.Model):
    """Modelo para registrar el seguimiento y cambios de estado de pedidos."""
    
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='seguimientos',
        verbose_name="Pedido"
    )
    estado_anterior = models.CharField(
        max_length=20, choices=Pedido.ESTADO_CHOICES,
        null=True, blank=True,
        verbose_name="Estado Anterior"
    )
    estado_nuevo = models.CharField(
        max_length=20, choices=Pedido.ESTADO_CHOICES,
        verbose_name="Estado Nuevo"
    )
    fecha_cambio = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha del Cambio"
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones del Cambio"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Usuario que realizó el cambio"
    )

    def __str__(self):
        return f"{self.pedido.numero_pedido} - {self.estado_anterior} → {self.estado_nuevo}"

    class Meta:
        verbose_name = "Seguimiento de Pedido"
        verbose_name_plural = "Seguimientos de Pedidos"
        ordering = ['-fecha_cambio']