# produccion/models.py

import logging
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DurationField, Q, Max
from django.contrib.auth import get_user_model # Importar get_user_model

# --- Importar modelos de otras apps ---
from inventario.models import LoteMateriaPrima, LoteProductoEnProceso, Tinta
from configuracion.models import UnidadMedida, Ubicacion, Proveedor, CategoriaMateriaPrima, TipoTinta, Maquina, RodilloAnilox, CausaParo, TipoDesperdicio, Proceso
from productos.models import ProductoTerminado
# from clientes.models import Cliente
# from personal.models import Colaborador

User = get_user_model()
logger = logging.getLogger(__name__)

# =============================================
# === MODELO ORDEN DE PRODUCCIÓN ===
# =============================================

class OrdenProduccion(models.Model):
    """Representa una Orden de Producción (OP) en el sistema."""
    ESTADOS_ETAPA = [
        ('PLAN', 'Planeada'), ('PROG', 'Programada'), ('LIBR', 'Liberada a Producción'),
        ('IMPR', 'En Impresión'), ('REFI', 'En Refilado'), ('SELL', 'En Sellado'), ('DOBL', 'En Doblado'),
        ('PEND', 'Pendiente Calidad'), ('TERM', 'Terminada'), ('CTOTAL', 'Cerrada Total'),
        ('CPARC', 'Cerrada Parcial'), ('ANUL', 'Anulada'),
    ]
    op_numero = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="No. Orden Producción (OP)", help_text="Identificador único de la Orden de Producción.")
    pedido_cliente = models.CharField(max_length=100, blank=True, null=True, verbose_name="Pedido Cliente No.")
    id_pedido_contable = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name="ID Pedido Contable")
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, verbose_name="Cliente")
    producto = models.ForeignKey('productos.ProductoTerminado', on_delete=models.PROTECT, verbose_name="Producto Terminado (Referencia)")
    cantidad_solicitada_kg = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Cantidad Solicitada (Kg)")
    cantidad_producida_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Cantidad Producida Acumulada (Kg)", editable=False) # Se actualizará sumando Lotes PT/WIP finales
    fecha_creacion = models.DateTimeField(default=timezone.now, editable=False, verbose_name="Fecha Creación OP")
    fecha_compromiso_entrega = models.DateField(verbose_name="Fecha Compromiso Entrega")
    fecha_estimada_inicio = models.DateField(null=True, blank=True, verbose_name="Fecha Estimada Inicio Prod.")
    fecha_real_inicio = models.DateField(null=True, blank=True, editable=False, verbose_name="Fecha Real Inicio Prod.")
    fecha_real_terminacion = models.DateField(null=True, blank=True, editable=False, verbose_name="Fecha Real Terminación Prod.")
    fecha_real_entrega = models.DateField(null=True, blank=True, editable=False, verbose_name="Fecha Real Entrega")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones", help_text="Información adicional relevante sobre la orden de producción")
    sustrato = models.ForeignKey('inventario.MateriaPrima', on_delete=models.PROTECT, verbose_name="Sustrato Principal")
    ancho_sustrato_mm = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Ancho Sustrato (mm)")
    calibre_sustrato_um = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Calibre Sustrato (µm)")
    tratamiento_sustrato = models.CharField(max_length=100, blank=True, verbose_name="Tratamiento Sustrato")
    color_sustrato = models.CharField(max_length=50, blank=True, verbose_name="Color Sustrato")
    procesos = models.ManyToManyField('configuracion.Proceso', verbose_name="Procesos Requeridos", help_text="Seleccione los procesos por los que debe pasar esta OP.")
    etapa_actual = models.CharField(max_length=10, choices=ESTADOS_ETAPA, default='PLAN', db_index=True, verbose_name="Etapa Actual")
    codigo_barras_op = models.CharField(max_length=100, blank=True, null=True, verbose_name="Código de Barras OP")
    observaciones_generales = models.TextField(blank=True, verbose_name="Observaciones Generales")
    observaciones_produccion = models.TextField(blank=True, verbose_name="Observaciones de Producción")
    is_active = models.BooleanField(default=True, verbose_name="Activa", help_text="Indica si la OP no está anulada.")
    actualizado_en = models.DateTimeField(auto_now=True, editable=False)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='ops_creadas', null=True, blank=True, editable=False)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='ops_actualizadas', null=True, blank=True, editable=False)

    @property
    def codigo_cliente(self): return getattr(self.cliente, 'codigo_cliente', None)
    @property
    def nit_cliente(self): return getattr(self.cliente, 'nit', None)
    @property
    def codigo_referencia(self): return getattr(self.producto, 'codigo', None)

    def save(self, *args, **kwargs):
        # Mantener lógica para anular
        if self.etapa_actual == 'ANUL': self.is_active = False
        # else: self.is_active = True # No reactivar automáticamente al cambiar de ANUL
        # La asignación de usuario creador/actualizador se hace en el Admin/View/API
        super().save(*args, **kwargs)

    def __str__(self):
        cliente_str = getattr(self.cliente, 'razon_social', 'N/A')
        prod_str = getattr(self.producto, 'codigo', 'N/A')
        return f"OP {self.op_numero} - {cliente_str} - {prod_str}"

    class Meta: verbose_name = "Orden de Producción"; verbose_name_plural = "Órdenes de Producción"; ordering = ['-fecha_creacion', 'op_numero']

