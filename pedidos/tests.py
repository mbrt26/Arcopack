# pedidos/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from .models import Pedido, LineaPedido, SeguimientoPedido
from clientes.models import Cliente
from productos.models import ProductoTerminado, CategoriaProducto, UnidadMedida


class PedidoModelTest(TestCase):
    """Tests para el modelo Pedido"""
    
    def setUp(self):
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear cliente de prueba
        self.cliente = Cliente.objects.create(
            tipo_documento='NIT',
            numero_documento='900123456',
            razon_social='Cliente Test S.A.S.',
            activo=True
        )
        
        # Crear unidad de medida
        self.unidad = UnidadMedida.objects.create(
            nombre='Unidad',
            simbolo='UN'
        )
        
        # Crear categoría de producto
        self.categoria = CategoriaProducto.objects.create(
            nombre='Categoría Test',
            descripcion='Categoría de prueba'
        )
        
        # Crear producto de prueba
        self.producto = ProductoTerminado.objects.create(
            codigo='PROD-001',
            nombre='Producto Test',
            categoria=self.categoria,
            precio_venta=Decimal('100.00'),
            unidad_medida=self.unidad,
            activo=True
        )

    def test_crear_pedido(self):
        """Test de creación de pedido"""
        pedido = Pedido.objects.create(
            numero_pedido='PED-2024-0001',
            cliente=self.cliente,
            fecha_pedido=date.today(),
            fecha_compromiso=date.today() + timedelta(days=30),
            creado_por=self.user
        )
        
        self.assertEqual(pedido.numero_pedido, 'PED-2024-0001')
        self.assertEqual(pedido.cliente, self.cliente)
        self.assertEqual(pedido.estado, 'BORRADOR')
        self.assertEqual(pedido.prioridad, 'NORMAL')
        self.assertIsNotNone(pedido.creado_en)

    def test_calcular_total_pedido(self):
        """Test de cálculo del total del pedido"""
        pedido = Pedido.objects.create(
            numero_pedido='PED-2024-0002',
            cliente=self.cliente,
            fecha_pedido=date.today(),
            fecha_compromiso=date.today() + timedelta(days=30),
            creado_por=self.user
        )
        
        # Agregar líneas al pedido
        LineaPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=10,
            precio_unitario=Decimal('100.00')
        )
        
        LineaPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=5,
            precio_unitario=Decimal('200.00')
        )
        
        # Calcular total
        pedido.calcular_total()
        
        # 10 * 100 + 5 * 200 = 2000
        self.assertEqual(pedido.valor_total, Decimal('2000.00'))

    def test_porcentaje_completado(self):
        """Test del cálculo de porcentaje completado"""
        pedido = Pedido.objects.create(
            numero_pedido='PED-2024-0003',
            cliente=self.cliente,
            fecha_pedido=date.today(),
            fecha_compromiso=date.today() + timedelta(days=30),
            creado_por=self.user
        )
        
        linea = LineaPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=100,
            precio_unitario=Decimal('50.00'),
            cantidad_producida=25
        )
        
        # 25 de 100 = 25%
        self.assertEqual(pedido.porcentaje_completado, 25.0)

    def test_validacion_fechas(self):
        """Test de validación de fechas"""
        with self.assertRaises(Exception):
            # Fecha de compromiso anterior a fecha de pedido debería fallar
            Pedido.objects.create(
                numero_pedido='PED-2024-0004',
                cliente=self.cliente,
                fecha_pedido=date.today(),
                fecha_compromiso=date.today() - timedelta(days=1),
                creado_por=self.user
            )

    def test_seguimiento_automatico(self):
        """Test de creación automática de seguimiento"""
        pedido = Pedido.objects.create(
            numero_pedido='PED-2024-0005',
            cliente=self.cliente,
            fecha_pedido=date.today(),
            fecha_compromiso=date.today() + timedelta(days=30),
            creado_por=self.user
        )
        
        # Cambiar estado
        estado_anterior = pedido.estado
        pedido.estado = 'CONFIRMADO'
        pedido.save()
        
        # Crear seguimiento
        SeguimientoPedido.objects.create(
            pedido=pedido,
            estado_anterior=estado_anterior,
            estado_nuevo='CONFIRMADO',
            usuario=self.user,
            observaciones='Test de cambio de estado'
        )
        
        self.assertEqual(pedido.seguimientos.count(), 1)


