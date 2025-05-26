# pedidos/validators.py
"""
Validadores personalizados para el módulo de pedidos
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date, timedelta
from decimal import Decimal


def validar_fecha_compromiso(value):
    """Valida que la fecha de compromiso no sea en el pasado"""
    if value < date.today():
        raise ValidationError(
            _('La fecha de compromiso no puede ser anterior a hoy.'),
            code='fecha_pasado'
        )
    
    # Validar que no sea demasiado lejana (más de 2 años)
    fecha_maxima = date.today() + timedelta(days=730)
    if value > fecha_maxima:
        raise ValidationError(
            _('La fecha de compromiso no puede ser mayor a 2 años.'),
            code='fecha_muy_lejana'
        )


def validar_fecha_entrega(value):
    """Valida que la fecha de entrega sea válida"""
    if value and value < date.today():
        raise ValidationError(
            _('La fecha de entrega no puede ser anterior a hoy.'),
            code='fecha_entrega_pasado'
        )


def validar_numero_pedido(value):
    """Valida el formato del número de pedido"""
    import re
    
    # Formato esperado: PED-YYYY-NNNNNN
    patron = r'^PED-\d{4}-\d{6}$'
    
    if not re.match(patron, value):
        raise ValidationError(
            _('El número de pedido debe tener el formato PED-YYYY-NNNNNN'),
            code='formato_numero_invalido'
        )


def validar_cantidad_positiva(value):
    """Valida que la cantidad sea positiva"""
    if value <= 0:
        raise ValidationError(
            _('La cantidad debe ser mayor a cero.'),
            code='cantidad_no_positiva'
        )
    
    # Validar cantidad máxima razonable
    if value > 1000000:
        raise ValidationError(
            _('La cantidad no puede ser mayor a 1,000,000 unidades.'),
            code='cantidad_muy_alta'
        )


def validar_precio_positivo(value):
    """Valida que el precio sea positivo"""
    if value <= 0:
        raise ValidationError(
            _('El precio debe ser mayor a cero.'),
            code='precio_no_positivo'
        )
    
    # Validar precio máximo razonable (100 millones)
    if value > Decimal('100000000'):
        raise ValidationError(
            _('El precio no puede ser mayor a $100,000,000.'),
            code='precio_muy_alto'
        )


def validar_descuento(value):
    """Valida que el descuento esté en el rango válido"""
    if value < 0:
        raise ValidationError(
            _('El descuento no puede ser negativo.'),
            code='descuento_negativo'
        )
    
    if value > 100:
        raise ValidationError(
            _('El descuento no puede ser mayor al 100%.'),
            code='descuento_muy_alto'
        )


def validar_porcentaje_completado(value):
    """Valida que el porcentaje de completado esté en el rango válido"""
    if value < 0:
        raise ValidationError(
            _('El porcentaje completado no puede ser negativo.'),
            code='porcentaje_negativo'
        )
    
    if value > 100:
        raise ValidationError(
            _('El porcentaje completado no puede ser mayor al 100%.'),
            code='porcentaje_mayor_100'
        )


def validar_email_cliente(value):
    """Valida el formato del email del cliente"""
    import re
    
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if value and not re.match(patron, value):
        raise ValidationError(
            _('El formato del email no es válido.'),
            code='email_invalido'
        )


def validar_telefono_cliente(value):
    """Valida el formato del teléfono del cliente"""
    import re
    
    # Permitir números colombianos: +57, 3XX, XXX-XXXX
    patron = r'^(\+57\s?)?[3][0-9]{2}[\s-]?[0-9]{3}[\s-]?[0-9]{4}$'
    
    if value and not re.match(patron, value.replace(' ', '')):
        raise ValidationError(
            _('El formato del teléfono no es válido. Use formato: +57 3XX XXX XXXX'),
            code='telefono_invalido'
        )


def validar_nit_cliente(value):
    """Valida el formato del NIT del cliente"""
    import re
    
    if not value:
        return
    
    # Remover espacios y guiones
    nit_limpio = re.sub(r'[\s-]', '', value)
    
    # Validar que solo contenga números y opcionalmente un dígito verificador
    patron = r'^\d{8,15}-?\d?$'
    
    if not re.match(patron, nit_limpio):
        raise ValidationError(
            _('El formato del NIT no es válido.'),
            code='nit_invalido'
        )


def validar_observaciones_longitud(value):
    """Valida la longitud de las observaciones"""
    if value and len(value) > 1000:
        raise ValidationError(
            _('Las observaciones no pueden exceder 1000 caracteres.'),
            code='observaciones_muy_largas'
        )


def validar_especificaciones_tecnicas(value):
    """Valida las especificaciones técnicas"""
    if value and len(value) > 2000:
        raise ValidationError(
            _('Las especificaciones técnicas no pueden exceder 2000 caracteres.'),
            code='especificaciones_muy_largas'
        )


def validar_consistencia_fechas(fecha_pedido, fecha_compromiso, fecha_entrega=None):
    """Valida la consistencia entre las fechas del pedido"""
    errores = []
    
    if fecha_compromiso < fecha_pedido:
        errores.append(
            ValidationError(
                _('La fecha de compromiso no puede ser anterior a la fecha del pedido.'),
                code='fecha_compromiso_inconsistente'
            )
        )
    
    if fecha_entrega and fecha_entrega < fecha_pedido:
        errores.append(
            ValidationError(
                _('La fecha de entrega no puede ser anterior a la fecha del pedido.'),
                code='fecha_entrega_inconsistente'
            )
        )
    
    if fecha_entrega and fecha_compromiso and fecha_entrega < fecha_compromiso:
        errores.append(
            ValidationError(
                _('La fecha de entrega no puede ser anterior a la fecha de compromiso.'),
                code='fechas_entrega_compromiso_inconsistentes'
            )
        )
    
    if errores:
        raise ValidationError(errores)


def validar_estado_transicion(estado_actual, nuevo_estado):
    """Valida que la transición de estado sea permitida"""
    from .config import TRANSICIONES_ESTADO_PERMITIDAS
    
    transiciones_permitidas = TRANSICIONES_ESTADO_PERMITIDAS.get(estado_actual, [])
    
    if nuevo_estado not in transiciones_permitidas:
        raise ValidationError(
            _(f'No se puede cambiar el estado de {estado_actual} a {nuevo_estado}.'),
            code='transicion_estado_no_permitida'
        )


def validar_valor_total_consistente(lineas_pedido, valor_total):
    """Valida que el valor total sea consistente con las líneas del pedido"""
    if not lineas_pedido:
        return
    
    valor_calculado = sum(
        linea.cantidad * linea.precio_unitario * (1 - linea.descuento / 100)
        for linea in lineas_pedido
    )
    
    # Permitir una diferencia mínima por redondeos
    diferencia = abs(valor_total - valor_calculado)
    
    if diferencia > Decimal('0.01'):
        raise ValidationError(
            _('El valor total no coincide con la suma de las líneas del pedido.'),
            code='valor_total_inconsistente'
        )


def validar_capacidad_produccion(fecha_compromiso, cantidad_total):
    """Valida que la capacidad de producción sea suficiente"""
    # Esta validación debería considerar la capacidad de producción disponible
    # Por ahora, implementamos una validación básica
    
    # Capacidad máxima diaria (esto debería venir de configuración)
    CAPACIDAD_MAXIMA_DIARIA = 1000
    
    # Calcular días disponibles
    dias_disponibles = (fecha_compromiso - date.today()).days
    
    if dias_disponibles <= 0:
        raise ValidationError(
            _('No hay tiempo suficiente para cumplir con la fecha de compromiso.'),
            code='tiempo_insuficiente'
        )
    
    capacidad_disponible = CAPACIDAD_MAXIMA_DIARIA * dias_disponibles
    
    if cantidad_total > capacidad_disponible:
        raise ValidationError(
            _(f'La cantidad solicitada ({cantidad_total}) excede la capacidad de producción disponible ({capacidad_disponible}).'),
            code='capacidad_insuficiente'
        )


def validar_stock_disponible(producto, cantidad_solicitada):
    """Valida que haya stock suficiente del producto"""
    if hasattr(producto, 'stock_actual'):
        if producto.stock_actual < cantidad_solicitada:
            raise ValidationError(
                _(f'Stock insuficiente. Disponible: {producto.stock_actual}, Solicitado: {cantidad_solicitada}'),
                code='stock_insuficiente'
            )


def validar_cliente_activo(cliente):
    """Valida que el cliente esté activo"""
    if not cliente.activo:
        raise ValidationError(
            _('No se pueden crear pedidos para clientes inactivos.'),
            code='cliente_inactivo'
        )


def validar_producto_activo(producto):
    """Valida que el producto esté activo"""
    if not producto.activo:
        raise ValidationError(
            _('No se pueden agregar productos inactivos al pedido.'),
            code='producto_inactivo'
        )


def validar_precio_dentro_rango(precio_unitario, producto):
    """Valida que el precio esté dentro del rango permitido para el producto"""
    if hasattr(producto, 'precio_minimo') and producto.precio_minimo:
        if precio_unitario < producto.precio_minimo:
            raise ValidationError(
                _(f'El precio no puede ser menor al precio mínimo: ${producto.precio_minimo}'),
                code='precio_menor_minimo'
            )
    
    if hasattr(producto, 'precio_maximo') and producto.precio_maximo:
        if precio_unitario > producto.precio_maximo:
            raise ValidationError(
                _(f'El precio no puede ser mayor al precio máximo: ${producto.precio_maximo}'),
                code='precio_mayor_maximo'
            )


class ValidadorPedidoCompleto:
    """Validador completo para un pedido con todas sus líneas"""
    
    def __init__(self, pedido):
        self.pedido = pedido
        self.errores = []
    
    def validar_todo(self):
        """Ejecuta todas las validaciones del pedido"""
        self.validar_fechas()
        self.validar_cliente()
        self.validar_lineas()
        self.validar_valores()
        self.validar_capacidad()
        
        if self.errores:
            raise ValidationError(self.errores)
    
    def validar_fechas(self):
        """Valida todas las fechas del pedido"""
        try:
            validar_consistencia_fechas(
                self.pedido.fecha_pedido,
                self.pedido.fecha_compromiso,
                self.pedido.fecha_entrega
            )
        except ValidationError as e:
            self.errores.extend(e.error_list if hasattr(e, 'error_list') else [e])
    
    def validar_cliente(self):
        """Valida el cliente del pedido"""
        try:
            validar_cliente_activo(self.pedido.cliente)
        except ValidationError as e:
            self.errores.append(e)
    
    def validar_lineas(self):
        """Valida todas las líneas del pedido"""
        if not self.pedido.lineas.exists():
            self.errores.append(
                ValidationError(
                    _('El pedido debe tener al menos una línea.'),
                    code='sin_lineas'
                )
            )
            return
        
        for linea in self.pedido.lineas.all():
            try:
                validar_producto_activo(linea.producto)
                validar_cantidad_positiva(linea.cantidad)
                validar_precio_positivo(linea.precio_unitario)
                validar_precio_dentro_rango(linea.precio_unitario, linea.producto)
                validar_stock_disponible(linea.producto, linea.cantidad)
            except ValidationError as e:
                self.errores.append(e)
    
    def validar_valores(self):
        """Valida los valores monetarios del pedido"""
        try:
            validar_valor_total_consistente(
                self.pedido.lineas.all(),
                self.pedido.valor_total
            )
        except ValidationError as e:
            self.errores.append(e)
    
    def validar_capacidad(self):
        """Valida la capacidad de producción"""
        cantidad_total = sum(
            linea.cantidad for linea in self.pedido.lineas.all()
        )
        
        try:
            validar_capacidad_produccion(
                self.pedido.fecha_compromiso,
                cantidad_total
            )
        except ValidationError as e:
            self.errores.append(e)


# Funciones utilitarias para validaciones
def es_fecha_habil(fecha):
    """Verifica si una fecha es día hábil (lunes a viernes)"""
    return fecha.weekday() < 5


def calcular_fecha_habil_siguiente(fecha):
    """Calcula la siguiente fecha hábil"""
    while not es_fecha_habil(fecha):
        fecha += timedelta(days=1)
    return fecha


def validar_fecha_habil(value):
    """Valida que la fecha sea un día hábil"""
    if not es_fecha_habil(value):
        fecha_sugerida = calcular_fecha_habil_siguiente(value)
        raise ValidationError(
            _(f'La fecha debe ser un día hábil. Fecha hábil más cercana: {fecha_sugerida}'),
            code='fecha_no_habil'
        )