# =============================================
# === MODELOS PARA REGISTRO DE IMPRESIÓN ===
# =============================================

class RegistroImpresion(models.Model):
    lote_wip_asociado = models.ForeignKey(
        'inventario.LoteProductoEnProceso',
        on_delete=models.PROTECT,
        verbose_name="Lote WIP Asociado",
        null=True, blank=True,
        limit_choices_to={'estado': 'DISPONIBLE'},
        help_text="Solo lotes WIP disponibles y de la misma OP"
    )
    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='registros_impresion')
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha Registro")
    maquina = models.ForeignKey('configuracion.Maquina', on_delete=models.PROTECT, limit_choices_to={'tipo': 'IMPRESORA'})
    operario_principal = models.ForeignKey('personal.Colaborador', on_delete=models.PROTECT, related_name='impresiones_operadas')
    hora_inicio = models.DateTimeField(verbose_name="Fecha y Hora Inicio")
    hora_final = models.DateTimeField(verbose_name="Fecha y Hora Final")
    anilox = models.ForeignKey('configuracion.RodilloAnilox', on_delete=models.PROTECT, verbose_name="Rodillo Anilox")
    repeticion_mm = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Repetición (mm)")
    pistas = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name="Número de Pistas")
    tipo_tinta_principal = models.ForeignKey('inventario.Tinta', on_delete=models.PROTECT, related_name='+', verbose_name="Tipo Tinta Principal")
    aprobado_por = models.ForeignKey('personal.Colaborador', on_delete=models.PROTECT, related_name='impresiones_aprobadas')
    usa_retal = models.BooleanField(default=False, verbose_name="¿Usa Retal?")
    pistas_retal = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)], verbose_name="Pistas en Retal")
    embobinado = models.CharField(max_length=80, blank=True, verbose_name="Sentido Embobinado")
    tipo_montaje = models.CharField(max_length=80, blank=True, verbose_name="Tipo de Montaje")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    def clean(self): # ... (validaciones existentes) ...
        if self.hora_inicio and self.hora_final and self.hora_final <= self.hora_inicio: raise ValidationError({'hora_final': "La hora final debe ser posterior a la hora de inicio."})
        if self.usa_retal and (self.pistas_retal is None or self.pistas_retal < 1): raise ValidationError({'pistas_retal': "Se requieren las pistas si se usa retal."})
        if not self.usa_retal and self.pistas_retal is not None: raise ValidationError({'pistas_retal': 'Pistas retal no debe especificarse si no se usa retal.'})
        if self.maquina_id and self.maquina.tipo != 'IMPRESORA': raise ValidationError({'maquina': "La máquina seleccionada no es de tipo IMPRESORA."})

    # El método save() ya no necesita lógica especial aquí, la asignación de auditoría
    # se hará en el admin/view/api que llame a save.
    # def save(self, *args, **kwargs): ... (simplificado o eliminado)

    @property
    def duracion_total_min(self): # ... (cálculo duración) ...
         if self.hora_inicio and self.hora_final and self.hora_final > self.hora_inicio: return round((self.hora_final - self.hora_inicio).total_seconds() / 60, 2)
         return 0
    # --- Propiedades OEE ---
    # ... (Estos métodos ahora consultarán los Lotes WIP/PT vinculados a través del GFK) ...
    # def get_total_kg_producidos(self): ... LoteProductoEnProceso.objects.filter(proceso_origen...=self)...aggregate(Sum(...)) ...

    def __str__(self): return f"Impresión OP {self.orden_produccion.op_numero} - Máq {self.maquina.codigo} - {self.fecha}"
    class Meta: verbose_name = "Registro de Impresión"; verbose_name_plural = "Registros de Impresión"; ordering = ['-fecha', '-hora_inicio']

# --- Modelos Relacionados con Impresión (Paro, Desperdicio, Consumos) ---
# (ParoImpresion, DesperdicioImpresion, ConsumoTintaImpresion, ConsumoSustratoImpresion sin cambios)
class ParoImpresion(models.Model):
    registro_impresion = models.ForeignKey(RegistroImpresion, on_delete=models.CASCADE, related_name='paros_impresion')
    causa_paro = models.ForeignKey('configuracion.CausaParo', on_delete=models.PROTECT)
    hora_inicio_paro = models.DateTimeField(); hora_final_paro = models.DateTimeField()
    observaciones = models.TextField(blank=True, null=True); is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    @property
    def duracion_paro_min(self):
        if self.hora_inicio_paro and self.hora_final_paro and self.hora_final_paro > self.hora_inicio_paro: return round((self.hora_final_paro - self.hora_inicio_paro).total_seconds() / 60, 2)
        return 0
    def clean(self):
        if self.hora_inicio_paro and self.hora_final_paro and self.hora_final_paro <= self.hora_inicio_paro: raise ValidationError("Hora final debe ser posterior a hora inicio.")
    class Meta: verbose_name = "Paro de Impresión"; verbose_name_plural = "Paros de Impresión"; ordering = ['hora_inicio_paro']

