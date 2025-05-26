# productos/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from django.conf import settings

# --- Importar modelos de otras apps ---
# Importamos todos los modelos necesarios de 'configuracion'
from configuracion.models import (
    EstadoProducto, UnidadMedida, CategoriaProducto, SubLinea,
    TipoMaterial, TipoMateriaPrima, Tratamiento, TipoTinta,
    TipoSellado, TipoTroquel, TipoZipper, TipoValvula, TipoImpresion,
    CuentaContable, Servicio
)
# Importar modelo Cliente
from clientes.models import Cliente

def upload_producto_path(instance, filename):
    """Función para definir la ruta de carga de archivos de productos"""
    return f'productos/{instance.codigo}/{filename}'

class ProductoTerminado(models.Model):
    """Modelo maestro para Productos Terminados y sus especificaciones."""

    # --- Campos Principales ---
    codigo = models.CharField(
        max_length=40, unique=True, db_index=True,
        verbose_name="Código Producto",
        help_text="Código único del producto terminado."
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre Producto")
    
    # NUEVO: Campo Cliente
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        null=True, blank=True,  # Permitir nulos temporalmente
        verbose_name="Cliente",
        help_text="Cliente para el cual se fabrica este producto terminado"
    )
    
    tipo_materia_prima = models.ForeignKey(
        TipoMateriaPrima, on_delete=models.PROTECT,
        verbose_name="Tipo Materia Prima Base"
    )
    estado = models.ForeignKey(
        EstadoProducto, on_delete=models.PROTECT,
        verbose_name="Estado", default=1 # Asumiendo 'Activo' es ID 1
    )
    unidad_medida = models.ForeignKey(
        UnidadMedida, on_delete=models.PROTECT,
        verbose_name="Unidad de Medida Principal"
    )
    cuenta_contable = models.ForeignKey(
        CuentaContable, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Cuenta Contable"
    )
    
    # CAMBIO: categoria → linea, subcategoria → sublinea
    linea = models.ForeignKey(
        CategoriaProducto, on_delete=models.PROTECT,
        verbose_name="Línea",
        default=1  # Valor temporal por defecto para migración
    )
    sublinea = models.ForeignKey(
        SubLinea, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="SubLínea"
    )
    
    # ELIMINADO: comercializable
    servicio = models.ForeignKey(
        Servicio, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Servicio Asociado"
    )

    # NUEVO: Campo para archivos adjuntos
    archivo_adjunto = models.FileField(
        upload_to=upload_producto_path, 
        null=True, blank=True,
        verbose_name="Archivo Adjunto",
        help_text="Archivo relacionado con el producto (especificaciones, planos, etc.)"
    )

    # --- Especificaciones Generales ---
    MEDIDA_CHOICES = [("m", "Metros"), ("cm", "Centímetros"), ("mm", "Milímetros"), ("pul", "Pulgadas")]
    medida_en = models.CharField(
        max_length=3, choices=MEDIDA_CHOICES, default="mm",
        verbose_name="Unidad Dimensiones"
    )
    tipo_material = models.ForeignKey(
        TipoMaterial, on_delete=models.PROTECT,
        verbose_name="Tipo Material Específico"
    )
    calibre_um = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(0.0)], verbose_name="Calibre (µm)"
    )
    largo = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)],
        verbose_name="Largo", help_text="Medido en la unidad seleccionada en 'Unidad Dimensiones'"
    )
    ancho = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)],
        verbose_name="Ancho", help_text="Medido en la unidad seleccionada en 'Unidad Dimensiones'"
    )
    factor_decimal = models.DecimalField(
        max_digits=8, decimal_places=2, default=1.00, validators=[MinValueValidator(0.0)],
        verbose_name="Factor Decimal", help_text="Factor multiplicador (propósito a definir)"
    )
    ancho_rollo = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Ancho Rollo (mm?)", help_text="Ancho del rollo de material base"
    )
    metros_lineales = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Metros Lineales"
    )
    
    # ELIMINADOS: lamina, extrusion_doble, programa_lamina
    cantidad_xml = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Cantidad XML"
    )
    largo_material = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Largo Material por Unidad"
    )
    tratamiento = models.ForeignKey(
        Tratamiento, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Tratamiento Superficie"
    )
    tipo_tinta = models.ForeignKey(
        TipoTinta, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Tipo de Tinta Estándar"
    )
    
    # MOVIDO A SECCION IMPRESION: pistas
    color = models.CharField(max_length=40, blank=True, verbose_name="Color Principal")

    # --- Sección Doblado ---
    dob_medida_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, 
        validators=[MinValueValidator(0.0)],
        verbose_name="Doblado: Medida (cm)",
        help_text="Medida para el proceso de doblado en centímetros"
    )

    # --- Sección Sellado ---
    sellado_peso_millar = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Peso Millar (Kg)"
    )
    sellado_tipo = models.ForeignKey(
        TipoSellado, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Sellado: Tipo"
    )
    sellado_fuelle_lateral = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Fuelle Lateral (mm)" # Confirmar unidad
    )
    sellado_fuelle_superior = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Fuelle Superior (mm)" # Confirmar unidad
    )
    sellado_fuelle_fondo = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Fuelle Fondo (mm)" # Confirmar unidad
    )
    sellado_solapa_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Solapa (cm)"
    )
    sellado_troquel_tipo = models.ForeignKey(
        TipoTroquel, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Sellado: Tipo Troquel"
    )
    sellado_troquel_medida = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Medida Troquel (mm?)" # Confirmar unidad
    )
    sellado_zipper_tipo = models.ForeignKey(
        TipoZipper, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Sellado: Tipo Zipper"
    )
    sellado_zipper_medida = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Medida Zipper (mm?)" # Confirmar unidad
    )
    sellado_valvula_tipo = models.ForeignKey(
        TipoValvula, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Sellado: Tipo Válvula"
    )
    sellado_valvula_medida = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Medida Válvula (mm?)" # Confirmar unidad
    )
    sellado_ultrasonido = models.BooleanField(default=False, verbose_name="Sellado: ¿Usa Ultrasonido?")
    sellado_ultrasonido_pos = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Posición Ultrasonido (mm)"
    )
    sellado_precorte = models.BooleanField(default=False, verbose_name="Sellado: ¿Lleva Precorte?")
    sellado_precorte_medida = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)],
        verbose_name="Sellado: Medida Precorte (mm?)"
    )

    # --- Sección Impresión ---
    imp_tipo_impresion = models.ForeignKey(
        TipoImpresion, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Impresión: Tipo Estándar"
    )
    # ELIMINADO: imp_rodillo
    # MOVIDO AQUI: pistas
    pistas = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)],
        verbose_name="Pistas Producción Estándar"
    )
    imp_repeticiones = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)],
        verbose_name="Impresión: Repeticiones Estándar"
    )

    # --- Campos de Auditoría ---
    is_active = models.BooleanField(default=True, verbose_name="Activo", db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True, editable=False)
    actualizado_en = models.DateTimeField(auto_now=True, editable=False)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='productos_creados', null=True, blank=True, editable=False
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='productos_actualizados', null=True, blank=True, editable=False
    )

    # --- Lógica de Negocio y Validación ---
    def _has_related_orders(self):
        """Verifica si existen Órdenes de Producción asociadas."""
        # Importar aquí para evitar importación circular si es necesario
        try:
            from produccion.models import OrdenProduccion
            return OrdenProduccion.objects.filter(producto=self).exists()
        except ImportError:
            # Manejar si la app produccion no está lista aún o hay problemas
            print("Advertencia: No se pudo importar OrdenProduccion para validación.")
            return False # O manejar de otra forma

    def clean(self):
        """Validaciones personalizadas del modelo."""
        super().clean()

        # Validar código no vacío
        if not self.codigo:
            raise ValidationError({'codigo': 'El código no puede estar vacío.'})

        # Validaciones condicionales para Sellado
        if self.sellado_ultrasonido and self.sellado_ultrasonido_pos is None:
            raise ValidationError({'sellado_ultrasonido_pos': 'La posición es requerida si se usa ultrasonido.'})
        if not self.sellado_ultrasonido and self.sellado_ultrasonido_pos is not None:
            raise ValidationError({'sellado_ultrasonido_pos': 'La posición no debe especificarse si no se usa ultrasonido.'})

        if self.sellado_precorte and self.sellado_precorte_medida is None:
            raise ValidationError({'sellado_precorte_medida': 'La medida es requerida si lleva precorte.'})
        if not self.sellado_precorte and self.sellado_precorte_medida is not None:
            raise ValidationError({'sellado_precorte_medida': 'La medida no debe especificarse si no lleva precorte.'})

    def save(self, *args, **kwargs):
        # Validar cambio de código si ya existe y tiene OPs
        # IMPORTANTE: Esta validación es MEJOR hacerla en la capa de API/Formulario
        # ANTES de llamar a save(), porque save() no debería fallar con ValidationError.
        # Lo dejamos aquí como una doble verificación o protección, revirtiendo el cambio.
        original_codigo = None
        if self.pk:
            try:
                original_codigo = ProductoTerminado.objects.values_list('codigo', flat=True).get(pk=self.pk)
                if original_codigo != self.codigo:
                    # Importar aquí para asegurar disponibilidad
                    from produccion.models import OrdenProduccion
                    if OrdenProduccion.objects.filter(producto_id=self.pk).exists():
                        print(f"WARN: Intento de cambiar código en producto {original_codigo} con OPs. Cambio revertido.")
                        self.codigo = original_codigo # Revertir
            except ProductoTerminado.DoesNotExist:
                pass # Es creación
            except ImportError:
                 print("WARN: No se pudo validar cambio de código por falta de OrdenProduccion.")

        # Asignar usuario de auditoría
        user = kwargs.pop('user', None)
        if user and user.is_authenticated:
            if not self.pk: self.creado_por = user
            self.actualizado_por = user

        # Ejecutar clean() para validaciones del modelo ANTES de guardar
        # Nota: full_clean() valida también constraints a nivel de campo y DB
        self.full_clean()

        super().save(*args, **kwargs) # Llama al método save() original

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    class Meta:
        verbose_name = "Producto Terminado"
        verbose_name_plural = "Productos Terminados"
        ordering = ['codigo']