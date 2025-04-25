# inventario/models.py

import logging
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model # <<< ¡ASEGÚRATE QUE ESTA LÍNEA ESTÉ AQUÍ!

# --- Importar modelos de OTRAS apps ---
from configuracion.models import UnidadMedida, Ubicacion, Proveedor, CategoriaMateriaPrima, TipoTinta
# from productos.models import ProductoTerminado
# from produccion.models import OrdenProduccion

User = get_user_model() # Ahora funcionará
logger = logging.getLogger(__name__)

# =============================================
# === MODELOS MAESTROS DE ITEMS ===
# =============================================

class MateriaPrima(models.Model):
    """Maestro de Materias Primas."""
    codigo = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Código MP", help_text="Código único de la materia prima.")
    nombre = models.CharField(max_length=150, verbose_name="Nombre MP")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    categoria = models.ForeignKey(CategoriaMateriaPrima, on_delete=models.PROTECT, verbose_name="Categoría")
    unidad_medida = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, verbose_name="Unidad de Medida Inventario")
    proveedor_preferido = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Proveedor Preferido")
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Stock Mínimo")
    stock_maximo = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Stock Máximo")
    tiempo_entrega_std_dias = models.PositiveIntegerField(default=0, verbose_name="Lead Time Estándar (días)")
    requiere_lote = models.BooleanField(default=True, verbose_name="¿Requiere Lote?", help_text="Indica si el inventario se maneja por lotes específicos.")
    is_active = models.BooleanField(default=True, verbose_name="Activo", db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    def __str__(self): return f"{self.codigo} - {self.nombre}"
    class Meta: verbose_name = "Materia Prima"; verbose_name_plural = "Materias Primas"; ordering = ['codigo']

class Tinta(models.Model):
    """Catálogo de Tintas específicas."""
    codigo = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Código Tinta", help_text="Código único de la tinta.")
    nombre = models.CharField(max_length=150, verbose_name="Nombre Descriptivo")
    tipo_tinta = models.ForeignKey(TipoTinta, on_delete=models.PROTECT, verbose_name="Tipo de Tinta")
    color_exacto = models.CharField(max_length=50, blank=True, verbose_name="Color / Pantone")
    fabricante = models.CharField(max_length=100, blank=True)
    referencia_fabricante = models.CharField(max_length=100, blank=True)
    unidad_medida = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, verbose_name="Unidad de Medida")
    requiere_lote = models.BooleanField(default=True, verbose_name="¿Requiere Lote?", help_text="Indica si el inventario se maneja por lotes específicos.")
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    def __str__(self): return f"{self.codigo} - {self.nombre} ({self.tipo_tinta.nombre})"
    class Meta: verbose_name = "Tinta"; verbose_name_plural = "Tintas"; ordering = ['codigo']

# =============================================
# === MODELO BASE ABSTRACTO PARA LOTES ===
# =============================================

