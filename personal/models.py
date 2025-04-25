# personal/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

class Colaborador(models.Model):
    """Representa un empleado o colaborador de la empresa."""
    # --- Información Básica ---
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    cedula = models.CharField( # Documento de identidad
        max_length=20, unique=True, db_index=True,
        verbose_name="Cédula / Documento ID"
    )
    codigo_empleado = models.CharField( # Código interno de nómina o similar
        max_length=50, unique=True, blank=True, null=True, # Puede no tenerlo o asignarse después
        verbose_name="Código Empleado"
    )

    # --- Información Laboral ---
    cargo = models.CharField(max_length=100, blank=True, verbose_name="Cargo") # O FK a un modelo Cargo
    area = models.CharField(max_length=100, blank=True, verbose_name="Área") # O FK a un modelo Area
    # turno = models.CharField(max_length=50, blank=True, verbose_name="Turno") # O FK a Turno
    fecha_ingreso = models.DateField(null=True, blank=True, verbose_name="Fecha de Ingreso")
    fecha_retiro = models.DateField(null=True, blank=True, verbose_name="Fecha de Retiro")

    # --- Opcional: Vínculo con Usuario Django ---
    # Si los colaboradores van a iniciar sesión en el sistema,
    # vinculamos este registro con un usuario de Django.
    # OneToOneField asegura que un usuario solo puede estar vinculado a un colaborador y viceversa.
    usuario_sistema = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Si se borra el usuario, no borrar el colaborador (o viceversa?)
        null=True, blank=True,
        related_name='colaborador', # Acceso desde user: user.colaborador
        verbose_name="Usuario del Sistema"
    )

    # --- Estado y Auditoría ---
    is_active = models.BooleanField(default=True, verbose_name="Activo", help_text="Indica si el colaborador está actualmente activo.")
    creado_en = models.DateTimeField(auto_now_add=True, editable=False)
    actualizado_en = models.DateTimeField(auto_now=True, editable=False)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL,
        null=True, blank=True, editable=False
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL,
        null=True, blank=True, editable=False
    )

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    def __str__(self):
        return self.nombre_completo

    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"
        ordering = ['apellidos', 'nombres']
        # Podríamos añadir constraints, ej: unique_together si nombres+apellidos+cedula debe ser único (aunque cédula ya es unique)