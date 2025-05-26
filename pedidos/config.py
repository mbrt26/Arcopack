# pedidos/config.py
"""
Configuraciones y constantes para el módulo de pedidos
"""

# Estados del pedido y sus transiciones permitidas
ESTADOS_PEDIDO = [
    ('BORRADOR', 'Borrador'),
    ('CONFIRMADO', 'Confirmado'),
    ('EN_PRODUCCION', 'En Producción'),
    ('PRODUCIDO', 'Producido'),
    ('PENDIENTE_FACTURAR', 'Pendiente Facturar'),
    ('FACTURADO', 'Facturado'),
    ('ENTREGADO', 'Entregado'),
    ('CANCELADO', 'Cancelado'),
]

# Prioridades del pedido
PRIORIDADES_PEDIDO = [
    ('BAJA', 'Baja'),
    ('NORMAL', 'Normal'),
    ('ALTA', 'Alta'),
    ('URGENTE', 'Urgente'),
]

# Transiciones de estado permitidas
TRANSICIONES_ESTADO = {
    'BORRADOR': ['CONFIRMADO', 'CANCELADO'],
    'CONFIRMADO': ['EN_PRODUCCION', 'CANCELADO'],
    'EN_PRODUCCION': ['PRODUCIDO', 'CANCELADO'],
    'PRODUCIDO': ['PENDIENTE_FACTURAR', 'FACTURADO'],
    'PENDIENTE_FACTURAR': ['FACTURADO'],
    'FACTURADO': ['ENTREGADO'],
    'ENTREGADO': [],  # Estado final
    'CANCELADO': []   # Estado final
}

# Configuración de colores para estados (para UI)
COLORES_ESTADO = {
    'BORRADOR': '#6c757d',      # Gris
    'CONFIRMADO': '#007bff',    # Azul
    'EN_PRODUCCION': '#ffc107', # Amarillo
    'PRODUCIDO': '#28a745',     # Verde
    'PENDIENTE_FACTURAR': '#fd7e14',  # Naranja
    'FACTURADO': '#20c997',     # Verde azulado
    'ENTREGADO': '#198754',     # Verde oscuro
    'CANCELADO': '#dc3545'      # Rojo
}

# Configuración de colores para prioridades
COLORES_PRIORIDAD = {
    'BAJA': '#6c757d',      # Gris
    'NORMAL': '#007bff',    # Azul
    'ALTA': '#ffc107',      # Amarillo
    'URGENTE': '#dc3545'    # Rojo
}

# Configuración de notificaciones por estado
NOTIFICACIONES_CONFIG = {
    'CONFIRMADO': {
        'grupos': ['produccion', 'administracion'],
        'asunto': 'Nuevo pedido confirmado para producción',
        'plantilla': 'pedidos/emails/pedido_confirmado.html'
    },
    'EN_PRODUCCION': {
        'grupos': ['ventas', 'administracion'],
        'asunto': 'Pedido iniciado en producción',
        'plantilla': 'pedidos/emails/pedido_en_produccion.html'
    },
    'PRODUCIDO': {
        'grupos': ['facturacion', 'administracion'],
        'asunto': 'Pedido completado - Listo para facturar',
        'plantilla': 'pedidos/emails/pedido_producido.html'
    },
    'FACTURADO': {
        'grupos': ['ventas', 'despacho'],
        'asunto': 'Pedido facturado - Listo para despacho',
        'plantilla': 'pedidos/emails/pedido_facturado.html'
    },
    'ENTREGADO': {
        'grupos': ['ventas', 'administracion'],
        'asunto': 'Pedido entregado exitosamente',
        'plantilla': 'pedidos/emails/pedido_entregado.html'
    },
    'CANCELADO': {
        'grupos': ['ventas', 'administracion'],
        'asunto': 'Pedido cancelado',
        'plantilla': 'pedidos/emails/pedido_cancelado.html'
    }
}

# Configuración de reportes
REPORTES_CONFIG = {
    'pedidos_por_estado': {
        'nombre': 'Pedidos por Estado',
        'descripcion': 'Reporte de pedidos agrupados por estado',
        'campos': ['numero_pedido', 'cliente', 'estado', 'fecha_pedido', 'valor_total']
    },
    'pedidos_vencidos': {
        'nombre': 'Pedidos Vencidos',
        'descripcion': 'Pedidos que han superado su fecha de compromiso',
        'campos': ['numero_pedido', 'cliente', 'fecha_compromiso', 'dias_vencido', 'valor_total']
    },
    'resumen_mensual': {
        'nombre': 'Resumen Mensual',
        'descripcion': 'Resumen de pedidos por mes',
        'campos': ['mes', 'cantidad_pedidos', 'valor_total', 'promedio_pedido']
    },
    'top_clientes': {
        'nombre': 'Top Clientes',
        'descripcion': 'Clientes con mayor valor en pedidos',
        'campos': ['cliente', 'cantidad_pedidos', 'valor_total', 'promedio_pedido']
    }
}