class DesperdicioImpresion(models.Model):
    registro_impresion = models.ForeignKey(RegistroImpresion, on_delete=models.CASCADE, related_name='desperdicios_impresion')
    tipo_desperdicio = models.ForeignKey('configuracion.TipoDesperdicio', on_delete=models.PROTECT)
    cantidad_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))])
    cantidad_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.0'))])
    observaciones = models.TextField(blank=True, null=True); is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    class Meta: verbose_name = "Desperdicio de Impresión"; verbose_name_plural = "Desperdicios de Impresión"

class ConsumoTintaImpresion(models.Model):
    registro_impresion = models.ForeignKey(RegistroImpresion, on_delete=models.CASCADE, related_name='consumo_tintas')
    tinta = models.ForeignKey('inventario.Tinta', on_delete=models.PROTECT)
    cantidad_kg = models.DecimalField(max_digits=8, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    lote_tinta = models.CharField(max_length=100, blank=True, verbose_name="Lote Tinta Consumido")
    is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    # Placeholder: Lógica para consumir LoteMateriaPrima de Tinta en save()
    class Meta: verbose_name = "Consumo de Tinta (Impresión)"; verbose_name_plural = "Consumos de Tinta (Impresión)"

class ConsumoSustratoImpresion(models.Model):
    registro_impresion = models.ForeignKey(RegistroImpresion, on_delete=models.CASCADE, related_name='consumos_sustrato')
    lote_consumido = models.ForeignKey(
        'inventario.LoteMateriaPrima', 
        on_delete=models.PROTECT, 
        verbose_name="Lote Sustrato Consumido", 
        limit_choices_to={'estado': 'DISPONIBLE'},  # Solo lotes disponibles
    )
    cantidad_kg_consumida = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Cantidad Consumida (Kg)")
    registrado_en = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)

    def clean(self): 
        super().clean()
        # Skip validation for empty inline forms
        if self.lote_consumido_id is None or self.registro_impresion_id is None:
            return
        # Validar que el lote corresponda al sustrato de la OP
        if self.lote_consumido_id and self.registro_impresion_id:
            op = self.registro_impresion.orden_produccion
            if self.lote_consumido.materia_prima_id != op.sustrato_id:
                raise ValidationError({
                    'lote_consumido': f'El lote debe ser del sustrato especificado en la OP ({op.sustrato})'
                })
        
        # CORRECCIÓN: Validar stock disponible con tolerancia decimal
        if (
            self.lote_consumido_id and
            self.cantidad_kg_consumida is not None and
            hasattr(self.lote_consumido, 'cantidad_actual') and
            self.lote_consumido.cantidad_actual is not None
        ):
            TOLERANCE = Decimal('0.0001')
            diferencia = self.cantidad_kg_consumida - self.lote_consumido.cantidad_actual
            
            if diferencia > TOLERANCE:
                raise ValidationError({
                    'cantidad_kg_consumida': (
                        f'Cantidad excede el stock disponible. '
                        f'Disponible: {self.lote_consumido.cantidad_actual} Kg, '
                        f'Solicitado: {self.cantidad_kg_consumida} Kg, '
                        f'Exceso: {diferencia} Kg'
                    )
                })
            elif diferencia > 0 and diferencia <= TOLERANCE:
                # Ajustar automáticamente dentro de tolerancia
                logger.warning(
                    f"Ajustando automáticamente cantidad de {self.cantidad_kg_consumida} "
                    f"a {self.lote_consumido.cantidad_actual} Kg para lote {self.lote_consumido.lote_id} "
                    f"(diferencia: {diferencia} dentro de tolerancia)"
                )
                self.cantidad_kg_consumida = self.lote_consumido.cantidad_actual

    def save(self, *args, **kwargs): 
        user = kwargs.pop('user', None)
        is_new = self.pk is None
        
        # CORRECCIÓN: Solo consumir automáticamente si es explícitamente solicitado
        # y si no se ha consumido previamente
        auto_consumir = kwargs.pop('auto_consumir', False)
        
        if is_new and user: 
            self.registrado_por = user
        
        # Guardar el registro primero
        super().save(*args, **kwargs)
        
        # Solo consumir si se solicita explícitamente y es un registro nuevo
        if auto_consumir and is_new and self.lote_consumido and self.cantidad_kg_consumida > 0:
            usuario_accion = user or self.registrado_por or User.objects.filter(is_superuser=True).first()
            if not usuario_accion: 
                raise ValueError("Usuario requerido para consumo automático.")
            try:
                self.lote_consumido.consumir(
                    cantidad_consumir=self.cantidad_kg_consumida, 
                    proceso_ref=self.registro_impresion, 
                    usuario=usuario_accion, 
                    observaciones=f"Consumo auto Reg.Consumo ID {self.id}"
                )
            except (ValidationError, ValueError) as e: 
                logger.error(f"ERROR (ConsumoSustratoImpresion.save): {e}")
                raise e
        
        logger.info(f"ConsumoSustratoImpresion guardado ID:{self.id}. Auto-consumo: {auto_consumir and is_new}")

    def consumir_lote_manual(self, usuario):
        """Método explícito para consumir el lote asociado."""
        if not self.lote_consumido or self.cantidad_kg_consumida <= 0:
            raise ValueError("No hay lote o cantidad válida para consumir.")
        
        return self.lote_consumido.consumir(
            cantidad_consumir=self.cantidad_kg_consumida,
            proceso_ref=self.registro_impresion,
            usuario=usuario,
            observaciones=f"Consumo manual Reg.Consumo ID {self.id}"
        )

    def __str__(self): return f"Consumo {self.cantidad_kg_consumida} Kg Lote {self.lote_consumido_id} en Impresión {self.registro_impresion_id}"
    class Meta: verbose_name = "Consumo Sustrato (Impresión)"; verbose_name_plural = "Consumos Sustrato (Impresión)"; unique_together = ('registro_impresion', 'lote_consumido')


