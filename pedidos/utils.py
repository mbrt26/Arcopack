# pedidos/utils.py

from django.utils import timezone
from django.db.models import Max
from decimal import Decimal
import re
from datetime import datetime, date

from .models import Pedido


def generar_numero_pedido():
    """
    Genera un número de pedido automático con formato PED-YYYY-NNNN
    """
    year = timezone.now().year
    
    # Buscar el último número del año actual
    ultimo_pedido = Pedido.objects.filter(
        numero_pedido__startswith=f'PED-{year}-'
    ).aggregate(
        max_numero=Max('numero_pedido')
    )
    
    if ultimo_pedido['max_numero']:
        # Extraer el número secuencial del último pedido
        try:
            ultimo_numero = int(ultimo_pedido['max_numero'].split('-')[2])
            nuevo_numero = ultimo_numero + 1
        except (IndexError, ValueError):
            nuevo_numero = 1
    else:
        nuevo_numero = 1
    
    return f'PED-{year}-{nuevo_numero:04d}'


def validar_numero_pedido(numero_pedido):
    """
    Valida que el formato del número de pedido sea correcto
    """
    patron = r'^PED-\d{4}-\d{4}$'
    return bool(re.match(patron, numero_pedido))


def calcular_valor_total_pedido(pedido):
    """
    Calcula el valor total de un pedido basado en sus líneas
    """
    total = Decimal('0.00')
    
    for linea in pedido.lineas.all():
        subtotal = linea.cantidad * linea.precio_unitario
        total += subtotal
    
    return total


def obtener_estados_permitidos(estado_actual):
    """
    Retorna los estados a los que se puede cambiar desde el estado actual
    """
    transiciones = {
        'BORRADOR': ['CONFIRMADO', 'CANCELADO'],
        'CONFIRMADO': ['EN_PRODUCCION', 'CANCELADO'],
        'EN_PRODUCCION': ['PRODUCIDO', 'CANCELADO'],
        'PRODUCIDO': ['PENDIENTE_FACTURAR', 'FACTURADO'],
        'PENDIENTE_FACTURAR': ['FACTURADO'],
        'FACTURADO': ['ENTREGADO'],
        'ENTREGADO': [],  # Estado final
        'CANCELADO': []   # Estado final
    }
    
    return transiciones.get(estado_actual, [])


def validar_cambio_estado(estado_actual, estado_nuevo):
    """
    Valida si es posible cambiar del estado actual al nuevo estado
    """
    estados_permitidos = obtener_estados_permitidos(estado_actual)
    return estado_nuevo in estados_permitidos


def calcular_dias_para_vencimiento(fecha_compromiso):
    """
    Calcula cuántos días faltan para el vencimiento del pedido
    """
    if not fecha_compromiso:
        return None
    
    hoy = date.today()
    delta = fecha_compromiso - hoy
    return delta.days


def obtener_prioridad_por_vencimiento(dias_vencimiento):
    """
    Sugiere una prioridad basada en los días para vencimiento
    """
    if dias_vencimiento is None:
        return 'NORMAL'
    
    if dias_vencimiento < 0:
        return 'URGENTE'  # Vencido
    elif dias_vencimiento <= 3:
        return 'URGENTE'  # Menos de 3 días
    elif dias_vencimiento <= 7:
        return 'ALTA'     # Una semana
    elif dias_vencimiento <= 15:
        return 'NORMAL'   # Dos semanas
    else:
        return 'BAJA'     # Más de dos semanas


def formatear_numero_pedido_para_busqueda(termino_busqueda):
    """
    Formatea un término de búsqueda para encontrar pedidos
    Permite buscar por número parcial o completo
    """
    termino = termino_busqueda.strip().upper()
    
    # Si es solo números, agregar prefijo
    if termino.isdigit():
        year = timezone.now().year
        if len(termino) <= 4:
            return f'PED-{year}-{termino.zfill(4)}'
        else:
            return f'PED-{termino[:4]}-{termino[4:].zfill(4)}'
    
    # Si ya tiene formato parcial, completar
    if termino.startswith('PED-'):
        return termino
    
    return termino