class LineaPedidoModelTest(TestCase):
    """Tests para el modelo LineaPedido"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.cliente = Cliente.objects.create(
            tipo_documento='NIT',
            numero_documento='900123456',
            razon_social='Cliente Test S.A.S.',
            activo=True
        )
        
        self.unidad = UnidadMedida.objects.create(
            nombre='Unidad',
            simbolo='UN'
        )
        
        self.categoria = CategoriaProducto.objects.create(
            nombre='Categoría Test'
        )
        
        self.producto = ProductoTerminado.objects.create(
            codigo='PROD-001',
            nombre='Producto Test',
            categoria=self.categoria,
            precio_venta=Decimal('100.00'),
            unidad_medida=self.unidad,
            activo=True
        )
        
        self.pedido = Pedido.objects.create(
            numero_pedido='PED-2024-0001',
            cliente=self.cliente,
            fecha_pedido=date.today(),
            fecha_compromiso=date.today() + timedelta(days=30),
            creado_por=self.user
        )

    def test_crear_linea_pedido(self):
        """Test de creación de línea de pedido"""
        linea = LineaPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=10,
            precio_unitario=Decimal('100.00'),
            especificaciones_tecnicas='Especificaciones de prueba'
        )
        
        self.assertEqual(linea.pedido, self.pedido)
        self.assertEqual(linea.producto, self.producto)
        self.assertEqual(linea.cantidad, 10)
        self.assertEqual(linea.precio_unitario, Decimal('100.00'))

    def test_subtotal_linea(self):
        """Test del cálculo de subtotal"""
        linea = LineaPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=15,
            precio_unitario=Decimal('75.50')
        )
        
        # 15 * 75.50 = 1132.50
        self.assertEqual(linea.subtotal, Decimal('1132.50'))

    def test_cantidad_pendiente(self):
        """Test del cálculo de cantidad pendiente"""
        linea = LineaPedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=100,
            precio_unitario=Decimal('50.00'),
            cantidad_producida=30
        )
        
        # 100 - 30 = 70
        self.assertEqual(linea.cantidad_pendiente, 70)


class PedidoViewsTest(TestCase):
    """Tests para las vistas del módulo de pedidos"""
    
    def setUp(self):
        self.client = Client()
        
        # Crear usuario con permisos
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Agregar permisos necesarios
        from django.contrib.auth.models import Permission
        permissions = [
            'add_pedido', 'change_pedido', 'view_pedido', 'delete_pedido'
        ]
        for perm_codename in permissions:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                self.user.user_permissions.add(perm)
            except Permission.DoesNotExist:
                pass
        
        self.cliente = Cliente.objects.create(
            tipo_documento='NIT',
            numero_documento='900123456',
            razon_social='Cliente Test S.A.S.',
            activo=True
        )
        
        self.unidad = UnidadMedida.objects.create(
            nombre='Unidad',
            simbolo='UN'
        )
        
        self.categoria = CategoriaProducto.objects.create(
            nombre='Categoría Test'
        )
        
        self.producto = ProductoTerminado.objects.create(
            codigo='PROD-001',
            nombre='Producto Test',
            categoria=self.categoria,
            precio_venta=Decimal('100.00'),
            unidad_medida=self.unidad,
            activo=True
        )

    def test_pedido_list_view(self):
        """Test de la vista de lista de pedidos"""
        self.client.login(username='testuser', password='testpass123')
        
        # Crear algunos pedidos de prueba
        for i in range(5):
            Pedido.objects.create(
                numero_pedido=f'PED-2024-000{i+1}',
                cliente=self.cliente,
                fecha_pedido=date.today(),
                fecha_compromiso=date.today() + timedelta(days=30),
                creado_por=self.user
            )
        
        response = self.client.get(reverse('pedidos:pedido_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lista de Pedidos')
        self.assertEqual(len(response.context['pedidos']), 5)

    def test_pedido_detail_view(self):
        """Test de la vista de detalle de pedido"""
        self.client.login(username='testuser', password='testpass123')
        
        pedido = Pedido.objects.create(
            numero_pedido='PED-2024-0001',
            cliente=self.cliente,
            fecha_pedido=date.today(),
            fecha_compromiso=date.today() + timedelta(days=30),
            creado_por=self.user
        )
        
        response = self.client.get(
            reverse('pedidos:pedido_detail', kwargs={'pk': pedido.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, pedido.numero_pedido)
        self.assertEqual(response.context['pedido'], pedido)

    def test_pedido_create_view_get(self):
        """Test GET de la vista de creación de pedido"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('pedidos:pedido_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nuevo Pedido')

    def test_pedido_create_view_post(self):
        """Test POST de la vista de creación de pedido"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'cliente': self.cliente.pk,
            'fecha_pedido': date.today(),
            'fecha_compromiso': date.today() + timedelta(days=30),
            'observaciones': 'Pedido de prueba',
            
            # Datos del formset (management form)
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            
            # Primera línea
            'form-0-producto': self.producto.pk,
            'form-0-cantidad': '10',
            'form-0-precio_unitario': '100.00',
            'form-0-especificaciones_tecnicas': 'Especificaciones de prueba'
        }
        
        response = self.client.post(reverse('pedidos:pedido_create'), data)
        
        # Debería redireccionar al detalle del pedido creado
        self.assertEqual(response.status_code, 302)
        
        # Verificar que el pedido se creó
        pedido = Pedido.objects.first()
        self.assertIsNotNone(pedido)
        self.assertEqual(pedido.cliente, self.cliente)
        self.assertEqual(pedido.lineas.count(), 1)

    def test_cambiar_estado_pedido(self):
        """Test de cambio de estado de pedido"""
        self.client.login(username='testuser', password='testpass123')
        
        pedido = Pedido.objects.create(
            numero_pedido='PED-2024-0001',
            cliente=self.cliente,
            fecha_pedido=date.today(),
            fecha_compromiso=date.today() + timedelta(days=30),
            creado_por=self.user
        )
        
        data = {
            'nuevo_estado': 'CONFIRMADO',
            'observaciones': 'Confirmando pedido de prueba'
        }
        
        response = self.client.post(
            reverse('pedidos:cambiar_estado', kwargs={'pk': pedido.pk}),
            data
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verificar que el estado cambió
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'CONFIRMADO')
        
        # Verificar que se creó el seguimiento
        self.assertEqual(pedido.seguimientos.count(), 1)

    def test_dashboard_view(self):
        """Test de la vista del dashboard"""
        self.client.login(username='testuser', password='testpass123')
        
        # Crear algunos pedidos con diferentes estados
        estados = ['BORRADOR', 'CONFIRMADO', 'EN_PRODUCCION']
        for i, estado in enumerate(estados):
            pedido = Pedido.objects.create(
                numero_pedido=f'PED-2024-000{i+1}',
                cliente=self.cliente,
                fecha_pedido=date.today(),
                fecha_compromiso=date.today() + timedelta(days=30),
                estado=estado,
                creado_por=self.user
            )
        
        response = self.client.get(reverse('pedidos:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard de Pedidos')
        
        estadisticas = response.context['estadisticas']
        self.assertEqual(estadisticas['total_pedidos'], 3)
        self.assertEqual(estadisticas['pedidos_confirmados'], 1)
        self.assertEqual(estadisticas['pedidos_en_produccion'], 1)


class PedidoUtilsTest(TestCase):
    """Tests para las utilidades del módulo de pedidos"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.cliente = Cliente.objects.create(
            tipo_documento='NIT',
            numero_documento='900123456',
            razon_social='Cliente Test S.A.S.',
            activo=True
        )

    def test_generar_numero_pedido(self):
        """Test de generación automática de número de pedido"""
        from .utils import generar_numero_pedido
        
        numero = generar_numero_pedido()
        year = timezone.now().year
        
        self.assertTrue(numero.startswith(f'PED-{year}-'))
        self.assertEqual(len(numero), 13)  # PED-YYYY-NNNN

    def test_validar_disponibilidad_producto(self):
        """Test de validación de disponibilidad de producto"""
        from .utils import validar_disponibilidad_producto
        
        # Este test dependería de la implementación específica
        # de validación de inventario
        pass