# =============================================
# === MODELOS PARA PROCESO DE REFILADO ===
# =============================================

class Refilado(models.Model):
    # ... (campos existentes) ...
    # --- Campo de producción reportada ELIMINADO ---
    # kg_producidos_reportados = ...
    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='registros_refilado')
    maquina = models.ForeignKey('configuracion.Maquina', on_delete=models.PROTECT, limit_choices_to={'tipo': 'REFILADORA'})
    operario_principal = models.ForeignKey('personal.Colaborador', on_delete=models.PROTECT, related_name='refilados_operados')
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha")
    hora_inicio = models.DateTimeField(verbose_name="Fecha y Hora Inicio")
    hora_final = models.DateTimeField(verbose_name="Fecha y Hora Final")
    cantidad_programada_kg = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Cantidad Programada (Kg)", null=True, blank=True)
    pistas = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name="Número de Pistas (Salidas)")
    embobinado_salida = models.CharField(max_length=80, blank=True, verbose_name="Sentido Embobinado Salida")
    peso_rollo_objetivo_kg = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))], verbose_name="Peso Objetivo por Bobina Salida (Kg)", null=True, blank=True)
    embalaje = models.CharField(max_length=80, blank=True, verbose_name="Tipo Embalaje Salida")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    def clean(self): # ... (validaciones) ...
        if self.hora_inicio and self.hora_final and self.hora_final <= self.hora_inicio: raise ValidationError({'hora_final': "La hora final debe ser posterior a la hora de inicio."})
        if self.maquina_id and self.maquina.tipo != 'REFILADORA': raise ValidationError({'maquina': "La máquina seleccionada no es de tipo REFILADORA."})

    # --- Propiedades OEE ---
    # ... (Definir aquí o calcular en vistas/reports) ...

    def __str__(self): return f"Refilado OP {self.orden_produccion.op_numero} - Máq {self.maquina.codigo} - {self.fecha}"
    class Meta: verbose_name = "Registro de Refilado"; verbose_name_plural = "Registros de Refilado"; ordering = ['-fecha', '-hora_inicio']

# --- Modelos Relacionados con Refilado ---
# (ParoRefilado, DesperdicioRefilado, ConsumoWipRefilado, ConsumoMpRefilado sin cambios)
class ParoRefilado(models.Model):
    refilado = models.ForeignKey(Refilado, on_delete=models.CASCADE, related_name='paros_refilado')
    causa_paro = models.ForeignKey('configuracion.CausaParo', on_delete=models.PROTECT)
    hora_inicio_paro = models.DateTimeField(); hora_final_paro = models.DateTimeField()
    observaciones = models.TextField(blank=True, null=True); is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    @property
    def duracion_paro_min(self):
        if self.hora_inicio_paro and self.hora_final_paro and self.hora_final_paro > self.hora_inicio_paro: return round((self.hora_final_paro - self.hora_inicio_paro).total_seconds() / 60, 2)
        return 0
    def clean(self):
        if self.hora_inicio_paro and self.hora_final_paro and self.hora_final_paro <= self.hora_inicio_paro: raise ValidationError("Hora final debe ser posterior a hora inicio.")
    class Meta: verbose_name = "Paro de Refilado"; verbose_name_plural = "Paros de Refilado"; ordering = ['hora_inicio_paro']

class DesperdicioRefilado(models.Model):
    refilado = models.ForeignKey(Refilado, on_delete=models.CASCADE, related_name='desperdicios_refilado')
    tipo_desperdicio = models.ForeignKey('configuracion.TipoDesperdicio', on_delete=models.PROTECT)
    kg_desperdicio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))])
    observaciones = models.TextField(blank=True, null=True); is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    class Meta: verbose_name = "Desperdicio de Refilado"; verbose_name_plural = "Desperdicios de Refilado"