def obtener_estadisticas_pedidos():
    """
    Obtiene estadísticas generales de pedidos
    """
    from django.db.models import Count, Sum, Q
    
    estadisticas = {}
    
    # Conteos por estado
    estados = Pedido.objects.values('estado').annotate(
        count=Count('id')
    ).order_by('estado')
    
    estadisticas['por_estado'] = {
        estado['estado']: estado['count'] 
        for estado in estados
    }
    
    # Conteos por prioridad
    prioridades = Pedido.objects.values('prioridad').annotate(
        count=Count('id')
    ).order_by('prioridad')
    
    estadisticas['por_prioridad'] = {
        prioridad['prioridad']: prioridad['count'] 
        for prioridad in prioridades
    }
    
    # Totales
    estadisticas['total'] = Pedido.objects.count()
    estadisticas['total_valor'] = Pedido.objects.aggregate(
        total=Sum('valor_total')
    )['total'] or Decimal('0.00')
    
    # Pedidos del mes actual
    mes_actual = timezone.now().month
    year_actual = timezone.now().year
    
    estadisticas['mes_actual'] = Pedido.objects.filter(
        fecha_pedido__month=mes_actual,
        fecha_pedido__year=year_actual
    ).count()
    
    # Pedidos vencidos
    estadisticas['vencidos'] = Pedido.objects.filter(
        fecha_compromiso__lt=date.today(),
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    ).count()
    
    # Pedidos próximos a vencer (próximos 7 días)
    fecha_limite = date.today() + timezone.timedelta(days=7)
    estadisticas['proximos_vencer'] = Pedido.objects.filter(
        fecha_compromiso__lte=fecha_limite,
        fecha_compromiso__gte=date.today(),
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    ).count()
    
    return estadisticas


def validar_disponibilidad_producto(producto_id, cantidad_solicitada):
    """
    Valida si hay suficiente inventario del producto
    (Placeholder para integración futura con módulo de inventario)
    """
    # TODO: Integrar con módulo de inventario
    # Por ahora retorna True asumiendo disponibilidad
    return True, "Producto disponible"


def calcular_fecha_estimada_entrega(fecha_pedido, lineas_pedido):
    """
    Calcula una fecha estimada de entrega basada en los productos del pedido
    """
    from datetime import timedelta
    
    # Días base de procesamiento
    dias_base = 7
    
    # Agregar días adicionales según la complejidad
    dias_adicionales = 0
    
    for linea in lineas_pedido:
        # Agregar días según la cantidad (cada 100 unidades = 1 día adicional)
        dias_adicionales += int(linea.cantidad / 100)
        
        # Si tiene especificaciones técnicas, agregar días
        if linea.especificaciones_tecnicas:
            dias_adicionales += 2
    
    # Máximo 30 días adicionales
    dias_adicionales = min(dias_adicionales, 30)
    
    fecha_estimada = fecha_pedido + timedelta(days=dias_base + dias_adicionales)
    
    # No entregar en fines de semana (ajustar al lunes siguiente)
    while fecha_estimada.weekday() in [5, 6]:  # Sábado = 5, Domingo = 6
        fecha_estimada += timedelta(days=1)
    
    return fecha_estimada


def generar_resumen_pedido(pedido):
    """
    Genera un resumen ejecutivo del pedido
    """
    resumen = {
        'numero_pedido': pedido.numero_pedido,
        'cliente': pedido.cliente.razon_social,
        'estado': pedido.get_estado_display(),
        'prioridad': pedido.get_prioridad_display(),
        'fecha_pedido': pedido.fecha_pedido,
        'fecha_compromiso': pedido.fecha_compromiso,
        'valor_total': pedido.valor_total,
        'cantidad_lineas': pedido.lineas.count(),
        'cantidad_productos': sum(linea.cantidad for linea in pedido.lineas.all()),
        'porcentaje_avance': pedido.porcentaje_completado,
        'dias_vencimiento': calcular_dias_para_vencimiento(pedido.fecha_compromiso),
        'requiere_atencion': False
    }
    
    # Determinar si requiere atención especial
    if resumen['dias_vencimiento'] is not None:
        if resumen['dias_vencimiento'] < 0:
            resumen['requiere_atencion'] = True
            resumen['motivo_atencion'] = 'Pedido vencido'
        elif resumen['dias_vencimiento'] <= 3 and pedido.estado in ['CONFIRMADO', 'EN_PRODUCCION']:
            resumen['requiere_atencion'] = True
            resumen['motivo_atencion'] = 'Próximo a vencer'
    
    if pedido.prioridad == 'URGENTE':
        resumen['requiere_atencion'] = True
        resumen['motivo_atencion'] = 'Prioridad urgente'
    
    return resumen


