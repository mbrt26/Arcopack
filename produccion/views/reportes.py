# produccion/views/reportes.py
"""
Vistas para reportes y análisis de producción.
"""

from decimal import Decimal
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType

from ..models import OrdenProduccion, RegistroImpresion, Refilado, Sellado, Doblado
from inventario.models import LoteProductoTerminado, LoteProductoEnProceso
from configuracion.models import Proceso

class ProcesoListView(LoginRequiredMixin, ListView):
    """Vista para listar procesos disponibles."""
    model = Proceso
    template_name = 'produccion/proceso_list.html'
    context_object_name = 'procesos'
    
    def get_queryset(self):
        return Proceso.objects.filter(is_active=True).order_by('secuencia_estandar')

class ResultadosProduccionView(LoginRequiredMixin, TemplateView):
    """Vista para mostrar resultados y KPIs de producción."""
    template_name = 'produccion/resultados_produccion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de filtro
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        proceso_id = self.request.GET.get('proceso_id')
        
        # Datos de resumen por proceso
        procesos_data = []
        procesos = Proceso.objects.filter(is_active=True)
        
        if proceso_id:
            procesos = procesos.filter(id=proceso_id)
            
        for proceso in procesos:
            proceso_data = {
                'proceso': proceso,
                'total_registros': 0,
                'total_produccion': 0,
                'total_consumo': 0,
                'eficiencia_promedio': 0
            }
            
            # Calcular datos según el tipo de proceso
            if proceso.nombre.lower() == 'impresion':
                registros = RegistroImpresion.objects.filter(is_active=True)
                if fecha_inicio:
                    registros = registros.filter(fecha_registro__gte=fecha_inicio)
                if fecha_fin:
                    registros = registros.filter(fecha_registro__lte=fecha_fin)
                    
                proceso_data['total_registros'] = registros.count()
                # Agregar más cálculos específicos aquí
                
            elif proceso.nombre.lower() == 'refilado':
                registros = Refilado.objects.filter(is_active=True)
                if fecha_inicio:
                    registros = registros.filter(fecha_registro__gte=fecha_inicio)
                if fecha_fin:
                    registros = registros.filter(fecha_registro__lte=fecha_fin)
                    
                proceso_data['total_registros'] = registros.count()
                
            elif proceso.nombre.lower() == 'sellado':
                registros = Sellado.objects.filter(is_active=True)
                if fecha_inicio:
                    registros = registros.filter(fecha_registro__gte=fecha_inicio)
                if fecha_fin:
                    registros = registros.filter(fecha_registro__lte=fecha_fin)
                    
                proceso_data['total_registros'] = registros.count()
                
            elif proceso.nombre.lower() == 'doblado':
                registros = Doblado.objects.filter(is_active=True)
                if fecha_inicio:
                    registros = registros.filter(fecha_registro__gte=fecha_inicio)
                if fecha_fin:
                    registros = registros.filter(fecha_registro__lte=fecha_fin)
                    
                proceso_data['total_registros'] = registros.count()
            
            procesos_data.append(proceso_data)
        
        context.update({
            'procesos_data': procesos_data,
            'procesos_para_filtro': Proceso.objects.filter(is_active=True),
            'filtros': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'proceso_id': proceso_id
            },
            'page_title': 'Resultados de Producción'
        })
        
        return context

