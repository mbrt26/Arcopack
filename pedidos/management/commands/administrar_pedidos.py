from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import date, timedelta

from pedidos.models import Pedido, SeguimientoPedido
from pedidos.utils import obtener_alertas_pedidos, generar_numero_pedido


class Command(BaseCommand):
    help = 'Administra pedidos: actualiza estados, genera reportes y alertas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--alertas',
            action='store_true',
            help='Muestra alertas de pedidos vencidos y próximos a vencer'
        )
        
        parser.add_argument(
            '--actualizar-estados',
            action='store_true',
            help='Actualiza automáticamente estados de pedidos según reglas de negocio'
        )
        
        parser.add_argument(
            '--reporte-diario',
            action='store_true',
            help='Genera reporte diario de pedidos'
        )
        
        parser.add_argument(
            '--limpiar-borradores',
            action='store_true',
            help='Elimina pedidos en borrador con más de 30 días de antigüedad'
        )
        
        parser.add_argument(
            '--generar-numeros',
            action='store_true',
            help='Genera números automáticos para pedidos sin número'
        )

    def handle(self, *args, **options):
        if options['alertas']:
            self.mostrar_alertas()
        
        if options['actualizar_estados']:
            self.actualizar_estados_automaticos()
        
        if options['reporte_diario']:
            self.generar_reporte_diario()
        
        if options['limpiar_borradores']:
            self.limpiar_borradores_antiguos()
        
        if options['generar_numeros']:
            self.generar_numeros_faltantes()
        
        if not any(options.values()):
            self.stdout.write(self.style.WARNING('No se especificó ninguna acción. Use --help para ver opciones.'))

    def mostrar_alertas(self):
        """Muestra alertas importantes de pedidos"""
        self.stdout.write(self.style.SUCCESS('=== ALERTAS DE PEDIDOS ==='))
        
        alertas = obtener_alertas_pedidos()
        
        if not alertas:
            self.stdout.write(self.style.SUCCESS('✓ No hay alertas pendientes'))
            return
        
        for alerta in alertas:
            if alerta['tipo'] == 'danger':
                style = self.style.ERROR
            elif alerta['tipo'] == 'warning':
                style = self.style.WARNING
            else:
                style = self.style.NOTICE
            
            self.stdout.write(style(f"⚠️  {alerta['mensaje']}"))

    def actualizar_estados_automaticos(self):
        """Actualiza estados de pedidos según reglas automáticas"""
        self.stdout.write(self.style.SUCCESS('=== ACTUALIZANDO ESTADOS AUTOMÁTICOS ==='))
        
        actualizados = 0
        
        # Marcar pedidos como vencidos si pasaron de la fecha de compromiso
        pedidos_vencidos = Pedido.objects.filter(
            fecha_compromiso__lt=date.today(),
            estado__in=['CONFIRMADO', 'EN_PRODUCCION'],
            observaciones__icontains='VENCIDO'  # Evitar marcar múltiples veces
        ).exclude(observaciones__icontains='VENCIDO')
        
        for pedido in pedidos_vencidos:
            pedido.observaciones = f"{pedido.observaciones or ''}\n[SISTEMA] Pedido marcado como VENCIDO el {date.today()}"
            pedido.save()
            
            # Crear seguimiento
            SeguimientoPedido.objects.create(
                pedido=pedido,
                estado_anterior=pedido.estado,
                estado_nuevo=pedido.estado,
                observaciones='Sistema: Pedido marcado como vencido automáticamente',
                usuario=None
            )
            
            actualizados += 1
        
        if actualizados > 0:
            self.stdout.write(
                self.style.WARNING(f'✓ {actualizados} pedidos marcados como vencidos')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ No hay pedidos para marcar como vencidos')
            )

    def generar_reporte_diario(self):
        """Genera reporte diario de pedidos"""
        self.stdout.write(self.style.SUCCESS('=== REPORTE DIARIO DE PEDIDOS ==='))
        
        hoy = date.today()
        
        # Estadísticas generales
        total_pedidos = Pedido.objects.count()
        pedidos_hoy = Pedido.objects.filter(fecha_pedido=hoy).count()
        
        # Por estado
        borradores = Pedido.objects.filter(estado='BORRADOR').count()
        confirmados = Pedido.objects.filter(estado='CONFIRMADO').count()
        en_produccion = Pedido.objects.filter(estado='EN_PRODUCCION').count()
        producidos = Pedido.objects.filter(estado='PRODUCIDO').count()
        facturados = Pedido.objects.filter(estado='FACTURADO').count()
        entregados = Pedido.objects.filter(estado='ENTREGADO').count()
        cancelados = Pedido.objects.filter(estado='CANCELADO').count()
        
        # Vencimientos
        vencidos = Pedido.objects.filter(
            fecha_compromiso__lt=hoy,
            estado__in=['CONFIRMADO', 'EN_PRODUCCION']
        ).count()
        
        proximos_3_dias = Pedido.objects.filter(
            fecha_compromiso__lte=hoy + timedelta(days=3),
            fecha_compromiso__gte=hoy,
            estado__in=['CONFIRMADO', 'EN_PRODUCCION']
        ).count()
        
        # Mostrar reporte
        self.stdout.write(f"📊 Fecha: {hoy.strftime('%d/%m/%Y')}")
        self.stdout.write(f"📈 Total de pedidos: {total_pedidos}")
        self.stdout.write(f"🆕 Pedidos creados hoy: {pedidos_hoy}")
        self.stdout.write("")
        
        self.stdout.write("📋 Estados:")
        self.stdout.write(f"   • Borradores: {borradores}")
        self.stdout.write(f"   • Confirmados: {confirmados}")
        self.stdout.write(f"   • En Producción: {en_produccion}")
        self.stdout.write(f"   • Producidos: {producidos}")
        self.stdout.write(f"   • Facturados: {facturados}")
        self.stdout.write(f"   • Entregados: {entregados}")
        self.stdout.write(f"   • Cancelados: {cancelados}")
        self.stdout.write("")
        
        if vencidos > 0:
            self.stdout.write(self.style.ERROR(f"⚠️  Pedidos vencidos: {vencidos}"))
        
        if proximos_3_dias > 0:
            self.stdout.write(self.style.WARNING(f"⏰ Vencen en 3 días: {proximos_3_dias}"))
        
        if vencidos == 0 and proximos_3_dias == 0:
            self.stdout.write(self.style.SUCCESS("✓ No hay pedidos vencidos o próximos a vencer"))

    def limpiar_borradores_antiguos(self):
        """Elimina pedidos en borrador con más de 30 días"""
        self.stdout.write(self.style.SUCCESS('=== LIMPIANDO BORRADORES ANTIGUOS ==='))
        
        fecha_limite = timezone.now() - timedelta(days=30)
        
        borradores_antiguos = Pedido.objects.filter(
            estado='BORRADOR',
            creado_en__lt=fecha_limite
        )
        
        count = borradores_antiguos.count()
        
        if count > 0:
            # Mostrar pedidos que serán eliminados
            self.stdout.write(f"📋 Pedidos a eliminar ({count}):")
            for pedido in borradores_antiguos[:10]:  # Mostrar máximo 10
                self.stdout.write(f"   • {pedido.numero_pedido} - {pedido.cliente.razon_social}")
            
            if count > 10:
                self.stdout.write(f"   ... y {count - 10} más")
            
            # Confirmar eliminación
            confirm = input("\n¿Está seguro de eliminar estos pedidos? (sí/no): ")
            
            if confirm.lower() in ['sí', 'si', 'yes', 'y']:
                eliminados = borradores_antiguos.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(f"✓ {eliminados} borradores antiguos eliminados")
                )
            else:
                self.stdout.write(self.style.WARNING("❌ Operación cancelada"))
        else:
            self.stdout.write(
                self.style.SUCCESS("✓ No hay borradores antiguos para eliminar")
            )

    def generar_numeros_faltantes(self):
        """Genera números automáticos para pedidos sin número"""
        self.stdout.write(self.style.SUCCESS('=== GENERANDO NÚMEROS FALTANTES ==='))
        
        pedidos_sin_numero = Pedido.objects.filter(
            Q(numero_pedido__isnull=True) | Q(numero_pedido='')
        ).order_by('creado_en')
        
        count = pedidos_sin_numero.count()
        
        if count > 0:
            self.stdout.write(f"📝 Encontrados {count} pedidos sin número")
            
            actualizados = 0
            for pedido in pedidos_sin_numero:
                nuevo_numero = generar_numero_pedido()
                pedido.numero_pedido = nuevo_numero
                pedido.save()
                
                self.stdout.write(f"   ✓ Pedido ID {pedido.id} → {nuevo_numero}")
                actualizados += 1
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ {actualizados} números generados exitosamente")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("✓ Todos los pedidos tienen número asignado")
            )