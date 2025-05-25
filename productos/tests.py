from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import ProductoTerminado
from configuracion.models import (
    CategoriaProducto, SubcategoriaProducto, EstadoProducto, UnidadMedida,
    TipoMateriaPrima, TipoMaterial, TipoSellado
)
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()

class ProductoTerminadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Configura datos de prueba que se compartirán entre todos los tests."""
        # Crear usuario para pruebas
        cls.user = User.objects.create_user(username='testuser', password='12345')
        
        # Crear datos maestros necesarios
        cls.categoria = CategoriaProducto.objects.create(nombre='Laminados')
        cls.subcategoria = SubcategoriaProducto.objects.create(
            nombre='Bilaminados', categoria=cls.categoria
        )
        cls.estado = EstadoProducto.objects.create(nombre='Activo')
        cls.unidad = UnidadMedida.objects.create(codigo='Kg', nombre='Kilogramo')
        cls.tipo_mp = TipoMateriaPrima.objects.create(nombre='BOPP')
        cls.tipo_material = TipoMaterial.objects.create(
            nombre='BOPP Trans 20µm',
            tipo_base=cls.tipo_mp
        )
        cls.tipo_sellado = TipoSellado.objects.create(nombre='Lateral')

    def test_crear_producto_datos_minimos(self):
        """Prueba crear un producto con los datos mínimos requeridos."""
        producto = ProductoTerminado(
            codigo='TEST001',
            nombre='Producto Test',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )
        producto.full_clean()  # Validar modelo
        producto.save()
        
        self.assertEqual(ProductoTerminado.objects.count(), 1)
        self.assertEqual(producto.codigo, 'TEST001')
        self.assertEqual(producto.medida_en, 'mm')  # valor por defecto
        self.assertFalse(producto.comercializable)  # valor por defecto

    def test_validacion_codigo_unico(self):
        """Prueba que no se pueden crear dos productos con el mismo código."""
        producto1 = ProductoTerminado.objects.create(
            codigo='TEST001',
            nombre='Producto Test 1',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )

        producto2 = ProductoTerminado(
            codigo='TEST001',  # Mismo código
            nombre='Producto Test 2',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )

        with self.assertRaises(ValidationError):
            producto2.full_clean()

    def test_validacion_ultrasonido(self):
        """Prueba las validaciones relacionadas con el sellado por ultrasonido."""
        producto = ProductoTerminado(
            codigo='TEST002',
            nombre='Producto Test',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00'),
            sellado_ultrasonido=True  # Activar ultrasonido sin posición
        )

        with self.assertRaises(ValidationError) as context:
            producto.full_clean()
        
        self.assertIn('sellado_ultrasonido_pos', str(context.exception))

        # Ahora agregamos la posición y debería validar
        producto.sellado_ultrasonido_pos = Decimal('10.00')
        producto.full_clean()  # No debería levantar ValidationError

    def test_validacion_medidas_positivas(self):
        """Prueba que las medidas deben ser positivas."""
        producto = ProductoTerminado(
            codigo='TEST003',
            nombre='Producto Test',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('-20.00'),  # Valor negativo
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )

        with self.assertRaises(ValidationError) as context:
            producto.full_clean()
        
        self.assertIn('calibre_um', str(context.exception))

    def test_validacion_precorte(self):
        """Prueba las validaciones relacionadas con el precorte."""
        producto = ProductoTerminado(
            codigo='TEST004',
            nombre='Producto Test',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00'),
            sellado_precorte=True  # Activar precorte sin medida
        )

        with self.assertRaises(ValidationError) as context:
            producto.full_clean()
        
        self.assertIn('sellado_precorte_medida', str(context.exception))

        # Agregar medida y debería validar
        producto.sellado_precorte_medida = Decimal('5.00')
        producto.full_clean()  # No debería levantar ValidationError

    def test_auditoria_campos(self):
        """Prueba que los campos de auditoría se llenan correctamente."""
        producto = ProductoTerminado(
            codigo='TEST005',
            nombre='Producto Test',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )
        
        # Guardar con usuario
        producto.save(user=self.user)
        
        self.assertEqual(producto.creado_por, self.user)
        self.assertEqual(producto.actualizado_por, self.user)
        self.assertIsNotNone(producto.creado_en)
        self.assertIsNotNone(producto.actualizado_en)

        # Modificar y guardar de nuevo
        producto.nombre = "Producto Test Modificado"
        producto.save(user=self.user)
        
        self.assertEqual(producto.actualizado_por, self.user)
        self.assertGreater(producto.actualizado_en, producto.creado_en)

    def test_validacion_subcategoria(self):
        """Prueba que la subcategoría pertenezca a la categoría correcta."""
        otra_categoria = CategoriaProducto.objects.create(nombre='Monocapa')
        subcategoria_otra = SubcategoriaProducto.objects.create(
            nombre='Mono BOPP',
            categoria=otra_categoria
        )

        producto = ProductoTerminado(
            codigo='TEST006',
            nombre='Producto Test',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,  # Categoría: Laminados
            subcategoria=subcategoria_otra,  # Subcategoría de Monocapa
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )

        # Debe fallar porque la subcategoría no pertenece a la categoría
        with self.assertRaises(ValidationError):
            producto.full_clean()

    def test_str_representation(self):
        """Prueba la representación en string del modelo."""
        producto = ProductoTerminado.objects.create(
            codigo='TEST007',
            nombre='Producto Test',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )

        self.assertEqual(str(producto), 'TEST007 - Producto Test')

class ProductoTerminadoAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        """Configura datos de prueba que se compartirán entre todos los tests."""
        # Crear usuario para pruebas
        cls.user = User.objects.create_user(username='testuser', password='12345')
        
        # Crear datos maestros necesarios
        cls.categoria = CategoriaProducto.objects.create(nombre='Laminados')
        cls.estado = EstadoProducto.objects.create(nombre='Activo')
        cls.unidad = UnidadMedida.objects.create(codigo='Kg', nombre='Kilogramo')
        cls.tipo_mp = TipoMateriaPrima.objects.create(nombre='BOPP')
        cls.tipo_material = TipoMaterial.objects.create(
            nombre='BOPP Trans 20µm',
            tipo_base=cls.tipo_mp
        )

    def setUp(self):
        """Se ejecuta antes de cada test."""
        self.client.force_authenticate(user=self.user)

    def test_crear_producto_api(self):
        """Prueba crear un producto vía API."""
        url = '/api/v1/productos/'  # Actualizado para coincidir con las URLs configuradas
        data = {
            'codigo': 'API001',
            'nombre': 'Producto API Test',
            'tipo_materia_prima': self.tipo_mp.id,
            'estado': self.estado.id,
            'unidad_medida': self.unidad.id,
            'categoria': self.categoria.id,
            'tipo_material': self.tipo_material.id,
            'calibre_um': '20.00',
            'largo': '100.00',
            'ancho': '50.00'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProductoTerminado.objects.count(), 1)
        self.assertEqual(ProductoTerminado.objects.get().codigo, 'API001')

    def test_listar_productos_api(self):
        """Prueba listar productos vía API."""
        # Crear algunos productos de prueba
        for i in range(3):
            ProductoTerminado.objects.create(
                codigo=f'API00{i+1}',
                nombre=f'Producto API Test {i+1}',
                tipo_materia_prima=self.tipo_mp,
                estado=self.estado,
                unidad_medida=self.unidad,
                categoria=self.categoria,
                tipo_material=self.tipo_material,
                calibre_um=Decimal('20.00'),
                largo=Decimal('100.00'),
                ancho=Decimal('50.00')
            )

        url = '/api/v1/productos/'  # Actualizado para coincidir con las URLs configuradas
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_actualizar_producto_api(self):
        """Prueba actualizar un producto vía API."""
        producto = ProductoTerminado.objects.create(
            codigo='API001',
            nombre='Producto Original',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )

        url = f'/api/v1/productos/{producto.id}/'  # Actualizado para coincidir con las URLs configuradas
        data = {
            'codigo': 'API001',  # Mismo código
            'nombre': 'Producto Modificado',  # Nuevo nombre
            'tipo_materia_prima': self.tipo_mp.id,
            'estado': self.estado.id,
            'unidad_medida': self.unidad.id,
            'categoria': self.categoria.id,
            'tipo_material': self.tipo_material.id,
            'calibre_um': '20.00',
            'largo': '100.00',
            'ancho': '50.00'
        }
        
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ProductoTerminado.objects.get(id=producto.id).nombre, 'Producto Modificado')

    def test_eliminar_producto_api(self):
        """Prueba el borrado lógico de un producto vía API."""
        producto = ProductoTerminado.objects.create(
            codigo='API001',
            nombre='Producto a Eliminar',
            tipo_materia_prima=self.tipo_mp,
            estado=self.estado,
            unidad_medida=self.unidad,
            categoria=self.categoria,
            tipo_material=self.tipo_material,
            calibre_um=Decimal('20.00'),
            largo=Decimal('100.00'),
            ancho=Decimal('50.00')
        )

        url = f'/api/v1/productos/{producto.id}/'  # Actualizado para coincidir con las URLs configuradas
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verificar que el producto sigue existiendo pero inactivo
        producto_db = ProductoTerminado.objects.get(id=producto.id)
        self.assertFalse(producto_db.is_active)
