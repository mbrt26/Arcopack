# clientes/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

# Importar modelos relacionados si fuera necesario (ej: Vendedor de 'personal')
# from personal.models import Colaborador

class Cliente(models.Model):
    """Representa un cliente de la empresa."""
    ORIGEN_CHOICES = [
        ('MANUAL', 'Registro Manual'),
        ('API', 'Sincronizado desde API Externa'),
    ]

    # --- Identificación ---
    nit = models.CharField(
        max_length=20, unique=True, db_index=True,
        verbose_name="NIT / Documento ID",
        help_text="Número de Identificación Tributaria u otro documento oficial."
    )
    codigo_cliente = models.CharField(
        max_length=50, unique=True, blank=True, null=True, # Puede venir de API o ser interno
        verbose_name="Código Cliente",
        help_text="Código interno o del sistema externo."
    )
    razon_social = models.CharField(max_length=255, verbose_name="Razón Social")
    nombre_comercial = models.CharField(
        max_length=255, blank=True,
        verbose_name="Nombre Comercial"
    )

    # --- Información de Contacto y Ubicación ---
    direccion_principal = models.CharField(max_length=255, blank=True, verbose_name="Dirección Principal")
    ciudad = models.CharField(max_length=100, blank=True)
    departamento = models.CharField(max_length=100, blank=True) # O usar Choices o FK a división administrativa
    pais = models.CharField(max_length=100, blank=True, default="Colombia")
    telefono_principal = models.CharField(max_length=50, blank=True, verbose_name="Teléfono Principal")
    email_principal = models.EmailField(blank=True, verbose_name="Email Principal")
    nombre_contacto_principal = models.CharField(max_length=150, blank=True, verbose_name="Contacto Principal")
    email_contacto_principal = models.EmailField(blank=True, verbose_name="Email Contacto Principal")

    # --- Información Comercial (Opcional) ---
    # vendedor_asignado = models.ForeignKey('personal.Colaborador', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vendedor Asignado")
    condiciones_pago = models.CharField(max_length=100, blank=True, verbose_name="Condiciones de Pago") # O FK a un modelo de CondicionesPago
    cupo_credito = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Cupo de Crédito")

    # --- Integración y Estado ---
    origen_datos = models.CharField(
        max_length=10, choices=ORIGEN_CHOICES, default='MANUAL',
        verbose_name="Origen del Registro"
    )
    id_externo = models.CharField( # ID en el sistema externo (contable, CRM)
        max_length=100, blank=True, null=True, db_index=True,
        verbose_name="ID Sistema Externo"
    )
    ultima_sincronizacion = models.DateTimeField(null=True, blank=True, editable=False, verbose_name="Última Sincronización API")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    # --- Auditoría ---
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='clientes_creados',
        null=True, blank=True, editable=False
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='clientes_actualizados',
        null=True, blank=True, editable=False
    )

    def __str__(self):
        return f"{self.razon_social} (NIT: {self.nit})"

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['razon_social']