class ConsumoWipRefilado(models.Model):
    registro_refilado = models.ForeignKey(Refilado, on_delete=models.CASCADE, related_name='consumos_wip')
    lote_consumido = models.ForeignKey(
        'inventario.LoteProductoEnProceso', 
        on_delete=models.PROTECT, 
        verbose_name="Lote WIP Consumido", 
        limit_choices_to={'estado': 'DISPONIBLE'}
    )
    cantidad_kg_consumida = models.DecimalField(
        max_digits=12, decimal_places=3, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        verbose_name="Cantidad Consumida (Kg)"
    )
    registrado_en = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)

    def clean(self): # ... (Validación de stock) ...
         super().clean()
         # Validar que el lote pertenezca a la misma OP
         if self.lote_consumido and self.registro_refilado:
             if self.lote_consumido.orden_produccion_id != self.registro_refilado.orden_produccion_id:
                 raise ValidationError({
                     'lote_consumido': 'El lote debe pertenecer a la misma Orden de Producción'
                 })
         if self.lote_consumido and hasattr(self.lote_consumido, 'cantidad_actual') and self.cantidad_kg_consumida > self.lote_consumido.cantidad_actual: raise ValidationError(...)

    def save(self, *args, **kwargs): # ... (Lógica de consumo) ...
        user = kwargs.pop('user', None); is_new = self.pk is None
        if is_new and user: self.registrado_por = user
        # self.full_clean() # Llamado desde admin save_formset
        if self.lote_consumido and self.cantidad_kg_consumida > 0:
             usuario_accion = user or self.registrado_por or User.objects.filter(is_superuser=True).first()
             if not usuario_accion: raise ValueError("Usuario requerido.")
             try: self.lote_consumido.consumir(cantidad_consumir=self.cantidad_kg_consumida, proceso_ref=self.registro_refilado, usuario=usuario_accion, observaciones=f"Consumo WIP auto Reg.Consumo Refilado ID {self.id or 'nuevo'}")
             except (ValidationError, ValueError) as e: logger.error(f"ERROR (ConsumoWipRefilado.save): {e}"); raise e
        super().save(*args, **kwargs)

    def __str__(self): return f"Consumo WIP {self.cantidad_kg_consumida} Kg Lote {self.lote_consumido_id} en Refilado {self.registro_refilado_id}"
    class Meta: verbose_name = "Consumo WIP (Refilado)"; verbose_name_plural = "Consumos WIP (Refilado)"; unique_together = ('registro_refilado', 'lote_consumido')

class ConsumoMpRefilado(models.Model):
    registro_refilado = models.ForeignKey(Refilado, on_delete=models.CASCADE, related_name='consumos_mp')
    lote_consumido = models.ForeignKey('inventario.LoteMateriaPrima', on_delete=models.PROTECT, verbose_name="Lote MP Consumido", limit_choices_to={'estado': 'DISPONIBLE'})
    cantidad_consumida = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Cantidad Consumida")
    registrado_en = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)

    def clean(self): # ... (Validación de stock) ...
         super().clean()
         if self.lote_consumido and hasattr(self.lote_consumido, 'cantidad_actual') and self.cantidad_consumida > self.lote_consumido.cantidad_actual: raise ValidationError(...)

    def save(self, *args, **kwargs): # ... (Lógica de consumo) ...
        user = kwargs.pop('user', None); is_new = self.pk is None
        if is_new and user: self.registrado_por = user
        # self.full_clean()
        if self.lote_consumido and self.cantidad_consumida > 0:
             usuario_accion = user or self.registrado_por or User.objects.filter(is_superuser=True).first()
             if not usuario_accion: raise ValueError("Usuario requerido.")
             try: self.lote_consumido.consumir(cantidad_consumir=self.cantidad_consumida, proceso_ref=self.registro_refilado, usuario=usuario_accion, observaciones=f"Consumo MP auto Reg.Consumo Refilado ID {self.id or 'nuevo'}")
             except (ValidationError, ValueError) as e: logger.error(f"ERROR (ConsumoMpRefilado.save): {e}"); raise e
        super().save(*args, **kwargs)

    def __str__(self): return f"Consumo MP {self.cantidad_consumida} Lote {self.lote_consumido_id} en Refilado {self.registro_refilado_id}"
    class Meta: verbose_name = "Consumo MP (Refilado)"; verbose_name_plural = "Consumos MP (Refilado)"


# =============================================
# === MODELOS PARA PROCESO DE SELLADO ===
# =============================================