class LoteBase(models.Model):
    """Clase base abstracta para Lotes de inventario (MP, WIP, PT)."""
    ESTADO_LOTE_CHOICES = [
        ('DISPONIBLE', 'Disponible'), ('CUARENTENA', 'En Cuarentena'), ('BLOQUEADO', 'Bloqueado'),
        ('CONSUMIDO', 'Consumido'), ('DESPACHADO', 'Despachado'), ('DESECHADO', 'Desechado/Scrap'),
    ]
    lote_id = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="ID Lote/Rollo/Paleta")
    cantidad_actual = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Cantidad Actual")
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, verbose_name="Ubicación Actual")
    estado = models.CharField(max_length=20, choices=ESTADO_LOTE_CHOICES, default='DISPONIBLE', verbose_name="Estado Lote", db_index=True)
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    creado_en = models.DateTimeField(auto_now_add=True, editable=False); actualizado_en = models.DateTimeField(auto_now=True, editable=False)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='%(class)s_creados', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='%(class)s_actualizados', on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    @property
    def unidad_medida_lote(self): raise NotImplementedError("Subclases deben implementar unidad_medida_lote.")
    @property
    def item_principal(self): raise NotImplementedError("Subclases deben implementar item_principal.")

    # --- Método Save Modificado ---
    def save(self, *args, **kwargs):
        """
        Sobrescribe save para asignar auditoría y registrar movimiento inicial
        al CREAR un nuevo lote con cantidad > 0.
        Requiere que 'user' se pase en kwargs al crear desde fuera del admin.
        """
        is_new = self.pk is None
        user = kwargs.pop('user', None)

        # Asignar auditoría si se pasa el usuario
        if user and user.is_authenticated:
             if is_new and hasattr(self, 'creado_por'): self.creado_por = user
             if hasattr(self, 'actualizado_por'): self.actualizado_por = user

        # Guardar el lote PRIMERO para obtener un PK
        super().save(*args, **kwargs)

        # Si es un lote NUEVO, tiene cantidad y podemos determinar el tipo/proceso,
        # registrar el movimiento de PRODUCCION o RECEPCION inicial.
        if is_new and self.cantidad_actual > 0:
            tipo_mov = None
            proceso_ref = None
            doc_ref = None # Documento de referencia (ej: recepción)
            usuario_accion = user or getattr(self, 'creado_por', None)

            if isinstance(self, LoteProductoEnProceso):
                tipo_mov = 'PRODUCCION_WIP'
                proceso_ref = getattr(self, 'proceso_origen_content_object', None) # Acceder GFK después de guardar
            elif isinstance(self, LoteProductoTerminado):
                tipo_mov = 'PRODUCCION_PT'
                proceso_ref = getattr(self, 'proceso_final_content_object', None)
            elif isinstance(self, LoteMateriaPrima):
                tipo_mov = 'RECEPCION_MP'
                # Usar el documento de recepción si existe
                doc_ref = getattr(self, 'documento_recepcion', None)

            if tipo_mov and usuario_accion:
                try:
                    self.registrar_movimiento(
                        tipo_movimiento=tipo_mov,
                        cantidad=self.cantidad_actual, # Cantidad inicial
                        usuario=usuario_accion,
                        ubicacion_destino=self.ubicacion, # Entra a su ubicación inicial
                        proceso_referencia=proceso_ref, # Referencia al proceso si aplica
                        documento_referencia=doc_ref, # Referencia al doc si aplica
                        observaciones=f"Movimiento automático creación Lote {self.lote_id}"
                    )
                except Exception as e:
                    logger.error(f"Error registrando movimiento automático para Lote {self.lote_id} ({tipo_mov}): {e}")
                    # Considerar si relanzar el error para deshacer la transacción
                    # raise e
            elif not usuario_accion:
                 logger.error(f"No se pudo registrar movimiento automático para Lote {self.lote_id} por falta de usuario.")

    # --- Otros Métodos Helper ---
    def registrar_movimiento(self, tipo_movimiento, cantidad, usuario, **kwargs):
        # ... (Código de registrar_movimiento como estaba antes) ...
        if not usuario or not usuario.is_authenticated: raise ValueError("Usuario autenticado requerido.")
        if tipo_movimiento in MovimientoInventario.TIPOS_SALIDA and cantidad > 0: cantidad = -abs(cantidad)
        elif tipo_movimiento in MovimientoInventario.TIPOS_ENTRADA and cantidad < 0: cantidad = abs(cantidad)
        mov = MovimientoInventario(
            tipo_movimiento=tipo_movimiento, lote_content_object=self, cantidad=cantidad,
            unidad_medida=self.unidad_medida_lote, usuario=usuario,
            ubicacion_origen=kwargs.get('ubicacion_origen'),
            ubicacion_destino=kwargs.get('ubicacion_destino', self.ubicacion),
            documento_referencia=kwargs.get('documento_referencia'),
            proceso_referencia_content_object=kwargs.get('proceso_referencia'),
            observaciones=kwargs.get('observaciones', f"Movimiento: {tipo_movimiento}")
        )
        mov.save()
        return mov

    def ajustar_stock(self, cantidad_ajuste, tipo_ajuste, usuario, **kwargs):
        # ... (Código de ajustar_stock como estaba antes) ...
        if tipo_ajuste not in ['AJUSTE_POSITIVO', 'AJUSTE_NEGATIVO']: raise ValueError("Tipo de ajuste inválido.")
        if not usuario or not usuario.is_authenticated: raise ValueError("Usuario autenticado requerido.")
        nueva_cantidad = self.cantidad_actual + cantidad_ajuste
        if nueva_cantidad < 0: raise ValidationError(f"Ajuste resultaría en stock negativo para lote {self.lote_id}.")
        self.cantidad_actual = nueva_cantidad; self.actualizado_por = usuario
        self.save(update_fields=['cantidad_actual', 'actualizado_en', 'actualizado_por'])
        self.registrar_movimiento(tipo_ajuste, cantidad_ajuste, usuario=usuario, **kwargs)
        logger.info(f"Stock Lote {self.lote_id} ajustado a {self.cantidad_actual}.")
        return True

    def transferir(self, nueva_ubicacion, usuario, **kwargs):
        # ... (Código de transferir como estaba antes) ...
        if not usuario or not usuario.is_authenticated: raise ValueError("Usuario autenticado requerido.")
        if self.cantidad_actual <= 0 and self.estado != 'CONSUMIDO': raise ValidationError(f"Lote {self.lote_id} sin stock positivo para transferir.")
        if not isinstance(nueva_ubicacion, Ubicacion): raise TypeError("nueva_ubicacion debe ser una instancia de Ubicacion.")
        if self.ubicacion == nueva_ubicacion: raise ValidationError("Ubicación origen y destino son la misma.")
        ubicacion_anterior = self.ubicacion; self.ubicacion = nueva_ubicacion; self.actualizado_por = usuario
        self.save(update_fields=['ubicacion', 'actualizado_en', 'actualizado_por'])
        self.registrar_movimiento('TRANSFERENCIA_SALIDA', self.cantidad_actual, usuario=usuario, ubicacion_origen=ubicacion_anterior, ubicacion_destino=nueva_ubicacion, **kwargs)
        self.registrar_movimiento('TRANSFERENCIA_ENTRADA', self.cantidad_actual, usuario=usuario, ubicacion_origen=ubicacion_anterior, ubicacion_destino=nueva_ubicacion, **kwargs)
        logger.info(f"Lote {self.lote_id} transferido de {ubicacion_anterior} a {nueva_ubicacion}.")
        return True

    class Meta: abstract = True; ordering = ['-creado_en', 'lote_id']

