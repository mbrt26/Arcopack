# produccion/services.py

import logging
from decimal import Decimal
from typing import Union
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import Max

# --- Importar modelos necesarios ---
from inventario.models import LoteMateriaPrima, LoteProductoEnProceso, LoteProductoTerminado, MovimientoInventario, Tinta
from .models import OrdenProduccion, RegistroImpresion, Refilado, Sellado, Doblado
from configuracion.models import Ubicacion, UnidadMedida, Proceso
from productos.models import ProductoTerminado
# from personal.models import Colaborador # Necesario si se usa en type hints o lógica

User = get_user_model()
logger = logging.getLogger(__name__) # Configura logging en settings.py

# =============================================
# === HELPER FUNCTION FOR WIP/PT DECISION ===
# =============================================

def es_ultimo_proceso_op(orden_produccion: OrdenProduccion, nombre_proceso_actual: str) -> bool:
    """
    Verifica si un proceso dado es el último en la secuencia definida
    para una Orden de Producción específica, basado en orden_flujo.
    """
    if not orden_produccion:
        logger.error("Error en es_ultimo_proceso_op: Se recibió orden_produccion None.")
        return False # No se puede determinar sin OP

    try:
        proceso_actual_obj = Proceso.objects.get(nombre__iexact=nombre_proceso_actual) # Usar iexact
        procesos_requeridos = orden_produccion.procesos.all()

        if procesos_requeridos.exists():
            max_orden_flujo = procesos_requeridos.aggregate(max_orden=Max('orden_flujo'))['max_orden']
            if proceso_actual_obj.orden_flujo == max_orden_flujo:
                logger.debug(f"Proceso '{nombre_proceso_actual}' (Orden: {proceso_actual_obj.orden_flujo}) es el último para OP {orden_produccion.op_numero} (Max Orden: {max_orden_flujo}).")
                return True
            else:
                logger.debug(f"Proceso '{nombre_proceso_actual}' (Orden: {proceso_actual_obj.orden_flujo}) NO es el último para OP {orden_produccion.op_numero} (Max Orden: {max_orden_flujo}).")
                return False
        else:
            logger.warning(f"OP {orden_produccion.op_numero} no tiene procesos definidos en el campo 'procesos'. Asumiendo que '{nombre_proceso_actual}' no es el último.")
            return False
    except Proceso.DoesNotExist:
         logger.error(f"Error crítico: Proceso con nombre '{nombre_proceso_actual}' no encontrado en configuración.")
         return False
    except Exception as e:
         logger.error(f"Error inesperado determinando último proceso ('{nombre_proceso_actual}') para OP {orden_produccion.op_numero}: {e}")
         return False

# =============================================
# === FUNCIONES PARA IMPRESIÓN ===
# =============================================

@transaction.atomic
def consumir_sustrato_impresion(
    *,
    registro_impresion: RegistroImpresion,
    lote_sustrato_id: str,
    cantidad_kg: Decimal,
    usuario: User
) -> LoteMateriaPrima:
    """Consume Lote MP (sustrato) para Impresión."""
    if cantidad_kg <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    logger.info(f"Consumiendo {cantidad_kg} Kg Lote MP '{lote_sustrato_id}' para Impresión ID {registro_impresion.id} por Usuario ID {usuario.id}")
    try: lote_a_consumir = LoteMateriaPrima.objects.select_for_update().get(lote_id=lote_sustrato_id)
    except LoteMateriaPrima.DoesNotExist: msg = f"Lote Materia Prima '{lote_sustrato_id}' no encontrado."; logger.error(msg); raise ValidationError(msg)
    try: lote_a_consumir.consumir(cantidad_consumir=cantidad_kg, proceso_ref=registro_impresion, usuario=usuario)
    except (ValidationError, ValueError) as e: logger.error(f"Error al consumir Lote MP '{lote_sustrato_id}': {e}"); raise e
    logger.info(f"Consumo exitoso Lote MP '{lote_sustrato_id}'. Restante: {lote_a_consumir.cantidad_actual}")
    return lote_a_consumir