class PedidoAPITest(TestCase):
    """Tests para las APIs del módulo de pedidos"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.unidad = UnidadMedida.objects.create(
            nombre='Unidad',
            simbolo='UN'
        )
        
        self.categoria = CategoriaProducto.objects.create(
            nombre='Categoría Test'
        )
        
        self.producto = ProductoTerminado.objects.create(
            codigo='PROD-001',
            nombre='Producto Test',
            categoria=self.categoria,
            precio_venta=Decimal('100.00'),
            unidad_medida=self.unidad,
            activo=True
        )

    def test_get_producto_info_api(self):
        """Test de la API para obtener información de producto"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(
            reverse('pedidos:get_producto_info'),
            {'producto_id': self.producto.pk}
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['id'], self.producto.pk)
        self.assertEqual(data['codigo'], self.producto.codigo)
        self.assertEqual(data['nombre'], self.producto.nombre)
        self.assertEqual(float(data['precio_venta']), float(self.producto.precio_venta))

    def test_get_producto_info_api_not_found(self):
        """Test de la API con producto inexistente"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(
            reverse('pedidos:get_producto_info'),
            {'producto_id': 99999}
        )
        
        self.assertEqual(response.status_code, 404)


class PedidoIntegrationTest(TestCase):
    """Tests de integración para el módulo completo"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Agregar permisos
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='pedidos'
        )
        self.user.user_permissions.set(permissions)
        
        self.cliente = Cliente.objects.create(
            tipo_documento='NIT',
            numero_documento='900123456',
            razon_social='Cliente Test S.A.S.',
            activo=True
        )

    def test_flujo_completo_pedido(self):
        """Test del flujo completo desde creación hasta entrega"""
        self.client.login(username='testuser', password='testpass123')
        
        # 1. Crear pedido
        pedido = Pedido.objects.create(
            numero_pedido='PED-2024-0001',
            cliente=self.cliente,
            fecha_pedido=date.today(),
            fecha_compromiso=date.today() + timedelta(days=30),
            creado_por=self.user
        )
        
        self.assertEqual(pedido.estado, 'BORRADOR')
        
        # 2. Confirmar pedido
        pedido.estado = 'CONFIRMADO'
        pedido.save()
        
        SeguimientoPedido.objects.create(
            pedido=pedido,
            estado_anterior='BORRADOR',
            estado_nuevo='CONFIRMADO',
            usuario=self.user,
            observaciones='Pedido confirmado'
        )
        
        # 3. Pasar a producción
        pedido.estado = 'EN_PRODUCCION'
        pedido.save()
        
        SeguimientoPedido.objects.create(
            pedido=pedido,
            estado_anterior='CONFIRMADO',
            estado_nuevo='EN_PRODUCCION',
            usuario=self.user,
            observaciones='Iniciada producción'
        )
        
        # 4. Completar producción
        pedido.estado = 'PRODUCIDO'
        pedido.save()
        
        # 5. Facturar
        pedido.estado = 'FACTURADO'
        pedido.numero_factura = 'FAC-001'
        pedido.fecha_facturacion = date.today()
        pedido.save()
        
        # 6. Entregar
        pedido.estado = 'ENTREGADO'
        pedido.save()
        
        # Verificar que el flujo se completó correctamente
        self.assertEqual(pedido.estado, 'ENTREGADO')
        self.assertIsNotNone(pedido.numero_factura)
        self.assertIsNotNone(pedido.fecha_facturacion)
        
        # Verificar seguimientos
        self.assertGreaterEqual(pedido.seguimientos.count(), 2)