class ResumenProduccionView(LoginRequiredMixin, TemplateView):
    """Vista para mostrar resumen de producción por orden y proceso."""
    template_name = 'produccion/resumen_produccion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de filtro
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        orden_id = self.request.GET.get('orden_id')
        proceso = self.request.GET.get('proceso')
        
        # Construir queryset base
        ordenes = OrdenProduccion.objects.filter(is_active=True).select_related(
            'cliente', 'producto'
        ).prefetch_related(
            'registros_impresion',
            'registros_refilado', 
            'registros_sellado',
            'registros_doblado'
        )
        
        # Aplicar filtros
        if orden_id:
            ordenes = ordenes.filter(pk=orden_id)
        
        if fecha_inicio:
            ordenes = ordenes.filter(fecha_creacion__gte=fecha_inicio)
        
        if fecha_fin:
            ordenes = ordenes.filter(fecha_creacion__lte=fecha_fin)
        
        # Preparar datos de resumen
        resumen_data = []
        for orden in ordenes[:50]:  # Limitar para performance
            orden_data = {
                'orden': orden,
                'procesos': {}
            }
            
            # Datos de impresión
            if not proceso or proceso == 'impresion':
                orden_data['procesos']['impresion'] = self._get_datos_impresion(orden)
            
            # Datos de refilado
            if not proceso or proceso == 'refilado':
                orden_data['procesos']['refilado'] = self._get_datos_refilado(orden)
            
            # Datos de sellado
            if not proceso or proceso == 'sellado':
                orden_data['procesos']['sellado'] = self._get_datos_sellado(orden)
            
            # Datos de doblado
            if not proceso or proceso == 'doblado':
                orden_data['procesos']['doblado'] = self._get_datos_doblado(orden)
            
            if orden_data['procesos']:  # Solo agregar si tiene datos de procesos
                resumen_data.append(orden_data)
        
        context.update({
            'resumen_data': resumen_data,
            'ordenes_para_filtro': OrdenProduccion.objects.filter(is_active=True).values('id', 'op_numero'),
            'filtros': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'orden_id': orden_id,
                'proceso': proceso
            },
            'page_title': 'Resumen de Producción'
        })
        
        return context
    
    def _get_datos_impresion(self, orden):
        """Obtiene datos de producción para el proceso de impresión."""
        registros_imp = orden.registros_impresion.all()
        if not registros_imp:
            return None
            
        total_prod_imp = 0
        total_consumo_imp = 0
        
        for reg in registros_imp:
            # Calcular producción
            ct = ContentType.objects.get_for_model(RegistroImpresion)
            lotes_pt = LoteProductoTerminado.objects.filter(
                proceso_final_content_type=ct,
                proceso_final_object_id=reg.pk
            )
            lotes_wip = LoteProductoEnProceso.objects.filter(
                proceso_origen_content_type=ct,
                proceso_origen_object_id=reg.pk
            )
            total_prod_imp += sum([lote.cantidad_actual for lote in lotes_pt]) + sum([lote.cantidad_actual for lote in lotes_wip])
            total_consumo_imp += sum([c.cantidad_kg_consumida for c in reg.consumos_sustrato.all()])
        
        return {
            'registros': len(registros_imp),
            'produccion_kg': total_prod_imp,
            'consumo_kg': total_consumo_imp,
            'eficiencia': (total_prod_imp / total_consumo_imp * 100) if total_consumo_imp > 0 else 0
        }
    
    def _get_datos_refilado(self, orden):
        """Obtiene datos de producción para el proceso de refilado."""
        registros_ref = orden.registros_refilado.all()
        if not registros_ref:
            return None
            
        total_prod_ref = 0
        total_consumo_ref = 0
        
        for reg in registros_ref:
            ct = ContentType.objects.get_for_model(Refilado)
            lotes = LoteProductoEnProceso.objects.filter(
                proceso_origen_content_type=ct,
                proceso_origen_object_id=reg.pk
            )
            total_prod_ref += sum([lote.cantidad_actual for lote in lotes])
            total_consumo_ref += sum([c.cantidad_kg_consumida for c in reg.consumos_wip_refilado.all()])
        
        return {
            'registros': len(registros_ref),
            'produccion_kg': total_prod_ref,
            'consumo_kg': total_consumo_ref,
            'eficiencia': (total_prod_ref / total_consumo_ref * 100) if total_consumo_ref > 0 else 0
        }
    
    def _get_datos_sellado(self, orden):
        """Obtiene datos de producción para el proceso de sellado."""
        registros_sell = orden.registros_sellado.all()
        if not registros_sell:
            return None
            
        total_prod_sell = 0
        total_consumo_sell = 0
        
        for reg in registros_sell:
            ct = ContentType.objects.get_for_model(Sellado)
            lotes = LoteProductoTerminado.objects.filter(
                proceso_final_content_type=ct,
                proceso_final_object_id=reg.pk
            )
            total_prod_sell += sum([lote.cantidad_actual for lote in lotes])
            total_consumo_sell += sum([c.cantidad_kg_consumida for c in reg.consumos_wip_sellado.all()])
        
        return {
            'registros': len(registros_sell),
            'produccion_unidades': total_prod_sell,
            'consumo_kg': total_consumo_sell
        }
    
    def _get_datos_doblado(self, orden):
        """Obtiene datos de producción para el proceso de doblado."""
        registros_dobl = orden.registros_doblado.all()
        if not registros_dobl:
            return None
            
        total_prod_dobl = 0
        total_consumo_dobl = 0
        
        for reg in registros_dobl:
            ct = ContentType.objects.get_for_model(Doblado)
            lotes = LoteProductoEnProceso.objects.filter(
                proceso_origen_content_type=ct,
                proceso_origen_object_id=reg.pk
            )
            total_prod_dobl += sum([lote.cantidad_actual for lote in lotes])
            total_consumo_dobl += sum([c.cantidad_kg_consumida for c in reg.consumos_wip_doblado.all()])
        
        return {
            'registros': len(registros_dobl),
            'produccion_kg': total_prod_dobl,
            'consumo_kg': total_consumo_dobl,
            'eficiencia': (total_prod_dobl / total_consumo_dobl * 100) if total_consumo_dobl > 0 else 0
        }