@transaction.atomic
def registrar_produccion_rollo_impreso(
    *, registro_impresion: RegistroImpresion, lote_salida_id: str, kg_producidos: Decimal,
    metros_producidos: Decimal = None, ubicacion_destino_codigo: str, usuario: User,
    observaciones_lote: str = ""
) -> Union[LoteProductoEnProceso, LoteProductoTerminado]:
    """Crea Lote WIP o PT (rollo impreso) y registra movimiento."""
    if kg_producidos <= 0: raise ValueError("Kg producidos deben ser positivos.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    if not registro_impresion or not registro_impresion.pk: raise ValueError("Registro inválido.")
    logger.info(f"Registrando producción {kg_producidos} Kg (ID: {lote_salida_id}) para Impresión ID {registro_impresion.id} por Usuario ID {usuario.id}")
    try:
        ubicacion_destino = Ubicacion.objects.get(codigo=ubicacion_destino_codigo, is_active=True)
        unidad_kg = UnidadMedida.objects.get(codigo='Kg')
        unidad_m = UnidadMedida.objects.get(codigo='m') if metros_producidos is not None else None
        orden_produccion = registro_impresion.orden_produccion
        producto_terminado = orden_produccion.producto
        if not orden_produccion or not producto_terminado: raise ValueError("OP o Producto inválido.")
    except ObjectDoesNotExist as e: msg = f"Error obteniendo datos relacionados: {e}"; logger.error(msg); raise ValidationError(msg)

    es_ultimo_paso = es_ultimo_proceso_op(orden_produccion, 'Impresión') # Asume nombre del proceso
    ct_registro = ContentType.objects.get_for_model(registro_impresion) # Obtener ContentType

    if es_ultimo_paso:
        if LoteProductoTerminado.objects.filter(lote_id=lote_salida_id).exists(): raise ValidationError(f"ID Lote PT '{lote_salida_id}' ya existe.")
        unidad_pt = producto_terminado.unidad_medida
        if unidad_pt.codigo != 'Kg': logger.warning(f"Producción Impresión PT en Kg, pero unidad producto es {unidad_pt.codigo}.")
        nuevo_lote_pt = LoteProductoTerminado.objects.create(
            lote_id=lote_salida_id, producto_terminado=producto_terminado, orden_produccion=orden_produccion,
            proceso_final_content_type=ct_registro, proceso_final_object_id=registro_impresion.pk,
            cantidad_producida=kg_producidos, cantidad_actual=kg_producidos,
            ubicacion=ubicacion_destino, estado='DISPONIBLE', fecha_produccion=timezone.now(),
            observaciones=observaciones_lote, creado_por=usuario, actualizado_por=usuario)
        nuevo_lote_pt.registrar_movimiento(tipo_movimiento='PRODUCCION_PT', cantidad=kg_producidos, usuario=usuario, ubicacion_destino=ubicacion_destino, proceso_referencia=registro_impresion, observaciones=f"Producción Impresión (PT) {registro_impresion.id}")
        logger.info(f"Lote PT (Impresión) '{lote_salida_id}' creado ({kg_producidos} Kg).")
        return nuevo_lote_pt
    else:
        if LoteProductoEnProceso.objects.filter(lote_id=lote_salida_id).exists(): raise ValidationError(f"ID Lote WIP '{lote_salida_id}' ya existe.")
        nuevo_lote_wip = LoteProductoEnProceso.objects.create(
            lote_id=lote_salida_id, producto_terminado=producto_terminado, orden_produccion=orden_produccion,
            proceso_origen_content_type=ct_registro, proceso_origen_object_id=registro_impresion.pk,
            cantidad_producida_primaria=kg_producidos, unidad_medida_primaria=unidad_kg,
            cantidad_producida_secundaria=metros_producidos, unidad_medida_secundaria=unidad_m,
            cantidad_actual=kg_producidos, ubicacion=ubicacion_destino, estado='DISPONIBLE',
            fecha_produccion=timezone.now(), observaciones=observaciones_lote,
            creado_por=usuario, actualizado_por=usuario)
        nuevo_lote_wip.registrar_movimiento(tipo_movimiento='PRODUCCION_WIP', cantidad=kg_producidos, usuario=usuario, ubicacion_destino=ubicacion_destino, proceso_referencia=registro_impresion, observaciones=f"Producción Impresión (WIP) {registro_impresion.id}")
        logger.info(f"Lote WIP (Impresión) '{lote_salida_id}' creado ({kg_producidos} Kg).")
        return nuevo_lote_wip

# =============================================
# === FUNCIONES PARA REFILADO ===
# =============================================

@transaction.atomic
def consumir_rollo_entrada_refilado(*, refilado: Refilado, lote_entrada_id: str, cantidad_kg: Decimal, usuario: User) -> LoteProductoEnProceso:
    """Consume Lote WIP para Refilado."""
    if cantidad_kg <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    logger.info(f"Consumiendo {cantidad_kg} Kg Lote WIP '{lote_entrada_id}' para Refilado ID {refilado.id} por Usuario ID {usuario.id}")
    try: lote_a_consumir = LoteProductoEnProceso.objects.select_for_update().get(lote_id=lote_entrada_id)
    except LoteProductoEnProceso.DoesNotExist: msg = f"Lote WIP entrada '{lote_entrada_id}' no encontrado."; logger.error(msg); raise ValidationError(msg)
    try: lote_a_consumir.consumir(cantidad_consumir=cantidad_kg, proceso_ref=refilado, usuario=usuario)
    except (ValidationError, ValueError) as e: logger.error(f"Error al consumir Lote WIP '{lote_entrada_id}': {e}"); raise e
    logger.info(f"Consumo exitoso Lote WIP '{lote_entrada_id}'. Restante: {lote_a_consumir.cantidad_actual}")
    return lote_a_consumir

@transaction.atomic
def consumir_mp_refilado(*, refilado: Refilado, lote_mp_id: str, cantidad_consumida: Decimal, usuario: User) -> LoteMateriaPrima:
    """Consume Lote MP (ej: core) para Refilado."""
    if cantidad_consumida <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    logger.info(f"Consumiendo {cantidad_consumida} Lote MP '{lote_mp_id}' para Refilado ID {refilado.id} por Usuario ID {usuario.id}")
    try: lote_a_consumir = LoteMateriaPrima.objects.select_for_update().get(lote_id=lote_mp_id)
    except LoteMateriaPrima.DoesNotExist: msg = f"Lote MP '{lote_mp_id}' no encontrado."; logger.error(msg); raise ValidationError(msg)
    try: lote_a_consumir.consumir(cantidad_consumir=cantidad_consumida, proceso_ref=refilado, usuario=usuario)
    except (ValidationError, ValueError) as e: logger.error(f"Error al consumir Lote MP '{lote_mp_id}': {e}"); raise e
    logger.info(f"Consumo exitoso Lote MP '{lote_mp_id}'. Restante: {lote_a_consumir.cantidad_actual}")
    return lote_a_consumir

@transaction.atomic
def registrar_produccion_rollo_refilado(
    *, refilado: Refilado, lote_salida_id: str, kg_producidos: Decimal,
    metros_producidos: Decimal = None, ubicacion_destino_codigo: str, usuario: User,
    observaciones_lote: str = ""
) -> Union[LoteProductoEnProceso, LoteProductoTerminado]:
    """Crea Lote WIP o PT (rollo refilado) y registra movimiento."""
    if kg_producidos <= 0: raise ValueError("Kg producidos deben ser positivos.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    if not refilado or not refilado.pk: raise ValueError("Registro de Refilado inválido.")
    logger.info(f"Registrando producción {kg_producidos} Kg (ID: {lote_salida_id}) para Refilado ID {refilado.id} por Usuario ID {usuario.id}")
    try:
        ubicacion_destino = Ubicacion.objects.get(codigo=ubicacion_destino_codigo, is_active=True)
        unidad_kg = UnidadMedida.objects.get(codigo='Kg')
        unidad_m = UnidadMedida.objects.get(codigo='m') if metros_producidos is not None else None
        orden_produccion = refilado.orden_produccion
        producto_terminado = orden_produccion.producto
        if not orden_produccion or not producto_terminado: raise ValueError("OP o Producto inválido.")
    except ObjectDoesNotExist as e: msg = f"Error obteniendo datos relacionados: {e}"; logger.error(msg); raise ValidationError(msg)

    es_ultimo_paso = es_ultimo_proceso_op(orden_produccion, 'Refilado')
    ct_registro = ContentType.objects.get_for_model(refilado)

    if es_ultimo_paso:
        if LoteProductoTerminado.objects.filter(lote_id=lote_salida_id).exists(): raise ValidationError(f"ID Lote PT '{lote_salida_id}' ya existe.")
        unidad_pt = producto_terminado.unidad_medida
        if unidad_pt.codigo != 'Kg': logger.warning(f"Producción Refilado PT en Kg, pero unidad producto es {unidad_pt.codigo}.")
        nuevo_lote_pt = LoteProductoTerminado.objects.create(
            lote_id=lote_salida_id, producto_terminado=producto_terminado, orden_produccion=orden_produccion,
            proceso_final_content_type=ct_registro, proceso_final_object_id=refilado.pk,
            cantidad_producida=kg_producidos, cantidad_actual=kg_producidos,
            ubicacion=ubicacion_destino, estado='DISPONIBLE', fecha_produccion=timezone.now(),
            observaciones=observaciones_lote, creado_por=usuario, actualizado_por=usuario)
        nuevo_lote_pt.registrar_movimiento(tipo_movimiento='PRODUCCION_PT', cantidad=kg_producidos, usuario=usuario, ubicacion_destino=ubicacion_destino, proceso_referencia=refilado, observaciones=f"Producción Refilado (PT) {refilado.id}")
        logger.info(f"Lote PT (Refilado) '{lote_salida_id}' creado ({kg_producidos} Kg).")
        return nuevo_lote_pt
    else:
        if LoteProductoEnProceso.objects.filter(lote_id=lote_salida_id).exists(): raise ValidationError(f"ID Lote WIP '{lote_salida_id}' ya existe.")
        nuevo_lote_wip = LoteProductoEnProceso.objects.create(
            lote_id=lote_salida_id, producto_terminado=producto_terminado, orden_produccion=orden_produccion,
            proceso_origen_content_type=ct_registro, proceso_origen_object_id=refilado.pk,
            cantidad_producida_primaria=kg_producidos, unidad_medida_primaria=unidad_kg,
            cantidad_producida_secundaria=metros_producidos, unidad_medida_secundaria=unidad_m,
            cantidad_actual=kg_producidos, ubicacion=ubicacion_destino, estado='DISPONIBLE',
            fecha_produccion=timezone.now(), observaciones=observaciones_lote,
            creado_por=usuario, actualizado_por=usuario)
        nuevo_lote_wip.registrar_movimiento(tipo_movimiento='PRODUCCION_WIP', cantidad=kg_producidos, usuario=usuario, ubicacion_destino=ubicacion_destino, proceso_referencia=refilado, observaciones=f"Producción Refilado (WIP) {refilado.id}")
        logger.info(f"Lote WIP (Refilado) '{lote_salida_id}' creado ({kg_producidos} Kg).")
        return nuevo_lote_wip

# =============================================
# === FUNCIONES PARA SELLADO ===
# =============================================

@transaction.atomic
def consumir_rollo_entrada_sellado(*, sellado: Sellado, lote_entrada_id: str, cantidad_kg: Decimal, usuario: User) -> LoteProductoEnProceso:
    """Consume Lote WIP para Sellado."""
    if cantidad_kg <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    logger.info(f"Consumiendo {cantidad_kg} Kg Lote WIP '{lote_entrada_id}' para Sellado ID {sellado.id} por Usuario ID {usuario.id}")
    try: lote_a_consumir = LoteProductoEnProceso.objects.select_for_update().get(lote_id=lote_entrada_id)
    except LoteProductoEnProceso.DoesNotExist: msg = f"Lote WIP entrada '{lote_entrada_id}' no encontrado."; logger.error(msg); raise ValidationError(msg)
    try: lote_a_consumir.consumir(cantidad_consumir=cantidad_kg, proceso_ref=sellado, usuario=usuario)
    except (ValidationError, ValueError) as e: logger.error(f"Error al consumir Lote WIP '{lote_entrada_id}': {e}"); raise e
    logger.info(f"Consumo exitoso Lote WIP '{lote_entrada_id}'. Restante: {lote_a_consumir.cantidad_actual}")
    return lote_a_consumir

@transaction.atomic
def consumir_mp_sellado(*, sellado: Sellado, lote_mp_id: str, cantidad_consumida: Decimal, usuario: User) -> LoteMateriaPrima:
    """Consume Lote MP (ej: zipper, válvula) para Sellado."""
    if cantidad_consumida <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    logger.info(f"Consumiendo {cantidad_consumida} Lote MP '{lote_mp_id}' para Sellado ID {sellado.id} por Usuario ID {usuario.id}")
    try: lote_a_consumir = LoteMateriaPrima.objects.select_for_update().get(lote_id=lote_mp_id)
    except LoteMateriaPrima.DoesNotExist: msg = f"Lote MP '{lote_mp_id}' no encontrado."; logger.error(msg); raise ValidationError(msg)
    try: lote_a_consumir.consumir(cantidad_consumir=cantidad_consumida, proceso_ref=sellado, usuario=usuario)
    except (ValidationError, ValueError) as e: logger.error(f"Error al consumir Lote MP '{lote_mp_id}': {e}"); raise e
    logger.info(f"Consumo exitoso Lote MP '{lote_mp_id}'. Restante: {lote_a_consumir.cantidad_actual}")
    return lote_a_consumir

@transaction.atomic
def registrar_produccion_bolsas_sellado(
    *, sellado: Sellado, lote_salida_id: str, unidades_producidas: int,
    ubicacion_destino_codigo: str, usuario: User, observaciones_lote: str = ""
) -> Union[LoteProductoEnProceso, LoteProductoTerminado]:
    """Crea Lote PT o WIP (bolsas selladas) y registra movimiento."""
    if unidades_producidas <= 0: raise ValueError("Unidades producidas deben ser positivas.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    if not sellado or not sellado.pk: raise ValueError("Registro de Sellado inválido.")
    logger.info(f"Registrando producción {unidades_producidas} Unid (ID: {lote_salida_id}) para Sellado ID {sellado.id} por Usuario ID {usuario.id}")
    try:
        ubicacion_destino = Ubicacion.objects.get(codigo=ubicacion_destino_codigo, is_active=True)
        orden_produccion = sellado.orden_produccion
        producto_terminado = orden_produccion.producto
        unidad_pt = producto_terminado.unidad_medida
        if not orden_produccion or not producto_terminado or not unidad_pt: raise ValueError("OP, Producto o Unidad PT inválido.")
    except ObjectDoesNotExist as e: msg = f"Error obteniendo datos relacionados: {e}"; logger.error(msg); raise ValidationError(msg)

    es_ultimo_paso = es_ultimo_proceso_op(orden_produccion, 'Sellado')
    ct_registro = ContentType.objects.get_for_model(sellado)

    if es_ultimo_paso:
        if LoteProductoTerminado.objects.filter(lote_id=lote_salida_id).exists(): raise ValidationError(f"ID Lote PT '{lote_salida_id}' ya existe.")
        kg_calculados = None
        if producto_terminado.sellado_peso_millar and producto_terminado.sellado_peso_millar > 0: kg_calculados = round(Decimal(unidades_producidas / 1000) * producto_terminado.sellado_peso_millar, 4)
        nuevo_lote_pt = LoteProductoTerminado.objects.create(
            lote_id=lote_salida_id, producto_terminado=producto_terminado, orden_produccion=orden_produccion,
            proceso_final_content_type=ct_registro, proceso_final_object_id=sellado.pk,
            cantidad_producida=unidades_producidas, cantidad_actual=unidades_producidas,
            ubicacion=ubicacion_destino, estado='DISPONIBLE', fecha_produccion=timezone.now(),
            observaciones=observaciones_lote, creado_por=usuario, actualizado_por=usuario)
        nuevo_lote_pt.registrar_movimiento(tipo_movimiento='PRODUCCION_PT', cantidad=unidades_producidas, usuario=usuario, ubicacion_destino=ubicacion_destino, proceso_referencia=sellado, observaciones=f"Producción Sellado (PT) {sellado.id}")
        logger.info(f"Lote PT (Sellado) '{lote_salida_id}' creado ({unidades_producidas} {unidad_pt.codigo}). Kg calc: {kg_calculados or 'N/A'}")
        return nuevo_lote_pt
    else:
        if LoteProductoEnProceso.objects.filter(lote_id=lote_salida_id).exists(): raise ValidationError(f"ID Lote WIP '{lote_salida_id}' ya existe.")
        try: unidad_unid = UnidadMedida.objects.get(codigo='Unid'); unidad_kg = UnidadMedida.objects.get(codigo='Kg')
        except UnidadMedida.DoesNotExist: raise RuntimeError("Unidad 'Unid' o 'Kg' no encontrada.")
        kg_calculados = None
        if producto_terminado.sellado_peso_millar and producto_terminado.sellado_peso_millar > 0: kg_calculados = round(Decimal(unidades_producidas / 1000) * producto_terminado.sellado_peso_millar, 4)
        nuevo_lote_wip = LoteProductoEnProceso.objects.create(
            lote_id=lote_salida_id, producto_terminado=producto_terminado, orden_produccion=orden_produccion,
            proceso_origen_content_type=ct_registro, proceso_origen_object_id=sellado.pk,
            cantidad_producida_primaria=unidades_producidas, unidad_medida_primaria=unidad_unid,
            cantidad_producida_secundaria=kg_calculados, unidad_medida_secundaria=unidad_kg if kg_calculados else None,
            cantidad_actual=unidades_producidas, ubicacion=ubicacion_destino, estado='DISPONIBLE',
            fecha_produccion=timezone.now(), observaciones=observaciones_lote,
            creado_por=usuario, actualizado_por=usuario)
        nuevo_lote_wip.registrar_movimiento(tipo_movimiento='PRODUCCION_WIP', cantidad=unidades_producidas, usuario=usuario, ubicacion_destino=ubicacion_destino, proceso_referencia=sellado, observaciones=f"Producción Sellado (WIP) {sellado.id}")
        logger.info(f"Lote WIP (Sellado) '{lote_salida_id}' creado ({unidades_producidas} {unidad_unid.codigo}).")
        return nuevo_lote_wip

# =============================================
# === FUNCIONES PARA DOBLADO ===
# =============================================

@transaction.atomic
def consumir_rollo_entrada_doblado(*, doblado: Doblado, lote_entrada_id: str, cantidad_kg: Decimal, usuario: User) -> LoteProductoEnProceso:
    """Consume Lote WIP para Doblado."""
    if cantidad_kg <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    logger.info(f"Consumiendo {cantidad_kg} Kg Lote WIP '{lote_entrada_id}' para Doblado ID {doblado.id} por Usuario ID {usuario.id}")
    try: lote_a_consumir = LoteProductoEnProceso.objects.select_for_update().get(lote_id=lote_entrada_id)
    except LoteProductoEnProceso.DoesNotExist: msg = f"Lote WIP entrada '{lote_entrada_id}' no encontrado."; logger.error(msg); raise ValidationError(msg)
    try: lote_a_consumir.consumir(cantidad_consumir=cantidad_kg, proceso_ref=doblado, usuario=usuario)
    except (ValidationError, ValueError) as e: logger.error(f"Error al consumir Lote WIP '{lote_entrada_id}': {e}"); raise e
    logger.info(f"Consumo exitoso Lote WIP '{lote_entrada_id}'. Restante: {lote_a_consumir.cantidad_actual}")
    return lote_a_consumir

@transaction.atomic
def consumir_mp_doblado(*, doblado: Doblado, lote_mp_id: str, cantidad_consumida: Decimal, usuario: User) -> LoteMateriaPrima:
    """Consume Lote MP para Doblado."""
    if cantidad_consumida <= 0: raise ValueError("Cantidad a consumir debe ser positiva.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    logger.info(f"Consumiendo {cantidad_consumida} Lote MP '{lote_mp_id}' para Doblado ID {doblado.id} por Usuario ID {usuario.id}")
    try: lote_a_consumir = LoteMateriaPrima.objects.select_for_update().get(lote_id=lote_mp_id)
    except LoteMateriaPrima.DoesNotExist: msg = f"Lote MP '{lote_mp_id}' no encontrado."; logger.error(msg); raise ValidationError(msg)
    try: lote_a_consumir.consumir(cantidad_consumir=cantidad_consumida, proceso_ref=doblado, usuario=usuario)
    except (ValidationError, ValueError) as e: logger.error(f"Error al consumir Lote MP '{lote_mp_id}': {e}"); raise e
    logger.info(f"Consumo exitoso Lote MP '{lote_mp_id}'. Restante: {lote_a_consumir.cantidad_actual}")
    return lote_a_consumir

@transaction.atomic
def registrar_produccion_rollo_doblado(
    *, doblado: Doblado, lote_salida_id: str, kg_producidos: Decimal,
    metros_producidos: Decimal = None, ubicacion_destino_codigo: str, usuario: User,
    observaciones_lote: str = ""
) -> Union[LoteProductoEnProceso, LoteProductoTerminado]:
    """Crea Lote WIP o PT (rollo doblado) y registra movimiento."""
    if kg_producidos <= 0: raise ValueError("Kg producidos deben ser positivos.")
    if not usuario or not usuario.is_authenticated: raise ValueError("Usuario inválido.")
    if not doblado or not doblado.pk: raise ValueError("Registro de Doblado inválido.")
    logger.info(f"Registrando producción {kg_producidos} Kg (ID: {lote_salida_id}) para Doblado ID {doblado.id} por Usuario ID {usuario.id}")
    try:
        ubicacion_destino = Ubicacion.objects.get(codigo=ubicacion_destino_codigo, is_active=True)
        unidad_kg = UnidadMedida.objects.get(codigo='Kg')
        unidad_m = UnidadMedida.objects.get(codigo='m') if metros_producidos is not None else None
        orden_produccion = doblado.orden_produccion
        producto_terminado = orden_produccion.producto
        if not orden_produccion or not producto_terminado: raise ValueError("OP o Producto inválido.")
    except ObjectDoesNotExist as e: msg = f"Error obteniendo datos relacionados: {e}"; logger.error(msg); raise ValidationError(msg)

    es_ultimo_paso = es_ultimo_proceso_op(orden_produccion, 'Doblado') # Asume nombre 'Doblado'
    ct_registro = ContentType.objects.get_for_model(doblado)

    if es_ultimo_paso:
        if LoteProductoTerminado.objects.filter(lote_id=lote_salida_id).exists(): raise ValidationError(f"ID Lote PT '{lote_salida_id}' ya existe.")
        unidad_pt = producto_terminado.unidad_medida
        unidad_pt_usar = unidad_pt
        if unidad_pt.codigo != 'Kg':
            logger.warning(f"Producción Doblado PT en Kg, pero unidad producto es {unidad_pt.codigo}.")
            try: unidad_pt_usar = UnidadMedida.objects.get(codigo='Kg')
            except UnidadMedida.DoesNotExist: raise RuntimeError("Unidad 'Kg' no encontrada.")
            # Mantener unidad_pt_usar como Kg si se decidió forzarla, si no, volver a unidad_pt

        nuevo_lote_pt = LoteProductoTerminado.objects.create(
            lote_id=lote_salida_id, producto_terminado=producto_terminado, orden_produccion=orden_produccion,
            proceso_final_content_type=ct_registro, proceso_final_object_id=doblado.pk,
            cantidad_producida=kg_producidos, cantidad_actual=kg_producidos, # Asume PT en Kg
            ubicacion=ubicacion_destino, estado='DISPONIBLE', fecha_produccion=timezone.now(),
            observaciones=observaciones_lote, creado_por=usuario, actualizado_por=usuario)
        nuevo_lote_pt.registrar_movimiento(tipo_movimiento='PRODUCCION_PT', cantidad=kg_producidos, usuario=usuario, ubicacion_destino=ubicacion_destino, proceso_referencia=doblado, observaciones=f"Producción Doblado (PT) {doblado.id}")
        logger.info(f"Lote PT (Doblado) '{lote_salida_id}' creado ({kg_producidos} {unidad_pt_usar.codigo}).")
        return nuevo_lote_pt
    else:
        if LoteProductoEnProceso.objects.filter(lote_id=lote_salida_id).exists(): raise ValidationError(f"ID Lote WIP '{lote_salida_id}' ya existe.")
        nuevo_lote_wip = LoteProductoEnProceso.objects.create(
            lote_id=lote_salida_id, producto_terminado=producto_terminado, orden_produccion=orden_produccion,
            proceso_origen_content_type=ct_registro, proceso_origen_object_id=doblado.pk,
            cantidad_producida_primaria=kg_producidos, unidad_medida_primaria=unidad_kg,
            cantidad_producida_secundaria=metros_producidos, unidad_medida_secundaria=unidad_m,
            cantidad_actual=kg_producidos, ubicacion=ubicacion_destino, estado='DISPONIBLE',
            fecha_produccion=timezone.now(), observaciones=observaciones_lote,
            creado_por=usuario, actualizado_por=usuario)
        nuevo_lote_wip.registrar_movimiento(tipo_movimiento='PRODUCCION_WIP', cantidad=kg_producidos, usuario=usuario, ubicacion_destino=ubicacion_destino, proceso_referencia=doblado, observaciones=f"Producción Doblado (WIP) {doblado.id}")
        logger.info(f"Lote WIP (Doblado) '{lote_salida_id}' creado ({kg_producidos} Kg).")
        return nuevo_lote_wip