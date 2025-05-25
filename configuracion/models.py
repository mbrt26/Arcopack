# configuracion/models.py

from django.db import models
from django.conf import settings # Para campos de auditoría
from django.utils import timezone # Para campos de fecha/hora

# =============================================
# === MODELOS BÁSICOS DE CONFIGURACIÓN ===
# =============================================

class UnidadMedida(models.Model):
    """Define las unidades de medida utilizables (Kg, m, m², Unid, etc.)."""
    codigo = models.CharField(
        max_length=10, unique=True, verbose_name="Código Unidad",
        help_text="Código corto para la unidad (ej: Kg, m, Unid)."
    )
    nombre = models.CharField(
        max_length=50, verbose_name="Nombre Unidad",
        help_text="Nombre descriptivo de la unidad de medida."
    )

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    class Meta:
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"
        ordering = ['nombre']

class EstadoProducto(models.Model):
    """Define los posibles estados de un Producto Terminado."""
    nombre = models.CharField(
        max_length=50, unique=True, verbose_name="Nombre Estado",
        help_text="Nombre del estado (ej: Activo, Obsoleto)."
    )
    descripcion = models.TextField(
        blank=True, verbose_name="Descripción",
        help_text="Descripción opcional del estado."
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Estado de Producto"
        verbose_name_plural = "Estados de Producto"
        ordering = ['nombre']

class CategoriaProducto(models.Model):
    """Categorías generales para Productos Terminados."""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría de Producto"
        verbose_name_plural = "Categorías de Productos"
        ordering = ['nombre']

class SubcategoriaProducto(models.Model):
    """Subcategorías dentro de una Categoría de Producto."""
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE, related_name='subcategorias')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.categoria.nombre} > {self.nombre}"

    class Meta:
        unique_together = ('categoria', 'nombre')
        verbose_name = "Subcategoría de Producto"
        verbose_name_plural = "Subcategorías de Productos"
        ordering = ['categoria__nombre', 'nombre']

class TipoMateriaPrima(models.Model):
    """Tipos base de materia prima (ej: BOPP, PET, Tinta Base)."""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tipo Materia Prima Base"
        verbose_name_plural = "Tipos Materia Prima Base"
        ordering = ['nombre']

class CategoriaMateriaPrima(models.Model):
    """Categorías para Materias Primas (Film, Tinta, Adhesivo, Componente, Core, etc.)."""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría Materia Prima"
        verbose_name_plural = "Categorías Materias Primas"
        ordering = ['nombre']

class TipoMaterial(models.Model):
    """Material específico con características base (ej: BOPP Transp 20mic)."""
    nombre = models.CharField(max_length=150, unique=True)
    tipo_base = models.ForeignKey(TipoMateriaPrima, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Tipo Base")
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tipo de Material Específico"
        verbose_name_plural = "Tipos de Material Específico"
        ordering = ['nombre']

class Maquina(models.Model):
    """Define las máquinas de producción."""
    TIPO_MAQUINA_CHOICES = [('IMPRESORA', 'Impresora'), ('REFILADORA', 'Refiladora'), ('SELLADORA', 'Selladora'), ('DOBLADORA', 'Dobladora'), ('LAMINADORA', 'Laminadora'), ('EXTRUSORA', 'Extrusora'), ('OTRO', 'Otro')]
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código Máquina")
    nombre = models.CharField(max_length=100, verbose_name="Nombre Máquina")
    tipo = models.CharField(max_length=20, choices=TIPO_MAQUINA_CHOICES, verbose_name="Tipo")
    marca = models.CharField(max_length=100, blank=True); modelo = models.CharField(max_length=100, blank=True)
    ubicacion_planta = models.CharField(max_length=100, blank=True, verbose_name="Ubicación en Planta")
    is_active = models.BooleanField(default=True, verbose_name="Activa")

    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = "Máquina"
        verbose_name_plural = "Máquinas"
        ordering = ['codigo']

class RodilloAnilox(models.Model):
    """Define los rodillos Anilox usados en impresión."""
    codigo = models.CharField(max_length=100, unique=True, verbose_name="Código Anilox")
    lineatura = models.PositiveIntegerField(null=True, blank=True, verbose_name="Lineatura (LPI)")
    volumen = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Volumen (BCM)")
    descripcion = models.CharField(max_length=200, blank=True)
    estado = models.CharField(max_length=50, blank=True, help_text="Ej: Bueno, Regular, Dañado")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    def __str__(self):
        return self.codigo

    class Meta:
        verbose_name = "Rodillo Anilox"
        verbose_name_plural = "Rodillos Anilox"
        ordering = ['codigo']

class CausaParo(models.Model):
    """Define las causas estándar de paros de máquina."""
    TIPO_PARO_CHOICES = [('MECANICO', 'Mecánico'), ('ELECTRICO', 'Eléctrico'), ('OPERATIVO', 'Operativo/Proceso'), ('MATERIAL', 'Falta/Defecto Material'), ('HERRAMIENTA', 'Herramental/Montaje'), ('PROGRAMADO', 'Paro Programado'), ('CALIDAD', 'Problema de Calidad'), ('SEGURIDAD', 'Seguridad'), ('EXTERNO', 'Externo'), ('OTROS', 'Otros')]
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código Causa")
    descripcion = models.CharField(max_length=200, verbose_name="Descripción Causa")
    tipo = models.CharField(max_length=20, choices=TIPO_PARO_CHOICES, verbose_name="Tipo de Causa")
    aplica_a = models.CharField(max_length=200, blank=True, help_text="Opcional: Tipos de máquina donde aplica")
    requiere_observacion = models.BooleanField(default=False, verbose_name="¿Requiere Observación Obligatoria?")

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

    class Meta:
        verbose_name = "Causa de Paro"
        verbose_name_plural = "Causas de Paro"
        ordering = ['tipo', 'codigo']

class TipoDesperdicio(models.Model):
    """Define los tipos de desperdicio que se pueden generar."""
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código Desperdicio")
    descripcion = models.CharField(max_length=200, verbose_name="Descripción Desperdicio")
    es_recuperable = models.BooleanField(default=False, verbose_name="¿Es Recuperable?")

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

    class Meta:
        verbose_name = "Tipo de Desperdicio"
        verbose_name_plural = "Tipos de Desperdicio"
        ordering = ['codigo']

class Proveedor(models.Model):
    """Maestro de Proveedores."""
    nit = models.CharField(max_length=20, unique=True, verbose_name="NIT/RUT")
    razon_social = models.CharField(max_length=255, verbose_name="Razón Social")
    nombre_comercial = models.CharField(max_length=255, blank=True, verbose_name="Nombre Comercial")
    direccion = models.CharField(max_length=255, blank=True); ciudad = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=50, blank=True); email = models.EmailField(blank=True)
    contacto_principal = models.CharField(max_length=150, blank=True)
    dias_credito = models.PositiveIntegerField(default=0, verbose_name="Días de Crédito")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True, editable=False); actualizado_en = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.razon_social

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['razon_social']

