# produccion/tests.py

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

# Importar modelos necesarios de diferentes apps
from .models import OrdenProduccion, RegistroImpresion, Refilado, Doblado, Sellado
from productos.models import ProductoTerminado
from clientes.models import Cliente
from inventario.models import (
    MateriaPrima, LoteMateriaPrima, LoteProductoEnProceso, 
    LoteProductoTerminado, MovimientoInventario, Tinta
)
from configuracion.models import (
    UnidadMedida, Ubicacion, Proceso, CategoriaProducto, 
    EstadoProducto, TipoMateriaPrima, TipoMaterial, Proveedor,
    CategoriaMateriaPrima, Maquina, RodilloAnilox, TipoTinta
)
from personal.models import Colaborador

# Importar las funciones de servicio que queremos probar
from .services import (
    consumir_sustrato_impresion, 
    registrar_produccion_rollo_impreso
)

User = get_user_model()

class ProduccionServiceTests(TransactionTestCase):
    def setUp(self):
        """
        Configura datos iniciales para cada prueba.
        """
        # 1. Crear Usuario y Colaborador de prueba
        self.test_user = User.objects.create_user(
            username='testuser', 
            password='password'
        )
        self.colaborador = Colaborador.objects.create(
            cedula='12345678',
            nombres='Test',
            apellidos='User',
            cargo='Operario',
            creado_por=self.test_user
        )

        # 2. Crear Configuraciones básicas
        self.ud_kg = UnidadMedida.objects.create(
            codigo='Kg', 
            nombre='Kilogramo'
        )
        self.ud_m = UnidadMedida.objects.create(
            codigo='m', 
            nombre='Metro'
        )
        self.ud_unid = UnidadMedida.objects.create(
            codigo='Unid', 
            nombre='Unidad'
        )
        self.ubicacion_mp = Ubicacion.objects.create(
            codigo='BOD-MP', 
            nombre='Bodega MP', 
            tipo='BODEGA_MP'
        )
        self.ubicacion_wip = Ubicacion.objects.create(
            codigo='BUF-WIP', 
            nombre='Buffer WIP', 
            tipo='BUFFER_PROD'
        )

        # Procesos y categorías
        self.proceso_impr = Proceso.objects.create(
            nombre='Impresión', 
            orden_flujo=10
        )
        self.cat_prod = CategoriaProducto.objects.create(
            nombre='Test Categoria'
        )
        self.est_prod = EstadoProducto.objects.create(
            nombre='Activo'
        )
        self.tipo_mp_film = TipoMateriaPrima.objects.create(
            nombre='Film'
        )
        self.tipo_mat_pet = TipoMaterial.objects.create(
            nombre='PET 12mic'
        )
        self.cat_mp = CategoriaMateriaPrima.objects.create(
            nombre='Film'
        )
        
        # Máquina y anilox
        self.maquina_imp = Maquina.objects.create(
            codigo='IMP01',
            nombre='Impresora 1',
            tipo='IMPRESORA'
        )
        self.anilox = RodilloAnilox.objects.create(
            codigo='ANX01',
            lineatura=400,
            volumen=Decimal('4.5'),
            descripcion='Anilox de prueba',
            estado='Bueno'
        )

        # 3. Crear Cliente, Proveedor, Tipo de Tinta y Tinta
        self.proveedor = Proveedor.objects.create(
            nit='900123456-7', 
            razon_social='Proveedor Test'
        )
        self.cliente = Cliente.objects.create(
            nit='123456789-0', 
            razon_social='Cliente Test'
        )
        self.tipo_tinta = TipoTinta.objects.create(
            nombre='FLEXO'
        )
        self.tinta_test = Tinta.objects.create(
            codigo='TIN01',
            nombre='Tinta Test',
            tipo_tinta=self.tipo_tinta,
            unidad_medida=self.ud_kg,
            color_exacto='Negro'
        )

        # 4. Crear Materia Prima (Sustrato)
        self.sustrato_pet = MateriaPrima.objects.create(
            codigo='PET-12',
            nombre='PET Transparente 12mic',
            categoria=self.cat_mp,
            unidad_medida=self.ud_kg,
            requiere_lote=True
        )

        # 5. Crear Producto Terminado
        self.producto_test = ProductoTerminado.objects.create(
            codigo="PRODTEST01",
            nombre="Producto Test",
            tipo_materia_prima=self.tipo_mp_film,
            estado=self.est_prod,
            unidad_medida=self.ud_kg,  # Cambiado de ud_unid a ud_kg
            categoria=self.cat_prod,
            tipo_material=self.tipo_mat_pet,
            medida_en="mm",
            calibre_um=12,
            largo=100,
            ancho=50
        )

        # 6. Crear Orden de Producción
        self.op_test = OrdenProduccion.objects.create(
            op_numero="OP-TEST-001",
            cliente=self.cliente,
            producto=self.producto_test,
            cantidad_solicitada_kg=Decimal('200.00'),
            fecha_compromiso_entrega=timezone.now().date(),
            sustrato=self.sustrato_pet,
            ancho_sustrato_mm=Decimal('1000'),
            calibre_sustrato_um=Decimal('12.0'),
            creado_por=self.test_user
        )
        self.op_test.procesos.add(self.proceso_impr)

        # 7. Crear Registro de Impresión
        self.registro_impresion = RegistroImpresion.objects.create(
            orden_produccion=self.op_test,
            fecha=timezone.now().date(),
            maquina=self.maquina_imp,
            operario_principal=self.colaborador,
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
            anilox=self.anilox,
            repeticion_mm=Decimal('200.0'),
            pistas=4,
            tipo_tinta_principal=self.tinta_test,
            aprobado_por=self.colaborador,
            creado_por=self.test_user
        )

        # 8. Crear Lote de Sustrato para pruebas
        self.lote_sustrato_1 = LoteMateriaPrima.objects.create(
            lote_id="ROLLO-TEST-001",
            materia_prima=self.sustrato_pet,
            cantidad_recibida=Decimal('150.00'),
            cantidad_actual=Decimal('150.00'),
            ubicacion=self.ubicacion_mp,
            proveedor=self.proveedor,
            creado_por=self.test_user
        )

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
        nuevo_lote_id = "WIP-TEST-001"
        kg_prod = Decimal('45.5')
        metros_prod = Decimal('1250.0')
        ubicacion_destino_codigo = self.ubicacion_wip.codigo

        # Asegurar que haya otro proceso después de Impresión
        proceso_siguiente = Proceso.objects.create(
            nombre='Refilado',
            orden_flujo=20  # Mayor que Impresión (10)
        )
        self.op_test.procesos.add(self.proceso_impr)  # Agregar proceso de impresión si no está
        self.op_test.procesos.add(proceso_siguiente)

        lotes_wip_antes = LoteProductoEnProceso.objects.count()
        lotes_pt_antes = LoteProductoTerminado.objects.count()
        movimientos_antes = MovimientoInventario.objects.count()

        with transaction.atomic():
            nuevo_lote = registrar_produccion_rollo_impreso(
                registro_impresion=self.registro_impresion,
                lote_salida_id=nuevo_lote_id,
                kg_producidos=kg_prod,
                metros_producidos=metros_prod,
                ubicacion_destino_codigo=ubicacion_destino_codigo,
                usuario=self.test_user,
                observaciones_lote="Prueba de creación WIP"
            )

            # Verificación del lote creado
            self.assertEqual(nuevo_lote.lote_id, nuevo_lote_id)
            self.assertEqual(nuevo_lote.cantidad_actual, kg_prod)
            self.assertEqual(nuevo_lote.orden_produccion, self.op_test)
            self.assertEqual(nuevo_lote.producto_terminado, self.producto_test)

            # Verificaciones específicas según el tipo
            if isinstance(nuevo_lote, LoteProductoEnProceso):
                self.assertEqual(nuevo_lote.cantidad_producida_primaria, kg_prod)
                self.assertEqual(nuevo_lote.cantidad_producida_secundaria, metros_prod)
                self.assertEqual(nuevo_lote.proceso_origen, self.registro_impresion)
            else:  # LoteProductoTerminado
                self.assertEqual(nuevo_lote.cantidad_producida, kg_prod)
                self.assertEqual(nuevo_lote.proceso_final, self.registro_impresion)

        # Verificaciones de base de datos (fuera de la transacción)
        self.assertEqual(LoteProductoEnProceso.objects.count(), lotes_wip_antes + 1)
        self.assertEqual(LoteProductoTerminado.objects.count(), lotes_pt_antes)  # No debería cambiar

        # Verificación del movimiento
        movimiento = MovimientoInventario.objects.latest('timestamp')
        self.assertEqual(movimiento.tipo_movimiento, 'PRODUCCION_WIP')
        self.assertEqual(movimiento.cantidad, kg_prod)
        self.assertEqual(movimiento.lote_content_object, nuevo_lote)
        self.assertEqual(movimiento.ubicacion_destino.codigo, ubicacion_destino_codigo)
        self.assertIsNone(movimiento.ubicacion_origen)
        self.assertEqual(movimiento.proceso_referencia_content_object, self.registro_impresion)

    def test_registrar_produccion_wip_id_duplicado(self):
        """Prueba que falle si el ID del lote de salida ya existe."""
        # Crear un lote WIP primero
        registrar_produccion_rollo_impreso(
             registro_impresion=self.registro_impresion,
             lote_salida_id="WIP-DUP-001",
             kg_producidos=Decimal('10.0'),
             ubicacion_destino_codigo=self.ubicacion_wip.codigo,
             usuario=self.test_user
        )
        # Intentar crear otro con el mismo ID
        with self.assertRaises(ValidationError):
             registrar_produccion_rollo_impreso(
                 registro_impresion=self.registro_impresion,
                 lote_salida_id="WIP-DUP-001",
                 kg_producidos=Decimal('5.0'),
                 ubicacion_destino_codigo=self.ubicacion_wip.codigo,
                 usuario=self.test_user
             )

    # --- Añadir más pruebas ---
    # - Probar consumir_sustrato con lote inválido o no disponible
    # - Probar registrar_produccion con ubicación inválida
    # - Probar registrar_produccion sin metros
    # - Probar funciones de servicio para Refilado, Sellado, Doblado...