class Sellado(models.Model):
    # ... (campos existentes) ...
    # --- Campo de producción reportada ELIMINADO ---
    # unidades_producidas_reportadas = ...
    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='registros_sellado')
    maquina = models.ForeignKey('configuracion.Maquina', on_delete=models.PROTECT, limit_choices_to={'tipo': 'SELLADORA'})
    operario_principal = models.ForeignKey('personal.Colaborador', on_delete=models.PROTECT, related_name='sellados_operados')
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha")
    hora_inicio = models.DateTimeField(verbose_name="Fecha y Hora Inicio")
    hora_final = models.DateTimeField(verbose_name="Fecha y Hora Final")
    cantidad_programada_unidades = models.PositiveIntegerField(verbose_name="Cantidad Programada (Unidades)", null=True, blank=True)
    ancho_mm = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Ancho Bolsa (mm)")
    largo_mm = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Largo Bolsa (mm)")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    def clean(self): # ... (validaciones) ...
         if self.hora_inicio and self.hora_final and self.hora_final <= self.hora_inicio: raise ValidationError({'hora_final': "La hora final debe ser posterior a la hora de inicio."})
         if self.maquina_id and self.maquina.tipo != 'SELLADORA': raise ValidationError({'maquina': "La máquina seleccionada no es de tipo SELLADORA."})

    # --- Propiedades OEE ---
    # ... (Definir aquí o calcular en vistas/reports) ...

    def __str__(self): return f"Sellado OP {self.orden_produccion.op_numero} - Máq {self.maquina.codigo} - {self.fecha}"
    class Meta: verbose_name = "Registro de Sellado"; verbose_name_plural = "Registros de Sellado"; ordering = ['-fecha', '-hora_inicio']

# --- Modelos Relacionados con Sellado ---
# (ParoSellado, DesperdicioSellado, ConsumoWipSellado, ConsumoMpSellado sin cambios)
class ParoSellado(models.Model):
    sellado = models.ForeignKey(Sellado, on_delete=models.CASCADE, related_name='paros_sellado')
    causa_paro = models.ForeignKey('configuracion.CausaParo', on_delete=models.PROTECT)
    hora_inicio_paro = models.DateTimeField(); hora_final_paro = models.DateTimeField()
    observaciones = models.TextField(blank=True, null=True); is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    @property
    def duracion_paro_min(self): # ... (cálculo) ...
        if self.hora_inicio_paro and self.hora_final_paro and self.hora_final_paro > self.hora_inicio_paro: return round((self.hora_final_paro - self.hora_inicio_paro).total_seconds() / 60, 2)
        return 0
    def clean(self): # ... (validación horas) ...
        if self.hora_inicio_paro and self.hora_final_paro and self.hora_final_paro <= self.hora_inicio_paro: raise ValidationError("Hora final debe ser posterior a hora inicio.")
    class Meta: verbose_name = "Paro de Sellado"; verbose_name_plural = "Paros de Sellado"; ordering = ['hora_inicio_paro']

class DesperdicioSellado(models.Model):
    sellado = models.ForeignKey(Sellado, on_delete=models.CASCADE, related_name='desperdicios_sellado')
    tipo_desperdicio = models.ForeignKey('configuracion.TipoDesperdicio', on_delete=models.PROTECT)
    kg_desperdicio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))])
    observaciones = models.TextField(blank=True, null=True); is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    class Meta: verbose_name = "Desperdicio de Sellado"; verbose_name_plural = "Desperdicios de Sellado"

class ConsumoWipSellado(models.Model):
    registro_sellado = models.ForeignKey(Sellado, on_delete=models.CASCADE, related_name='consumos_wip')
    lote_consumido = models.ForeignKey('inventario.LoteProductoEnProceso', on_delete=models.PROTECT, verbose_name="Lote WIP Consumido", limit_choices_to={'estado': 'DISPONIBLE'})
    cantidad_kg_consumida = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Cantidad Consumida (Kg)")
    registrado_en = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)

    def clean(self): # ... (Validación de stock) ...
         super().clean()
         if self.lote_consumido and hasattr(self.lote_consumido, 'cantidad_actual') and self.cantidad_kg_consumida > self.lote_consumido.cantidad_actual: raise ValidationError(...)

    def save(self, *args, **kwargs): # ... (Lógica de consumo) ...
        user = kwargs.pop('user', None); is_new = self.pk is None
        if is_new and user: self.registrado_por = user
        # self.full_clean()
        if self.lote_consumido and self.cantidad_kg_consumida > 0:
             usuario_accion = user or self.registrado_por or User.objects.filter(is_superuser=True).first()
             if not usuario_accion: raise ValueError("Usuario requerido.")
             try: self.lote_consumido.consumir(cantidad_consumir=self.cantidad_kg_consumida, proceso_ref=self.registro_sellado, usuario=usuario_accion, observaciones=f"Consumo WIP auto Reg.Consumo Sellado ID {self.id or 'nuevo'}")
             except (ValidationError, ValueError) as e: logger.error(f"ERROR (ConsumoWipSellado.save): {e}"); raise e
        super().save(*args, **kwargs)

    def __str__(self): return f"Consumo WIP {self.cantidad_kg_consumida} Kg Lote {self.lote_consumido_id} en Sellado {self.registro_sellado_id}"
    class Meta: verbose_name = "Consumo WIP (Sellado)"; verbose_name_plural = "Consumos WIP (Sellado)"; unique_together = ('registro_sellado', 'lote_consumido')