# =============================================
# === MODELOS DE LOTES ESPECÍFICOS ===
# =============================================

class LoteMateriaPrima(LoteBase):
    """Lote específico de Materia Prima."""
    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.PROTECT, related_name='lotes')
    cantidad_recibida = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Cantidad Recibida")
    fecha_recepcion = models.DateTimeField(default=timezone.now, verbose_name="Fecha Recepción")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha Vencimiento")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, verbose_name="Proveedor")
    documento_recepcion = models.CharField(max_length=100, blank=True, verbose_name="Documento Recepción")
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Costo Unitario Lote")

    @property
    def unidad_medida_lote(self): return self.materia_prima.unidad_medida
    @property
    def item_principal(self): return self.materia_prima

    def consumir(self, cantidad_consumir, proceso_ref, usuario, **kwargs):
        if not usuario or not usuario.is_authenticated: raise ValueError("Usuario requerido.")
        if cantidad_consumir <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
        if self.cantidad_actual < cantidad_consumir: raise ValidationError(f"Stock insuficiente en lote MP {self.lote_id}. Disp: {self.cantidad_actual}, Req: {cantidad_consumir}")
        if self.estado != 'DISPONIBLE': raise ValidationError(f"Lote MP {self.lote_id} no disponible (Estado: {self.estado})")
        self.cantidad_actual -= cantidad_consumir
        nuevo_estado = self.estado
        umbral_cero = Decimal('0.0001') # Umbral para considerar cero por decimales
        if self.cantidad_actual <= umbral_cero: nuevo_estado = 'CONSUMIDO'; self.cantidad_actual = Decimal('0.0')
        self.estado = nuevo_estado; self.actualizado_por = usuario
        # Pasar kwargs al registrar movimiento
        obs = kwargs.pop('observaciones', f"Consumo para Proceso Ref {getattr(proceso_ref, 'id', 'N/A')}")
        self.save(update_fields=['cantidad_actual', 'estado', 'actualizado_en', 'actualizado_por'])
        self.registrar_movimiento('CONSUMO_MP', cantidad_consumir, usuario=usuario, proceso_referencia=proceso_ref, observaciones=obs, **kwargs)
        logger.info(f"Consumidos {cantidad_consumir} {self.unidad_medida_lote.codigo} de Lote MP {self.lote_id}. Restante: {self.cantidad_actual}.")
        return True

    def __str__(self): return f"Lote MP: {self.lote_id} ({self.materia_prima.codigo}) - Disp: {self.cantidad_actual} {self.unidad_medida_lote.codigo}"
    class Meta(LoteBase.Meta): verbose_name = "Lote Materia Prima"; verbose_name_plural = "Lotes Materia Prima"

