from django.db import models
from django.conf import settings
from django.utils import timezone

class Notificacion(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    mensaje = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.mensaje} ({self.usuario})"

    def marcar_leida(self):
        if not self.leida:
            self.leida = True
            self.fecha_lectura = timezone.now()
            self.save()