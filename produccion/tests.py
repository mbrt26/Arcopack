# produccion/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError

# Importar modelos necesarios de diferentes apps
from .models import OrdenProduccion, RegistroImpresion
from productos.models import ProductoTerminado
from clientes.models import Cliente
from inventario.models import MateriaPrima, LoteMateriaPrima, LoteProductoEnProceso, MovimientoInventario
from configuracion.models import UnidadMedida, Ubicacion, Proceso, CategoriaProducto, EstadoProducto, TipoMateriaPrima, TipoMaterial, Proveedor # ¡Importar Proveedor!
# Importar las funciones de servicio que queremos probar
from .services import consumir_sustrato_impresion, registrar_produccion_rollo_impreso

User = get_user_model()

# --- Clase de Pruebas para Servicios de Producción ---
class ProduccionServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """
        Configura datos iniciales una vez para toda la clase de pruebas.
        Se ejecuta ANTES de todas las pruebas en esta clase.
        """
        # 1. Crear Usuario de prueba
        cls.test_user = User.objects.create_user(username='testuser', password='password')

        # 2. Crear Configuraciones básicas
        cls.ud_kg = UnidadMedida.objects.create(codigo='Kg', nombre='Kilogramo')
        cls.ud_m = UnidadMedida.objects.create(codigo='m', nombre='Metro')
        cls.ud_unid = UnidadMedida.objects.create(codigo='Unid', nombre='Unidad')
        cls.ubicacion_mp = Ubicacion.objects.create(codigo='BOD-MP', nombre='Bodega MP', tipo='BODEGA_MP')
        cls.ubicacion_wip = Ubicacion.objects.create(codigo='BUF-WIP', nombre='Buffer WIP', tipo='BUFFER_PROD')
        cls.proceso_impr = Proceso.objects.create(nombre='Impresión', orden_flujo=10)
        cls.cat_prod = CategoriaProducto.objects.create(nombre='Test Categoria')
        cls.est_prod = EstadoProducto.objects.create(nombre='Activo')
        cls.tipo_mp_film = TipoMateriaPrima.objects.create(nombre='Film')
        cls.tipo_mat_pet = TipoMaterial.objects.create(nombre='PET 12mic')
        cls.proveedor = Proveedor.objects.create(nit='900123456-7', razon_social='Proveedor Test')


        # 3. Crear Cliente, Materia Prima y Producto Terminado
        cls.cliente = Cliente.objects.create(nit='123456789-0', razon_social='Cliente Test')
        cls.sustrato_pet = MateriaPrima.objects.create(
            codigo='PET-12', nombre='PET Transparente 12mic', categoria_id=1, # Asume categoría Film es ID 1
            unidad_medida=cls.ud_kg, requiere_lote=True
        )
        cls.producto_test = ProductoTerminado.objects.create(
            codigo="PRODTEST01", nombre="Producto Test", tipo_materia_prima=cls.tipo_mp_film,
            estado=cls.est_prod, unidad_medida=cls.ud_unid, categoria=cls.cat_prod,
            tipo_material=cls.tipo_mat_pet, medida_en="mm", calibre_um=12, largo=100, ancho=50
        )

        # 4. Crear Orden de Producción
        cls.op_test = OrdenProduccion.objects.create(
            op_numero="OP-TEST-001", cliente=cls.cliente, producto=cls.producto_test,
            cantidad_solicitada_kg=Decimal('200.00'), fecha_compromiso_entrega=timezone.now().date(),
            sustrato=cls.sustrato_pet, ancho_sustrato_mm=Decimal('1000'), calibre_sustrato_um=Decimal('12.0')
        )
        cls.op_test.procesos.add(cls.proceso_impr)

        # 5. Crear Registro de Impresión (sin horas finales ni producción reportada aún)
        # Necesitamos una Máquina y Colaborador primero
        # ... (Si estos modelos existen, créalos aquí) ...
        # Por ahora, omitimos la creación real y creamos un objeto en memoria o mock para pasar a servicios
        # O creamos un registro básico asumiendo FKs a 1 (requiere que esos registros existan)
        # Para pruebas reales, necesitaríamos crear TODOS los prerequisitos.
        # Simplificación: Creamos un lote de MP para poder probar el consumo.
        cls.lote_sustrato_1 = LoteMateriaPrima.objects.create(
            lote_id="ROLLO-TEST-001",
            materia_prima=cls.sustrato_pet,
            cantidad_recibida=Decimal('150.00'),
            cantidad_actual=Decimal('150.00'),
            ubicacion=cls.ubicacion_mp,
            proveedor=cls.proveedor,
            creado_por=cls.test_user
        )

        # Crear un RegistroImpresion de ejemplo (asumiendo que los FKs existen o se crean aquí)
        # Necesitaríamos crear Maquina, Colaborador, RodilloAnilox, Tinta si no existen
        # cls.registro_impresion_test = RegistroImpresion.objects.create(...)

    # --- Pruebas para consumir_sustrato_impresion ---

    def test_consumir_sustrato_exitoso(self):
        """Prueba el consumo exitoso de materia prima."""
        # Crear un RegistroImpresion simple para la prueba (requiere FKs mínimos)
        # Necesitaríamos datos válidos para maquina, operario, anilox, tipo_tinta, aprobado_por
        # Simplificamos creando solo la OP y pasando esa referencia conceptualmente
        registro_impresion_mock = OrdenProduccion(id=999) # ¡Ojo! Esto es un MOCK muy básico

        cantidad_a_consumir = Decimal('50.00')
        lote_antes = LoteMateriaPrima.objects.get(lote_id="ROLLO-TEST-001")
        stock_inicial = lote_antes.cantidad_actual
        movimientos_antes = MovimientoInventario.objects.count()

        # Llamar al servicio
        lote_actualizado = consumir_sustrato_impresion(
            registro_impresion=registro_impresion_mock, # Pasar el mock o un registro real
            lote_sustrato_id="ROLLO-TEST-001",
            cantidad_kg=cantidad_a_consumir,
            usuario=self.test_user
        )

        # Verificar
        self.assertEqual(lote_actualizado.cantidad_actual, stock_inicial - cantidad_a_consumir)
        self.assertEqual(lote_actualizado.estado, 'DISPONIBLE') # No se agotó
        self.assertEqual(MovimientoInventario.objects.count(), movimientos_antes + 1)
        movimiento = MovimientoInventario.objects.latest('timestamp')
        self.assertEqual(movimiento.tipo_movimiento, 'CONSUMO_MP')
        self.assertEqual(movimiento.cantidad, -cantidad_a_consumir) # Consumo es negativo
        self.assertEqual(movimiento.lote_content_object, lote_actualizado)
        # Verificar la referencia al proceso (si es posible sin un registro real)
        # self.assertEqual(movimiento.proceso_referencia_content_object, registro_impresion_mock)

    def test_consumir_sustrato_stock_insuficiente(self):
        """Prueba que falle el consumo si no hay stock suficiente."""
        registro_impresion_mock = OrdenProduccion(id=999)
        cantidad_a_consumir = Decimal('200.00') # Más que el stock inicial de 150
        lote_antes = LoteMateriaPrima.objects.get(lote_id="ROLLO-TEST-001")
        stock_inicial = lote_antes.cantidad_actual
        movimientos_antes = MovimientoInventario.objects.count()

        # Verificar que lanza ValidationError y que nada cambió
        with self.assertRaises(ValidationError):
            consumir_sustrato_impresion(
                registro_impresion=registro_impresion_mock,
                lote_sustrato_id="ROLLO-TEST-001",
                cantidad_kg=cantidad_a_consumir,
                usuario=self.test_user
            )

        lote_despues = LoteMateriaPrima.objects.get(lote_id="ROLLO-TEST-001")
        self.assertEqual(lote_despues.cantidad_actual, stock_inicial) # No debe cambiar
        self.assertEqual(MovimientoInventario.objects.count(), movimientos_antes) # No debe crear movimiento

    def test_consumir_sustrato_agota_lote(self):
        """Prueba que el estado del lote cambie a CONSUMIDO si se agota."""
        registro_impresion_mock = OrdenProduccion(id=999)
        cantidad_a_consumir = Decimal('150.00') # Exactamente el stock inicial
        movimientos_antes = MovimientoInventario.objects.count()

        lote_actualizado = consumir_sustrato_impresion(
            registro_impresion=registro_impresion_mock,
            lote_sustrato_id="ROLLO-TEST-001",
            cantidad_kg=cantidad_a_consumir,
            usuario=self.test_user
        )

        self.assertEqual(lote_actualizado.cantidad_actual, Decimal('0.00'))
        self.assertEqual(lote_actualizado.estado, 'CONSUMIDO') # Cambió de estado
        self.assertEqual(MovimientoInventario.objects.count(), movimientos_antes + 1)

    # --- Pruebas para registrar_produccion_rollo_impreso ---

    def test_registrar_produccion_wip_exitoso(self):
        """Prueba la creación exitosa de un Lote WIP."""
        # Necesitamos un RegistroImpresion real para vincular
        # Simplificación: Usamos la OP como mock de referencia del proceso
        registro_impresion_mock = self.op_test
        nuevo_lote_id = "WIP-TEST-001"
        kg_prod = Decimal('45.5')
        metros_prod = Decimal('1250.0')
        ubicacion_destino_codigo = self.ubicacion_wip.codigo
        lotes_wip_antes = LoteProductoEnProceso.objects.count()
        movimientos_antes = MovimientoInventario.objects.count()

        nuevo_lote = registrar_produccion_rollo_impreso(
            registro_impresion=registro_impresion_mock, # ¡Ojo! Pasando OP como mock
            lote_salida_id=nuevo_lote_id,
            kg_producidos=kg_prod,
            metros_producidos=metros_prod,
            ubicacion_destino_codigo=ubicacion_destino_codigo,
            usuario=self.test_user,
            observaciones_lote="Prueba de creación WIP"
        )

        # Verificar que el Lote WIP se creó
        self.assertEqual(LoteProductoEnProceso.objects.count(), lotes_wip_antes + 1)
        self.assertEqual(nuevo_lote.lote_id, nuevo_lote_id)
        self.assertEqual(nuevo_lote.cantidad_actual, kg_prod)
        self.assertEqual(nuevo_lote.cantidad_producida_primaria, kg_prod)
        self.assertEqual(nuevo_lote.cantidad_producida_secundaria, metros_prod)
        self.assertEqual(nuevo_lote.ubicacion, self.ubicacion_wip)
        self.assertEqual(nuevo_lote.estado, 'DISPONIBLE')
        self.assertEqual(nuevo_lote.orden_produccion, self.op_test)
        self.assertEqual(nuevo_lote.producto_terminado, self.producto_test)
        # Verificar la referencia genérica al proceso (debe apuntar al mock de OP aquí)
        self.assertEqual(nuevo_lote.proceso_origen_content_object, registro_impresion_mock)

        # Verificar que se creó el MovimientoInventario
        self.assertEqual(MovimientoInventario.objects.count(), movimientos_antes + 1)
        movimiento = MovimientoInventario.objects.latest('timestamp')
        self.assertEqual(movimiento.tipo_movimiento, 'PRODUCCION_WIP')
        self.assertEqual(movimiento.cantidad, kg_prod) # Positivo
        self.assertEqual(movimiento.lote_content_object, nuevo_lote)
        self.assertEqual(movimiento.ubicacion_destino, self.ubicacion_wip)
        self.assertIsNone(movimiento.ubicacion_origen)
        self.assertEqual(movimiento.proceso_referencia_content_object, registro_impresion_mock)

    def test_registrar_produccion_wip_id_duplicado(self):
        """Prueba que falle si el ID del lote de salida ya existe."""
        # Crear un lote WIP primero
        registrar_produccion_rollo_impreso(
             registro_impresion=self.op_test, lote_salida_id="WIP-DUP-001",
             kg_producidos=Decimal('10.0'), ubicacion_destino_codigo=self.ubicacion_wip.codigo,
             usuario=self.test_user
        )
        # Intentar crear otro con el mismo ID
        with self.assertRaises(ValidationError):
             registrar_produccion_rollo_impreso(
                 registro_impresion=self.op_test, lote_salida_id="WIP-DUP-001",
                 kg_producidos=Decimal('5.0'), ubicacion_destino_codigo=self.ubicacion_wip.codigo,
                 usuario=self.test_user
             )

    # --- Añadir más pruebas ---
    # - Probar consumir_sustrato con lote inválido o no disponible
    # - Probar registrar_produccion con ubicación inválida
    # - Probar registrar_produccion sin metros
    # - Probar funciones de servicio para Refilado, Sellado, Doblado...