class ConsumoMpSellado(models.Model):
    registro_sellado = models.ForeignKey(Sellado, on_delete=models.CASCADE, related_name='consumos_mp')
    lote_consumido = models.ForeignKey('inventario.LoteMateriaPrima', on_delete=models.PROTECT, verbose_name="Lote MP Consumido", limit_choices_to={'estado': 'DISPONIBLE'})
    cantidad_consumida = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Cantidad Consumida")
    registrado_en = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)

    def clean(self): # ... (Validación de stock) ...
        super().clean()
        if self.lote_consumido and hasattr(self.lote_consumido, 'cantidad_actual') and self.cantidad_consumida > self.lote_consumido.cantidad_actual: raise ValidationError(...)

    def save(self, *args, **kwargs): # ... (Lógica de consumo) ...
        user = kwargs.pop('user', None); is_new = self.pk is None
        if is_new and user: self.registrado_por = user
        # self.full_clean()
        if self.lote_consumido and self.cantidad_consumida > 0:
            usuario_accion = user or self.registrado_por or User.objects.filter(is_superuser=True).first()
            if not usuario_accion: raise ValueError("Usuario requerido.")
            try: self.lote_consumido.consumir(cantidad_consumir=self.cantidad_consumida, proceso_ref=self.registro_sellado, usuario=usuario_accion, observaciones=f"Consumo MP auto Reg.Consumo Sellado ID {self.id or 'nuevo'}")
            except (ValidationError, ValueError) as e: logger.error(f"ERROR (ConsumoMpSellado.save): {e}"); raise e
        super().save(*args, **kwargs)

    def __str__(self): return f"Consumo MP {self.cantidad_consumida} Lote {self.lote_consumido_id} en Sellado {self.registro_sellado_id}"
    class Meta: verbose_name = "Consumo MP (Sellado)"; verbose_name_plural = "Consumos MP (Sellado)"


# =============================================
# === MODELOS PARA PROCESO DE DOBLADO ===
# =============================================

class Doblado(models.Model):
    # ... (campos existentes) ...
    # --- Campo de producción reportada ELIMINADO ---
    # kg_producidos_reportados = ...
    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='registros_doblado')
    maquina = models.ForeignKey('configuracion.Maquina', on_delete=models.PROTECT, limit_choices_to={'tipo': 'DOBLADORA'})
    operario_principal = models.ForeignKey('personal.Colaborador', on_delete=models.PROTECT, related_name='doblados_operados')
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha")
    hora_inicio = models.DateTimeField(verbose_name="Fecha y Hora Inicio")
    hora_final = models.DateTimeField(verbose_name="Fecha y Hora Final")
    cantidad_programada_kg = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Cantidad Programada (Kg)")
    medida_doblado_cm = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Medida Doblado (cm)")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    def clean(self): # ... (validaciones) ...
        if self.hora_inicio and self.hora_final and self.hora_final <= self.hora_inicio: raise ValidationError({'hora_final': "La hora final debe ser posterior a la hora de inicio."})
        if self.maquina_id and self.maquina.tipo != 'DOBLADORA': raise ValidationError({'maquina': "La máquina seleccionada no es de tipo DOBLADORA."})

    # --- Propiedades OEE ---
    # ... (Definir aquí o calcular en vistas/reports) ...

    def __str__(self): return f"Doblado OP {self.orden_produccion.op_numero} - Máq {self.maquina.codigo} - {self.fecha}"
    class Meta: verbose_name = "Registro de Doblado"; verbose_name_plural = "Registros de Doblado"; ordering = ['-fecha', '-hora_inicio']

# --- Modelos Relacionados con Doblado ---
# (ParoDoblado, DesperdicioDoblado, ConsumoWipDoblado, ConsumoMpDoblado sin cambios)
class ParoDoblado(models.Model):
    doblado = models.ForeignKey(Doblado, on_delete=models.CASCADE, related_name='paros_doblado')
    causa_paro = models.ForeignKey('configuracion.CausaParo', on_delete=models.PROTECT)
    hora_inicio_paro = models.DateTimeField(); hora_final_paro = models.DateTimeField()
    observaciones = models.TextField(blank=True, null=True); is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    @property
    def duracion_paro_min(self): # ... (cálculo) ...
        if self.hora_inicio_paro and self.hora_final_paro and self.hora_final_paro > self.hora_inicio_paro: return round((self.hora_final_paro - self.hora_inicio_paro).total_seconds() / 60, 2)
        return 0
    def clean(self): # ... (validación horas) ...
        if self.hora_inicio_paro and self.hora_final_paro and self.hora_final_paro <= self.hora_inicio_paro: raise ValidationError("Hora final debe ser posterior a hora inicio.")
    class Meta: verbose_name = "Paro de Doblado"; verbose_name_plural = "Paros de Doblado"; ordering = ['hora_inicio_paro']

class DesperdicioDoblado(models.Model):
    doblado = models.ForeignKey(Doblado, on_delete=models.CASCADE, related_name='desperdicios_doblado')
    tipo_desperdicio = models.ForeignKey('configuracion.TipoDesperdicio', on_delete=models.PROTECT)
    kg_desperdicio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))])
    observaciones = models.TextField(blank=True, null=True); is_active = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True); actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    class Meta: verbose_name = "Desperdicio de Doblado"; verbose_name_plural = "Desperdicios de Doblado"