# Configuración de alertas
ALERTAS_CONFIG = {
    'dias_vencimiento_critico': 3,      # Días antes del vencimiento para alerta crítica
    'dias_vencimiento_advertencia': 7,  # Días antes del vencimiento para advertencia
    'porcentaje_avance_minimo': 10,     # Porcentaje mínimo de avance esperado por semana
    'valor_pedido_alto': 10000000,      # Valor en pesos para considerar pedido de valor alto
}

# Configuración de formatos
FORMATOS_CONFIG = {
    'numero_pedido': 'PED-{year}-{number:04d}',
    'fecha_display': '%d/%m/%Y',
    'fecha_hora_display': '%d/%m/%Y %H:%M',
    'moneda_display': '${:,.0f}',
    'porcentaje_display': '{:.1f}%'
}

# Configuración de paginación
PAGINACION_CONFIG = {
    'pedidos_por_pagina': 25,
    'lineas_por_pagina': 50,
    'reportes_por_pagina': 100
}

# Configuración de exportación
EXPORTACION_CONFIG = {
    'formatos_permitidos': ['csv', 'xlsx', 'pdf'],
    'max_registros_csv': 10000,
    'max_registros_xlsx': 50000,
    'campos_exportacion_basica': [
        'numero_pedido', 'cliente', 'estado', 'prioridad',
        'fecha_pedido', 'fecha_compromiso', 'valor_total'
    ],
    'campos_exportacion_completa': [
        'numero_pedido', 'cliente', 'estado', 'prioridad',
        'fecha_pedido', 'fecha_compromiso', 'valor_total',
        'observaciones', 'creado_por', 'fecha_creacion',
        'actualizado_por', 'fecha_actualizacion'
    ]
}

# Configuración de validaciones
VALIDACIONES_CONFIG = {
    'valor_minimo_pedido': 10000,       # Valor mínimo en pesos
    'valor_maximo_pedido': 500000000,   # Valor máximo en pesos
    'dias_maximos_compromiso': 365,     # Días máximos para fecha de compromiso
    'cantidad_maxima_lineas': 100,      # Máximo número de líneas por pedido
    'cantidad_maxima_producto': 999999, # Cantidad máxima por producto
}

# Configuración de integración con otros módulos
INTEGRACION_CONFIG = {
    'inventario': {
        'validar_stock': True,
        'reservar_automatico': False,
        'actualizar_disponibilidad': True
    },
    'produccion': {
        'crear_op_automatica': False,
        'sincronizar_estados': True,
        'notificar_cambios': True
    },
    'facturacion': {
        'crear_factura_automatica': False,
        'validar_datos_facturacion': True,
        'enviar_por_email': False
    },
    'contabilidad': {
        'generar_asientos': False,
        'validar_centros_costo': True
    }
}

# Mensajes del sistema
MENSAJES_SISTEMA = {
    'pedido_creado': 'El pedido {numero_pedido} ha sido creado exitosamente.',
    'pedido_actualizado': 'El pedido {numero_pedido} ha sido actualizado.',
    'estado_cambiado': 'El estado del pedido {numero_pedido} ha cambiado de {estado_anterior} a {estado_nuevo}.',
    'pedido_cancelado': 'El pedido {numero_pedido} ha sido cancelado.',
    'error_transicion': 'No es posible cambiar del estado {estado_actual} a {estado_nuevo}.',
    'error_validacion': 'Error de validación: {detalle}',
    'sin_permisos': 'No tiene permisos para realizar esta acción.',
    'pedido_no_encontrado': 'El pedido solicitado no existe.',
    'cliente_inactivo': 'No se puede crear pedidos para clientes inactivos.',
    'producto_no_disponible': 'El producto {producto} no está disponible.',
    'stock_insuficiente': 'Stock insuficiente para el producto {producto}. Disponible: {disponible}, Solicitado: {solicitado}.'
}

# Configuración de campos requeridos por estado
CAMPOS_REQUERIDOS_POR_ESTADO = {
    'CONFIRMADO': ['fecha_compromiso'],
    'FACTURADO': ['numero_factura', 'fecha_factura'],
    'ENTREGADO': ['fecha_entrega', 'entregado_por'],
}

# Configuración de permisos
PERMISOS_CONFIG = {
    'crear_pedido': 'pedidos.add_pedido',
    'ver_pedido': 'pedidos.view_pedido',
    'editar_pedido': 'pedidos.change_pedido',
    'eliminar_pedido': 'pedidos.delete_pedido',
    'cambiar_estado': 'pedidos.change_estado_pedido',
    'generar_reportes': 'pedidos.generate_reports',
    'exportar_datos': 'pedidos.export_data',
    'ver_dashboard': 'pedidos.view_dashboard',
}

# Configuración de logging
LOGGING_CONFIG = {
    'log_creacion': True,
    'log_actualizacion': True,
    'log_eliminacion': True,
    'log_cambio_estado': True,
    'log_exportacion': True,
    'log_reportes': True,
    'nivel_log': 'INFO'
}