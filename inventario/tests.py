from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

from .models import (
    MateriaPrima,
    LoteMateriaPrima,
    MovimientoInventario
)
from configuracion.models import (
    UnidadMedida,
    Ubicacion,
    Proveedor,
    CategoriaMateriaPrima
)

User = get_user_model()

class InventarioTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Crear usuario de prueba
        cls.test_user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Crear datos maestros necesarios
        cls.categoria_mp = CategoriaMateriaPrima.objects.create(
            nombre='Film'
        )
        
        cls.unidad_kg = UnidadMedida.objects.create(
            codigo='KG',
            nombre='Kilogramos'
        )
        
        cls.ubicacion_mp = Ubicacion.objects.create(
            codigo='ALM-MP',
            nombre='Almacén Materias Primas'
        )
        
        cls.ubicacion_alt = Ubicacion.objects.create(
            codigo='ALM-SEC',
            nombre='Almacén Secundario'
        )
        
        cls.proveedor = Proveedor.objects.create(
            nit='900123456-7',
            razon_social='Proveedor Test'
        )
        
        # Crear materia prima de prueba
        cls.materia_prima = MateriaPrima.objects.create(
            codigo='MP-TEST-001',
            nombre='Materia Prima Test',
            categoria=cls.categoria_mp,
            unidad_medida=cls.unidad_kg,
            proveedor_preferido=cls.proveedor,
            stock_minimo=100,
            stock_maximo=1000,
            requiere_lote=True
        )

    def test_crear_lote_mp(self):
        """Prueba la creación de un lote de materia prima"""
        lote = LoteMateriaPrima.objects.create(
            lote_id='LOTE-TEST-001',
            materia_prima=self.materia_prima,
            cantidad_actual=500,
            cantidad_recibida=500,
            ubicacion=self.ubicacion_mp,
            proveedor=self.proveedor,
            creado_por=self.test_user
        )
        
        self.assertEqual(lote.estado, 'DISPONIBLE')
        self.assertEqual(lote.cantidad_actual, Decimal('500'))
        
        # Verificar que se creó el movimiento de recepción
        mov = MovimientoInventario.objects.filter(
            tipo_movimiento='RECEPCION_MP',
            lote_object_id=lote.id
        ).first()
        
        self.assertIsNotNone(mov)
        self.assertEqual(mov.cantidad, Decimal('500'))
        self.assertEqual(mov.ubicacion_destino, self.ubicacion_mp)

    def test_consumir_lote_mp(self):
        """Prueba el consumo de un lote de materia prima"""
        lote = LoteMateriaPrima.objects.create(
            lote_id='LOTE-TEST-002',
            materia_prima=self.materia_prima,
            cantidad_actual=200,
            cantidad_recibida=200,
            ubicacion=self.ubicacion_mp,
            proveedor=self.proveedor,
            creado_por=self.test_user
        )
        
        # Consumir parte del lote
        lote.consumir(
            cantidad_consumir=50,
            proceso_ref=None,
            usuario=self.test_user
        )
        
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal('150'))
        self.assertEqual(lote.estado, 'DISPONIBLE')
        
        # Verificar el movimiento de consumo
        mov = MovimientoInventario.objects.filter(
            tipo_movimiento='CONSUMO_MP',
            lote_object_id=lote.id
        ).first()
        
        self.assertIsNotNone(mov)
        self.assertEqual(mov.cantidad, Decimal('-50'))

    def test_transferir_lote_mp(self):
        """Prueba la transferencia de un lote entre ubicaciones"""
        lote = LoteMateriaPrima.objects.create(
            lote_id='LOTE-TEST-003',
            materia_prima=self.materia_prima,
            cantidad_actual=300,
            cantidad_recibida=300,
            ubicacion=self.ubicacion_mp,
            proveedor=self.proveedor,
            creado_por=self.test_user
        )
        
        # Transferir a otra ubicación
        lote.transferir(
            nueva_ubicacion=self.ubicacion_alt,
            usuario=self.test_user
        )
        
        lote.refresh_from_db()
        self.assertEqual(lote.ubicacion, self.ubicacion_alt)
        
        # Verificar movimientos de transferencia
        movs = MovimientoInventario.objects.filter(
            lote_object_id=lote.id
        ).order_by('timestamp')
        
        mov_salida = movs.filter(tipo_movimiento='TRANSFERENCIA_SALIDA').first()
        mov_entrada = movs.filter(tipo_movimiento='TRANSFERENCIA_ENTRADA').first()
        
        self.assertIsNotNone(mov_salida)
        self.assertIsNotNone(mov_entrada)
        self.assertEqual(mov_salida.cantidad, Decimal('-300'))
        self.assertEqual(mov_entrada.cantidad, Decimal('300'))

    def test_validaciones_lote_mp(self):
        """Prueba las validaciones en operaciones de lotes"""
        lote = LoteMateriaPrima.objects.create(
            lote_id='LOTE-TEST-004',
            materia_prima=self.materia_prima,
            cantidad_actual=100,
            cantidad_recibida=100,
            ubicacion=self.ubicacion_mp,
            proveedor=self.proveedor,
            creado_por=self.test_user
        )
        
        # Intentar consumir más de lo disponible
        with self.assertRaises(ValidationError):
            lote.consumir(
                cantidad_consumir=150,
                proceso_ref=None,
                usuario=self.test_user
            )
        
        # Consumir todo el lote
        lote.consumir(
            cantidad_consumir=100,
            proceso_ref=None,
            usuario=self.test_user
        )
        
        lote.refresh_from_db()
        self.assertEqual(lote.estado, 'CONSUMIDO')
        self.assertEqual(lote.cantidad_actual, Decimal('0'))
        
        # Intentar consumir de un lote consumido
        with self.assertRaises(ValidationError):
            lote.consumir(
                cantidad_consumir=1,
                proceso_ref=None,
                usuario=self.test_user
            )