class ConsumoWipDoblado(models.Model):
    registro_doblado = models.ForeignKey(Doblado, on_delete=models.CASCADE, related_name='consumos_wip')
    lote_consumido = models.ForeignKey('inventario.LoteProductoEnProceso', on_delete=models.PROTECT, verbose_name="Lote WIP Consumido", limit_choices_to={'estado': 'DISPONIBLE'})
    cantidad_kg_consumida = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Cantidad Consumida (Kg)")
    registrado_en = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)

    def clean(self): # ... (Validación de stock) ...
        super().clean()
        if self.lote_consumido and hasattr(self.lote_consumido, 'cantidad_actual') and self.cantidad_kg_consumida > self.lote_consumido.cantidad_actual: raise ValidationError(...)

    def save(self, *args, **kwargs): # ... (Lógica de consumo) ...
        user = kwargs.pop('user', None); is_new = self.pk is None
        if is_new and user: self.registrado_por = user
        # self.full_clean()
        if self.lote_consumido and self.cantidad_kg_consumida > 0:
             usuario_accion = user or self.registrado_por or User.objects.filter(is_superuser=True).first()
             if not usuario_accion: raise ValueError("Usuario requerido.")
             try: self.lote_consumido.consumir(cantidad_consumir=self.cantidad_kg_consumida, proceso_ref=self.registro_doblado, usuario=usuario_accion, observaciones=f"Consumo WIP auto Reg.Consumo Doblado ID {self.id or 'nuevo'}")
             except (ValidationError, ValueError) as e: logger.error(f"ERROR (ConsumoWipDoblado.save): {e}"); raise e
        super().save(*args, **kwargs)

    def __str__(self): return f"Consumo WIP {self.cantidad_kg_consumida} Kg Lote {self.lote_consumido_id} en Doblado {self.registro_doblado_id}"
    class Meta: verbose_name = "Consumo WIP (Doblado)"; verbose_name_plural = "Consumos WIP (Doblado)"; unique_together = ('registro_doblado', 'lote_consumido')

class ConsumoMpDoblado(models.Model):
    registro_doblado = models.ForeignKey(Doblado, on_delete=models.CASCADE, related_name='consumos_mp')
    lote_consumido = models.ForeignKey('inventario.LoteMateriaPrima', on_delete=models.PROTECT, verbose_name="Lote MP Consumido", limit_choices_to={'estado': 'DISPONIBLE'})
    cantidad_consumida = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Cantidad Consumida")
    registrado_en = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)

    def clean(self): # ... (Validación de stock) ...
         super().clean()
         if self.lote_consumido and hasattr(self.lote_consumido, 'cantidad_actual') and self.cantidad_consumida > self.lote_consumido.cantidad_actual: raise ValidationError(...)

    def save(self, *args, **kwargs): # ... (Lógica de consumo) ...
        user = kwargs.pop('user', None); is_new = self.pk is None
        if is_new and user: self.registrado_por = user
        # self.full_clean()
        if self.lote_consumido and self.cantidad_consumida > 0:
             usuario_accion = user or self.registrado_por or User.objects.filter(is_superuser=True).first()
             if not usuario_accion: raise ValueError("Usuario requerido.")
             try: self.lote_consumido.consumir(cantidad_consumir=self.cantidad_consumida, proceso_ref=self.registro_doblado, usuario=usuario_accion, observaciones=f"Consumo MP auto Reg.Consumo Doblado ID {self.id or 'nuevo'}")
             except (ValidationError, ValueError) as e: logger.error(f"ERROR (ConsumoMpDoblado.save): {e}"); raise e
        super().save(*args, **kwargs)

    def __str__(self): return f"Consumo MP {self.cantidad_consumida} Lote {self.lote_consumido_id} en Doblado {self.registro_doblado_id}"
    class Meta: verbose_name = "Consumo MP (Doblado)"; verbose_name_plural = "Consumos MP (Doblado)"


# --- SEÑALES (Opcional, si almacenas indicadores OEE en los modelos principales) ---
# ...

class OrdenProduccionProceso(models.Model):
    """Define la secuencia de procesos por los que pasa una Orden de Producción."""
    orden_produccion = models.ForeignKey('OrdenProduccion', on_delete=models.CASCADE, related_name='procesos_secuencia')
    proceso = models.ForeignKey('configuracion.Proceso', on_delete=models.PROTECT)
    secuencia = models.PositiveIntegerField(help_text="Orden/secuencia del proceso en la OP (1=primero, 2=segundo, ...)")

    class Meta:
        unique_together = ('orden_produccion', 'proceso')
        ordering = ['orden_produccion', 'secuencia']
        verbose_name = "Secuencia de Proceso en OP"
        verbose_name_plural = "Secuencias de Procesos en OP"

    def __str__(self):
        return f"{self.orden_produccion} - {self.secuencia}. {self.proceso}"