class Proceso(models.Model):
    """Define los procesos productivos principales y su orden."""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    orden_flujo = models.PositiveIntegerField(default=0, help_text="Orden en el flujo productivo estándar (menor=antes)", db_index=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Proceso Productivo"
        verbose_name_plural = "Procesos Productivos"
        ordering = ['orden_flujo', 'nombre']

class Ubicacion(models.Model):
    """Representa una ubicación física de almacenamiento."""
    TIPO_UBICACION_CHOICES = [('BODEGA_MP', 'Bodega Materia Prima'), ('BODEGA_PT', 'Bodega Producto Terminado'), ('BODEGA_WIP', 'Bodega Producto en Proceso'), ('PISO_PROD', 'Piso Producción'), ('BUFFER_PROD', 'Buffer Intermedio Producción'), ('CALIDAD', 'Área de Calidad'), ('DESPACHO', 'Área de Despacho'), ('OBSOLETOS', 'Área de Obsoletos'), ('EXTERNO', 'Ubicación Externa'), ('OTRO', 'Otro')]
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código Ubicación")
    nombre = models.CharField(max_length=150, verbose_name="Nombre Ubicación")
    tipo = models.CharField(max_length=20, choices=TIPO_UBICACION_CHOICES, verbose_name="Tipo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    creado_en = models.DateTimeField(auto_now_add=True, editable=False); actualizado_en = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        ordering = ['codigo']

# =============================================================
# === MODELOS AUXILIARES PARA ESPECIFICACIONES DE PRODUCTO ===
# =============================================================

class Lamina(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Tipo de Lámina"
        verbose_name_plural="Tipos de Lámina"
        ordering = ['nombre']

class Tratamiento(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Tratamiento")

    def __str__(self):
         return self.nombre

    class Meta:
         verbose_name="Tratamiento Superficie"
         verbose_name_plural="Tratamientos Superficie"
         ordering = ['nombre']

class TipoTinta(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Tipo Tinta")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Tipo de Tinta"
        verbose_name_plural="Tipos de Tinta"
        ordering = ['nombre']

class ProgramaLamina(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Programa")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Programa de Lámina"
        verbose_name_plural="Programas de Lámina"
        ordering = ['nombre']

class TipoSellado(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Tipo Sellado")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Tipo de Sellado"
        verbose_name_plural="Tipos de Sellado"
        ordering = ['nombre']

class TipoTroquel(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Tipo Troquel")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Tipo de Troquel"
        verbose_name_plural="Tipos de Troquel"
        ordering = ['nombre']

class TipoZipper(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Tipo Zipper")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Tipo de Zipper"
        verbose_name_plural="Tipos de Zipper"
        ordering = ['nombre']

class TipoValvula(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Tipo Válvula")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Tipo de Válvula"
        verbose_name_plural="Tipos de Válvula"
        ordering = ['nombre']

class TipoImpresion(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Tipo Impresión")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Tipo de Impresión"
        verbose_name_plural="Tipos de Impresión"
        ordering = ['nombre']

class CuentaContable(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código Cuenta")
    nombre = models.CharField(max_length=150, verbose_name="Nombre Cuenta")
    naturaleza = models.CharField(max_length=10, choices=[('DEBITO', 'Débito'), ('CREDITO', 'Crédito')], blank=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    class Meta:
        verbose_name="Cuenta Contable"
        verbose_name_plural="Cuentas Contables"
        ordering = ['codigo']

class Servicio(models.Model):
    nombre = models.CharField(max_length=150, unique=True, verbose_name="Nombre Servicio")
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name="Servicio"
        verbose_name_plural="Servicios"
        ordering = ['nombre']