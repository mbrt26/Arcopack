# pedidos/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Pedido, SeguimientoPedido
from notificaciones.models import Notificacion

User = get_user_model()


@receiver(pre_save, sender=Pedido)
def pedido_pre_save(sender, instance, **kwargs):
    """Signal que se ejecuta antes de guardar un pedido"""
    if instance.pk:  # Si es una actualización
        try:
            pedido_anterior = Pedido.objects.get(pk=instance.pk)
            instance._estado_anterior = pedido_anterior.estado
        except Pedido.DoesNotExist:
            instance._estado_anterior = None
    else:  # Si es un nuevo pedido
        instance._estado_anterior = None


@receiver(post_save, sender=Pedido)
def pedido_post_save(sender, instance, created, **kwargs):
    """Signal que se ejecuta después de guardar un pedido"""
    
    if created:
        # Crear primera entrada de seguimiento para pedidos nuevos
        SeguimientoPedido.objects.create(
            pedido=instance,
            estado_anterior=None,
            estado_nuevo=instance.estado,
            usuario=instance.creado_por,
            observaciones='Pedido creado'
        )
        
        # Crear notificación para el equipo de ventas
        Notificacion.objects.create(
            tipo='PEDIDO_NUEVO',
            titulo='Nuevo pedido creado',
            mensaje=f'Se ha creado el pedido {instance.numero_pedido} para {instance.cliente.razon_social}',
            usuario=instance.creado_por,
            datos_adicionales={
                'pedido_id': instance.pk,
                'numero_pedido': instance.numero_pedido,
                'cliente': instance.cliente.razon_social
            }
        )
    
    else:
        # Verificar si cambió el estado
        estado_anterior = getattr(instance, '_estado_anterior', None)
        
        if estado_anterior and estado_anterior != instance.estado:
            # Crear entrada de seguimiento para cambio de estado
            SeguimientoPedido.objects.create(
                pedido=instance,
                estado_anterior=estado_anterior,
                estado_nuevo=instance.estado,
                usuario=instance.actualizado_por,
                observaciones=f'Cambio automático de estado: {estado_anterior} → {instance.estado}'
            )
            
            # Crear notificaciones según el nuevo estado
            crear_notificacion_cambio_estado(instance, estado_anterior)


def crear_notificacion_cambio_estado(pedido, estado_anterior):
    """Crea notificaciones específicas según el cambio de estado"""
    
    notificaciones_config = {
        'CONFIRMADO': {
            'tipo': 'PEDIDO_CONFIRMADO',
            'titulo': 'Pedido confirmado',
            'mensaje': f'El pedido {pedido.numero_pedido} ha sido confirmado y está listo para producción'
        },
        'EN_PRODUCCION': {
            'tipo': 'PEDIDO_EN_PRODUCCION',
            'titulo': 'Pedido en producción',
            'mensaje': f'El pedido {pedido.numero_pedido} ha iniciado su proceso de producción'
        },
        'PRODUCIDO': {
            'tipo': 'PEDIDO_PRODUCIDO',
            'titulo': 'Pedido producido',
            'mensaje': f'El pedido {pedido.numero_pedido} ha sido completado y está listo para facturación'
        },
        'FACTURADO': {
            'tipo': 'PEDIDO_FACTURADO',
            'titulo': 'Pedido facturado',
            'mensaje': f'El pedido {pedido.numero_pedido} ha sido facturado (Factura: {pedido.numero_factura})'
        },
        'ENTREGADO': {
            'tipo': 'PEDIDO_ENTREGADO',
            'titulo': 'Pedido entregado',
            'mensaje': f'El pedido {pedido.numero_pedido} ha sido entregado al cliente'
        },
        'CANCELADO': {
            'tipo': 'PEDIDO_CANCELADO',
            'titulo': 'Pedido cancelado',
            'mensaje': f'El pedido {pedido.numero_pedido} ha sido cancelado'
        }
    }
    
    config = notificaciones_config.get(pedido.estado)
    if config:
        # Determinar usuarios a notificar según el estado
        usuarios_notificar = obtener_usuarios_a_notificar(pedido.estado)
        
        for usuario in usuarios_notificar:
            Notificacion.objects.create(
                tipo=config['tipo'],
                titulo=config['titulo'],
                mensaje=config['mensaje'],
                usuario=usuario,
                datos_adicionales={
                    'pedido_id': pedido.pk,
                    'numero_pedido': pedido.numero_pedido,
                    'cliente': pedido.cliente.razon_social,
                    'estado_anterior': estado_anterior,
                    'estado_nuevo': pedido.estado
                }
            )


def obtener_usuarios_a_notificar(estado):
    """Retorna los usuarios que deben ser notificados según el estado del pedido"""
    
    usuarios_por_estado = {
        'CONFIRMADO': ['group:produccion', 'group:administracion'],
        'EN_PRODUCCION': ['group:ventas', 'group:administracion'],
        'PRODUCIDO': ['group:facturacion', 'group:administracion'],
        'FACTURADO': ['group:ventas', 'group:despacho'],
        'ENTREGADO': ['group:ventas', 'group:administracion'],
        'CANCELADO': ['group:ventas', 'group:administracion']
    }
    
    grupos_notificar = usuarios_por_estado.get(estado, [])
    usuarios = []
    
    for grupo in grupos_notificar:
        if grupo.startswith('group:'):
            grupo_nombre = grupo.replace('group:', '')
            # Obtener usuarios del grupo
            try:
                from django.contrib.auth.models import Group
                grupo_obj = Group.objects.get(name=grupo_nombre)
                usuarios.extend(grupo_obj.user_set.all())
            except Group.DoesNotExist:
                continue
    
    return list(set(usuarios))  # Eliminar duplicados