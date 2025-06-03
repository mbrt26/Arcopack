from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse
from django.db import transaction

from .base_views import BaseConfiguracionMixin
from .models import (
    Maquina, TipoMaquina, Anilox, TipoTinta,
    Proveedor, Cliente, ConfiguracionGeneral
)

# ===== DASHBOARD Y REPORTES =====
class DashboardView(BaseConfiguracionMixin, TemplateView):
    """Dashboard principal con estadísticas y reportes"""
    template_name = 'configuracion/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Dashboard de Configuración',
            'stats': self.get_dashboard_stats(),
            'recent_activities': self.get_recent_activities(),
            'alerts': self.get_system_alerts()
        })
        return context
    
    def get_dashboard_stats(self):
        """Obtener estadísticas para el dashboard"""
        return {
            'maquinas': {
                'total': Maquina.objects.count(),
                'activas': Maquina.objects.filter(is_active=True).count(),
                'por_tipo': TipoMaquina.objects.annotate(
                    total=Count('maquina')
                ).values('nombre', 'total')
            },
            'proveedores': {
                'total': Proveedor.objects.count(),
                'activos': Proveedor.objects.filter(is_active=True).count()
            }
        }
    
    def get_recent_activities(self):
        """Obtener actividades recientes del sistema"""
        # Implementar lógica de actividades recientes
        return []
    
    def get_system_alerts(self):
        """Obtener alertas del sistema"""
        alerts = []
        # Implementar lógica de alertas
        return alerts

# ===== AJAX ENDPOINTS =====
@login_required
def api_toggle_status(request, model_name, pk):
    """API endpoint genérico para cambiar estado activo/inactivo"""
    model_map = {
        'maquina': Maquina,
        'proveedor': Proveedor,
    }
    
    if model_name not in model_map:
        return JsonResponse({'success': False, 'message': 'Modelo no válido'})
    
    Model = model_map[model_name]
    instance = get_object_or_404(Model, pk=pk)
    
    if not request.user.has_perm(f'configuracion.change_{model_name}'):
        return JsonResponse({'success': False, 'message': 'Permiso denegado'})
    
    instance.is_active = not instance.is_active
    instance.save()
    
    return JsonResponse({
        'success': True,
        'new_status': instance.is_active,
        'message': f'{Model._meta.verbose_name} {"activado" if instance.is_active else "desactivado"} exitosamente'
    })

@login_required
def api_get_related_items(request, model_name, parent_id):
    """API endpoint genérico para obtener items relacionados"""
    model_map = {
        'maquinas': (Maquina, 'tipo_id'),
        # Agregar más modelos según necesidad
    }
    
    if model_name not in model_map:
        return JsonResponse({'success': False, 'message': 'Modelo no válido'})
    
    Model, parent_field = model_map[model_name]
    items = Model.objects.filter(**{parent_field: parent_id})
    
    data = [{
        'id': item.id,
        'nombre': str(item),
        'codigo': getattr(item, 'codigo', None)
    } for item in items]
    
    return JsonResponse({'success': True, 'items': data})

# ===== CONFIGURACIÓN GENERAL =====
class ConfiguracionGeneralView(BaseConfiguracionMixin, TemplateView):
    """Vista para configuración general del sistema"""
    template_name = 'configuracion/configuracion_general.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = ConfiguracionGeneral.get_instance()
        context.update({
            'title': 'Configuración General',
            'config': config,
            'form': ConfiguracionGeneralForm(instance=config)
        })
        return context
    
    def post(self, request, *args, **kwargs):
        config = ConfiguracionGeneral.get_instance()
        form = ConfiguracionGeneralForm(request.POST, instance=config)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada exitosamente')
            return redirect('configuracion_web:configuracion-general')
        
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)

# ===== IMPORTACIÓN/EXPORTACIÓN =====
class ImportExportView(BaseConfiguracionMixin, TemplateView):
    """Vista para importar/exportar datos"""
    template_name = 'configuracion/import_export.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Importar/Exportar Datos'
        context['modelos_disponibles'] = [
            ('maquinas', 'Máquinas'),
            ('proveedores', 'Proveedores'),
            # Agregar más modelos según necesidad
        ]
        return context
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Implementar lógica de importación
        try:
            # Procesar archivo
            messages.success(request, 'Datos importados exitosamente')
        except Exception as e:
            messages.error(request, f'Error al importar datos: {str(e)}')
        
        return redirect('configuracion_web:import-export')