class LoteProductoEnProceso(LoteBase):
    """Lote/Rollo de Producto en Proceso (WIP)."""
    producto_terminado = models.ForeignKey('productos.ProductoTerminado', on_delete=models.PROTECT, related_name='lotes_wip')
    orden_produccion = models.ForeignKey('produccion.OrdenProduccion', on_delete=models.PROTECT, related_name='lotes_wip_producidos')
    proceso_origen_content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name='+')
    proceso_origen_object_id = models.PositiveIntegerField()
    proceso_origen = GenericForeignKey('proceso_origen_content_type', 'proceso_origen_object_id')
    cantidad_producida_primaria = models.DecimalField(max_digits=14, decimal_places=4, verbose_name="Cant. Producida (Unidad Primaria)")
    unidad_medida_primaria = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, related_name='+') # Unidad de cantidad_actual y _primaria
    cantidad_producida_secundaria = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, verbose_name="Cant. Producida (Unidad Secundaria)")
    unidad_medida_secundaria = models.ForeignKey(UnidadMedida, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    fecha_produccion = models.DateTimeField(default=timezone.now, verbose_name="Fecha Producción")

    @property
    def unidad_medida_lote(self): return self.unidad_medida_primaria
    @property
    def item_principal(self): return self.producto_terminado

    def consumir(self, cantidad_consumir, proceso_ref, usuario, **kwargs):
        # Lógica similar a LoteMateriaPrima.consumir, registra CONSUMO_WIP
        if not usuario or not usuario.is_authenticated: raise ValueError("Usuario requerido.")
        if cantidad_consumir <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
        if self.cantidad_actual < cantidad_consumir: raise ValidationError(f"Stock insuficiente en lote WIP {self.lote_id}. Disp: {self.cantidad_actual}, Req: {cantidad_consumir}")
        if self.estado != 'DISPONIBLE': raise ValidationError(f"Lote WIP {self.lote_id} no disponible (Estado: {self.estado})")
        self.cantidad_actual -= cantidad_consumir
        nuevo_estado = self.estado
        umbral_cero = Decimal('0.0001')
        if self.cantidad_actual <= umbral_cero: nuevo_estado = 'CONSUMIDO'; self.cantidad_actual = Decimal('0.0')
        self.estado = nuevo_estado; self.actualizado_por = usuario
        obs = kwargs.pop('observaciones', f"Consumo para Proceso Ref {getattr(proceso_ref, 'id', 'N/A')}")
        self.save(update_fields=['cantidad_actual', 'estado', 'actualizado_en', 'actualizado_por'])
        self.registrar_movimiento('CONSUMO_WIP', cantidad_consumir, usuario=usuario, proceso_referencia=proceso_ref, observaciones=obs, **kwargs)
        logger.info(f"Consumidos {cantidad_consumir} {self.unidad_medida_lote.codigo} de Lote WIP {self.lote_id}. Restante: {self.cantidad_actual}.")
        return True

    def __str__(self):
        prod_codigo = getattr(self.producto_terminado, 'codigo', 'N/A')
        unidad_str = getattr(self.unidad_medida_lote, 'codigo', 'N/A')
        return f"Lote WIP: {self.lote_id} ({prod_codigo}) - Disp: {self.cantidad_actual} {unidad_str}"
    class Meta(LoteBase.Meta): verbose_name = "Lote Producto en Proceso"; verbose_name_plural = "Lotes Producto en Proceso"

class LoteProductoTerminado(LoteBase):
    """Lote/Paleta/Caja de Producto Terminado."""
    producto_terminado = models.ForeignKey('productos.ProductoTerminado', on_delete=models.PROTECT, related_name='lotes_pt')
    orden_produccion = models.ForeignKey('produccion.OrdenProduccion', on_delete=models.PROTECT, related_name='lotes_pt_producidos')
    proceso_final_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    proceso_final_object_id = models.PositiveIntegerField(null=True, blank=True)
    proceso_final = GenericForeignKey('proceso_final_content_type', 'proceso_final_object_id')
    cantidad_producida = models.DecimalField(max_digits=14, decimal_places=4, verbose_name="Cantidad Producida") # Unidad de producto.unidad_medida
    fecha_produccion = models.DateTimeField(default=timezone.now, verbose_name="Fecha Producción")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha Vencimiento")

    @property
    def unidad_medida_lote(self): return self.producto_terminado.unidad_medida
    @property
    def item_principal(self): return self.producto_terminado

    def despachar(self, cantidad_despachar, documento_salida, usuario, **kwargs):
        """Despacha cantidad de este lote PT."""
        if not usuario or not usuario.is_authenticated: raise ValueError("Usuario requerido.")
        if cantidad_despachar <= 0: raise ValueError("Cantidad a despachar debe ser positiva.")
        if self.cantidad_actual < cantidad_despachar: raise ValidationError(f"Stock insuficiente en lote PT {self.lote_id}. Disp: {self.cantidad_actual}, Req: {cantidad_despachar}")
        if self.estado != 'DISPONIBLE': raise ValidationError(f"Lote PT {self.lote_id} no disponible (Estado: {self.estado})")
        self.cantidad_actual -= cantidad_despachar
        nuevo_estado = self.estado
        umbral_cero = Decimal('0.0001')
        if self.cantidad_actual <= umbral_cero: nuevo_estado = 'DESPACHADO'; self.cantidad_actual = Decimal('0.0')
        self.estado = nuevo_estado; self.actualizado_por = usuario
        obs = kwargs.pop('observaciones', f"Despacho Doc: {documento_salida}")
        self.save(update_fields=['cantidad_actual', 'estado', 'actualizado_en', 'actualizado_por'])
        self.registrar_movimiento('ENVIO_PT', cantidad_despachar, usuario=usuario, documento_referencia=documento_salida, observaciones=obs, **kwargs)
        logger.info(f"Despachados {cantidad_despachar} {self.unidad_medida_lote.codigo} de Lote PT {self.lote_id}. Restante: {self.cantidad_actual}.")
        return True

    def __str__(self):
        prod_codigo = getattr(self.producto_terminado, 'codigo', 'N/A')
        unidad_str = getattr(self.unidad_medida_lote, 'codigo', 'N/A')
        return f"Lote PT: {self.lote_id} ({prod_codigo}) - Disp: {self.cantidad_actual} {unidad_str}"
    class Meta(LoteBase.Meta): verbose_name = "Lote Producto Terminado"; verbose_name_plural = "Lotes Producto Terminado"

# =============================================
# === MODELO DE MOVIMIENTOS DE INVENTARIO ===
# =============================================

class MovimientoInventario(models.Model):
    """Log de todas las transacciones de inventario."""
    TIPOS_ENTRADA = ['RECEPCION_MP', 'PRODUCCION_WIP', 'PRODUCCION_PT', 'AJUSTE_POSITIVO', 'TRANSFERENCIA_ENTRADA', 'QA_RELEASE', 'DEVOLUCION_CLIENTE']
    TIPOS_SALIDA = ['CONSUMO_MP', 'CONSUMO_WIP', 'ENVIO_PT', 'AJUSTE_NEGATIVO', 'TRANSFERENCIA_SALIDA', 'QA_HOLD', 'DESECHO_SCRAP', 'DEVOLUCION_PROVEEDOR']
    TIPO_MOVIMIENTO_CHOICES = [
        ('RECEPCION_MP', 'Recepción Materia Prima'), ('PRODUCCION_WIP', 'Producción Producto en Proceso'), ('PRODUCCION_PT', 'Producción Producto Terminado'),
        ('AJUSTE_POSITIVO', 'Ajuste Positivo'), ('TRANSFERENCIA_ENTRADA', 'Entrada por Transferencia'), ('QA_RELEASE', 'Liberación de Calidad'), ('DEVOLUCION_CLIENTE', 'Devolución de Cliente'),
        ('CONSUMO_MP', 'Consumo Materia Prima'), ('CONSUMO_WIP', 'Consumo Producto en Proceso'), ('ENVIO_PT', 'Envío Producto Terminado'),
        ('AJUSTE_NEGATIVO', 'Ajuste Negativo'), ('TRANSFERENCIA_SALIDA', 'Salida por Transferencia'), ('QA_HOLD', 'Bloqueo por Calidad'),
        ('DESECHO_SCRAP', 'Desecho / Scrap'), ('DEVOLUCION_PROVEEDOR', 'Devolución a Proveedor'),
    ]

    timestamp = models.DateTimeField(default=timezone.now, editable=False, db_index=True, verbose_name="Fecha y Hora")
    tipo_movimiento = models.CharField(max_length=30, choices=TIPO_MOVIMIENTO_CHOICES, verbose_name="Tipo Movimiento")
    lote_content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name='+')
    lote_object_id = models.PositiveIntegerField(db_index=True)
    lote_content_object = GenericForeignKey('lote_content_type', 'lote_object_id')
    cantidad = models.DecimalField(max_digits=14, decimal_places=4, verbose_name="Cantidad Movida") # +/-
    unidad_medida = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, verbose_name="Unidad de Medida")
    ubicacion_origen = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos_salida', verbose_name="Ubicación Origen")
    ubicacion_destino = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos_entrada', verbose_name="Ubicación Destino")
    documento_referencia = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name="Documento Referencia") # Permitir Nulos
    proceso_referencia_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    proceso_referencia_object_id = models.PositiveIntegerField(null=True, blank=True)
    proceso_referencia_content_object = GenericForeignKey('proceso_referencia_content_type', 'proceso_referencia_object_id')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Usuario Responsable")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    def __str__(self):
        signo = "+" if self.cantidad > 0 else ""
        lote_str = f"Lote ID {self.lote_object_id}"
        try:
            if self.lote_content_object: lote_str = str(self.lote_content_object)
            else: lote_type = self.lote_content_type.model_class().__name__ if self.lote_content_type else "Desconocido"; lote_str = f"{lote_type} ID {self.lote_object_id} (No encontrado)"
        except Exception as e: logger.error(f"Error al obtener lote para MovimientoInventario {self.id}: {e}"); lote_str = f"Lote ID {self.lote_object_id} (Error)"
        unidad_str = getattr(self.unidad_medida, 'codigo', 'N/A')
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.get_tipo_movimiento_display()} - {lote_str} - Cant: {signo}{self.cantidad} {unidad_str}"

    class Meta:
        verbose_name = "Movimiento de Inventario"; verbose_name_plural = "Movimientos de Inventario"
        ordering = ['-timestamp']
        indexes = [ models.Index(fields=["lote_content_type", "lote_object_id", "-timestamp"]), models.Index(fields=["tipo_movimiento", "-timestamp"]), models.Index(fields=["documento_referencia"]), ]