def exportar_pedidos_csv(queryset):
    """
    Exporta un queryset de pedidos a formato CSV
    """
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Escribir encabezados
    headers = [
        'Número Pedido', 'Cliente', 'Estado', 'Prioridad',
        'Fecha Pedido', 'Fecha Compromiso', 'Valor Total',
        'Cantidad Líneas', 'Porcentaje Avance', 'Creado Por'
    ]
    writer.writerow(headers)
    
    # Escribir datos
    for pedido in queryset:
        row = [
            pedido.numero_pedido,
            pedido.cliente.razon_social,
            pedido.get_estado_display(),
            pedido.get_prioridad_display(),
            pedido.fecha_pedido.strftime('%d/%m/%Y'),
            pedido.fecha_compromiso.strftime('%d/%m/%Y') if pedido.fecha_compromiso else '',
            float(pedido.valor_total) if pedido.valor_total else 0,
            pedido.lineas.count(),
            pedido.porcentaje_completado,
            pedido.creado_por.get_full_name() or pedido.creado_por.username
        ]
        writer.writerow(row)
    
    return output.getvalue()


def obtener_alertas_pedidos():
    """
    Obtiene alertas importantes relacionadas con pedidos
    """
    alertas = []
    
    # Pedidos vencidos
    pedidos_vencidos = Pedido.objects.filter(
        fecha_compromiso__lt=date.today(),
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    ).count()
    
    if pedidos_vencidos > 0:
        alertas.append({
            'tipo': 'danger',
            'mensaje': f'Hay {pedidos_vencidos} pedido(s) vencido(s)',
            'icono': 'fas fa-exclamation-triangle',
            'url': '/pedidos/?vencidos=1'
        })
    
    # Pedidos próximos a vencer
    fecha_limite = date.today() + timezone.timedelta(days=3)
    pedidos_proximos = Pedido.objects.filter(
        fecha_compromiso__lte=fecha_limite,
        fecha_compromiso__gte=date.today(),
        estado__in=['CONFIRMADO', 'EN_PRODUCCION']
    ).count()
    
    if pedidos_proximos > 0:
        alertas.append({
            'tipo': 'warning',
            'mensaje': f'Hay {pedidos_proximos} pedido(s) que vencen en los próximos 3 días',
            'icono': 'fas fa-clock',
            'url': '/pedidos/?proximos=1'
        })
    
    # Pedidos urgentes sin avance
    pedidos_urgentes = Pedido.objects.filter(
        prioridad='URGENTE',
        estado='CONFIRMADO'
    ).count()
    
    if pedidos_urgentes > 0:
        alertas.append({
            'tipo': 'info',
            'mensaje': f'Hay {pedidos_urgentes} pedido(s) urgentes pendientes de iniciar producción',
            'icono': 'fas fa-bolt',
            'url': '/pedidos/?prioridad=URGENTE&estado=CONFIRMADO'
        })
    
    return alertas


def sincronizar_con_produccion(pedido):
    """
    Sincroniza el estado del pedido con el módulo de producción
    (Placeholder para integración futura)
    """
    # TODO: Implementar integración con módulo de producción
    pass


def notificar_cambio_estado(pedido, estado_anterior, estado_nuevo, usuario):
    """
    Envía notificaciones por cambio de estado
    (Placeholder para integración con módulo de notificaciones)
    """
    # TODO: Implementar integración con módulo de notificaciones
    pass


class PedidosUtils:
    """
    Clase de utilidades para el manejo de pedidos
    """
    
    @staticmethod
    def validar_pedido_completo(pedido):
        """
        Valida si un pedido está completo y listo para ser procesado
        """
        if not pedido.lineas.exists():
            return False, "El pedido no tiene líneas de detalle"
            
        if not pedido.cliente:
            return False, "El pedido no tiene un cliente asociado"
            
        return True, ""
    
    @staticmethod
    def calcular_tiempo_estimado(pedido):
        """
        Calcula el tiempo estimado de producción para un pedido
        """
        # Lógica para calcular tiempo estimado
        return timedelta(days=5)  # Valor por defecto


class NotificacionesPedidos:
    """
    Clase para manejar notificaciones relacionadas con pedidos
    """
    
    @staticmethod
    def enviar_notificacion_estado(pedido, estado_anterior, estado_nuevo, usuario):
        """
        Envía notificación de cambio de estado
        """
        # Lógica para enviar notificación
        pass
        
    @staticmethod
    def enviar_recordatorio_pendiente(pedido):
        """
        Envía recordatorio de pedido pendiente
        """
        # Lógica para enviar recordatorio
        pass