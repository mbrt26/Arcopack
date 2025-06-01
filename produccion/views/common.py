# produccion/views/common.py
"""
Vistas comunes para manejo de paros, producción y consumos.
"""

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404
from django.urls import reverse

from ..models import (
    RegistroImpresion, Refilado, Sellado, Doblado, CausaParo,
    ParoImpresion, ParoRefilado, ParoSellado, ParoDoblado
)
from inventario.models import Ubicacion
from ..services import (
    registrar_produccion_rollo_impreso,
    registrar_produccion_rollo_refilado,
    registrar_produccion_bolsas_sellado,
    registrar_produccion_rollo_doblado
)

# =============================================
# === VISTAS ESPECÍFICAS PARA REGISTRAR PAROS ===
# =============================================

@login_required
def iniciar_paro_view(request, proceso_tipo, registro_id):
    """Vista para iniciar un paro en cualquier proceso."""
    if request.method == 'POST':
        causa_paro_id = request.POST.get('causa_paro')
        observaciones = request.POST.get('observaciones', '')
        
        try:
            # Obtener el modelo y registro correcto según el tipo de proceso
            if proceso_tipo == 'impresion':
                registro = get_object_or_404(RegistroImpresion, pk=registro_id, is_active=True)
                ParoImpresion.objects.create(
                    registro_impresion=registro,
                    causa_paro_id=causa_paro_id,
                    hora_inicio_paro=timezone.now().time(),
                    observaciones=observaciones
                )
            elif proceso_tipo == 'refilado':
                registro = get_object_or_404(Refilado, pk=registro_id, is_active=True)
                ParoRefilado.objects.create(
                    refilado=registro,
                    causa_paro_id=causa_paro_id,
                    hora_inicio_paro=timezone.now().time(),
                    observaciones=observaciones
                )
            elif proceso_tipo == 'sellado':
                registro = get_object_or_404(Sellado, pk=registro_id, is_active=True)
                ParoSellado.objects.create(
                    sellado=registro,
                    causa_paro_id=causa_paro_id,
                    hora_inicio_paro=timezone.now().time(),
                    observaciones=observaciones
                )
            elif proceso_tipo == 'doblado':
                registro = get_object_or_404(Doblado, pk=registro_id, is_active=True)
                ParoDoblado.objects.create(
                    doblado=registro,
                    causa_paro_id=causa_paro_id,
                    hora_inicio_paro=timezone.now().time(),
                    observaciones=observaciones
                )
            else:
                messages.error(request, 'Tipo de proceso no válido.')
                return redirect('produccion_web:proceso-list')
            
            messages.success(request, f'Paro iniciado exitosamente en {proceso_tipo}.')
            return redirect(f'produccion_web:{proceso_tipo}-kanban')
            
        except Exception as e:
            messages.error(request, f'Error al iniciar paro: {str(e)}')
            return redirect(f'produccion_web:{proceso_tipo}-kanban')
    
    # GET request - mostrar formulario
    context = {
        'proceso_tipo': proceso_tipo,
        'registro_id': registro_id,
        'causas_paro': CausaParo.objects.filter(is_active=True),
        'page_title': f'Iniciar Paro - {proceso_tipo.title()}'
    }
    return render(request, 'produccion/iniciar_paro_form.html', context)

@login_required
def finalizar_paro_view(request, proceso_tipo, paro_id):
    """Vista para finalizar un paro activo."""
    try:
        # Obtener el paro correcto según el tipo de proceso
        if proceso_tipo == 'impresion':
            paro = get_object_or_404(ParoImpresion, pk=paro_id, hora_final_paro__isnull=True)
        elif proceso_tipo == 'refilado':
            paro = get_object_or_404(ParoRefilado, pk=paro_id, hora_final_paro__isnull=True)
        elif proceso_tipo == 'sellado':
            paro = get_object_or_404(ParoSellado, pk=paro_id, hora_final_paro__isnull=True)
        elif proceso_tipo == 'doblado':
            paro = get_object_or_404(ParoDoblado, pk=paro_id, hora_final_paro__isnull=True)
        else:
            messages.error(request, 'Tipo de proceso no válido.')
            return redirect('produccion_web:proceso-list')
        
        # Finalizar el paro
        paro.hora_final_paro = timezone.now().time()
        paro.save()
        
        messages.success(request, f'Paro finalizado exitosamente en {proceso_tipo}.')
        return redirect(f'produccion_web:{proceso_tipo}-kanban')
        
    except Exception as e:
        messages.error(request, f'Error al finalizar paro: {str(e)}')
        return redirect(f'produccion_web:{proceso_tipo}-kanban')

# =============================================
# === VISTAS PARA REGISTRO DE PRODUCCIÓN POR LOTES ===
# =============================================

class RegistroProduccionView(LoginRequiredMixin, TemplateView):
    """Vista unificada para registrar producción de cualquier proceso."""
    template_name = 'produccion/registro_produccion_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proceso_tipo = self.kwargs.get('proceso_tipo')
        registro_id = self.kwargs.get('registro_id')
        
        # Obtener el registro del proceso correspondiente
        if proceso_tipo == 'impresion':
            registro = get_object_or_404(RegistroImpresion, pk=registro_id, is_active=True)
            context['puede_generar_pt'] = self._es_ultimo_proceso(registro.orden_produccion, 'Impresion')
        elif proceso_tipo == 'refilado':
            registro = get_object_or_404(Refilado, pk=registro_id, is_active=True)
            context['puede_generar_pt'] = self._es_ultimo_proceso(registro.orden_produccion, 'Refilado')
        elif proceso_tipo == 'sellado':
            registro = get_object_or_404(Sellado, pk=registro_id, is_active=True)
            context['puede_generar_pt'] = self._es_ultimo_proceso(registro.orden_produccion, 'Sellado')
        elif proceso_tipo == 'doblado':
            registro = get_object_or_404(Doblado, pk=registro_id, is_active=True)
            context['puede_generar_pt'] = self._es_ultimo_proceso(registro.orden_produccion, 'Doblado')
        else:
            raise Http404("Proceso no válido")
        
        context.update({
            'registro': registro,
            'proceso_tipo': proceso_tipo,
            'page_title': f'Registrar Producción - {proceso_tipo.title()}',
            'ubicaciones': Ubicacion.objects.filter(is_active=True),
            'cancel_url': reverse(f'produccion_web:{proceso_tipo}-kanban')
        })
        
        return context
    
    def _es_ultimo_proceso(self, orden_produccion, proceso_nombre):
        """Determina si el proceso es el último en la secuencia de la OP."""
        try:
            ultimo_proceso = orden_produccion.procesos_secuencia.order_by('-secuencia').first()
            return ultimo_proceso and ultimo_proceso.proceso.nombre == proceso_nombre
        except:
            return False
    
    def post(self, request, *args, **kwargs):
        proceso_tipo = kwargs.get('proceso_tipo')
        registro_id = kwargs.get('registro_id')
        
        try:
            with transaction.atomic():
                if proceso_tipo == 'impresion':
                    resultado = self._registrar_produccion_impresion(request, registro_id)
                elif proceso_tipo == 'refilado':
                    resultado = self._registrar_produccion_refilado(request, registro_id)
                elif proceso_tipo == 'sellado':
                    resultado = self._registrar_produccion_sellado(request, registro_id)
                elif proceso_tipo == 'doblado':
                    resultado = self._registrar_produccion_doblado(request, registro_id)
                else:
                    raise ValueError("Proceso no válido")
                
                messages.success(request, f'Producción registrada exitosamente en {proceso_tipo}.')
                return redirect(f'produccion_web:{proceso_tipo}-kanban')
                    
        except Exception as e:
            messages.error(request, f'Error al registrar producción: {str(e)}')
            return self.get(request, *args, **kwargs)
    
    def _registrar_produccion_impresion(self, request, registro_id):
        """Registra producción para proceso de impresión."""
        registro = get_object_or_404(RegistroImpresion, pk=registro_id, is_active=True)
        
        lote_salida_id = request.POST.get('lote_salida_id')
        kg_producidos = Decimal(request.POST.get('kg_producidos', '0'))
        metros_producidos = request.POST.get('metros_producidos')
        ubicacion_codigo = request.POST.get('ubicacion_destino_codigo')
        observaciones = request.POST.get('observaciones_lote', '')
        
        if metros_producidos:
            metros_producidos = Decimal(metros_producidos)
        
        return registrar_produccion_rollo_impreso(
            registro_impresion=registro,
            lote_salida_id=lote_salida_id,
            kg_producidos=kg_producidos,
            metros_producidos=metros_producidos,
            ubicacion_destino_codigo=ubicacion_codigo,
            usuario=request.user,
            observaciones_lote=observaciones
        )
    
    def _registrar_produccion_refilado(self, request, registro_id):
        """Registra producción para proceso de refilado."""
        registro = get_object_or_404(Refilado, pk=registro_id, is_active=True)
        
        lote_salida_id = request.POST.get('lote_salida_id')
        kg_producidos = Decimal(request.POST.get('kg_producidos', '0'))
        ubicacion_codigo = request.POST.get('ubicacion_destino_codigo')
        observaciones = request.POST.get('observaciones_lote', '')
        
        return registrar_produccion_rollo_refilado(
            refilado=registro,
            lote_salida_id=lote_salida_id,
            kg_producidos=kg_producidos,
            ubicacion_destino_codigo=ubicacion_codigo,
            usuario=request.user,
            observaciones_lote=observaciones
        )
    
    def _registrar_produccion_sellado(self, request, registro_id):
        """Registra producción para proceso de sellado."""
        registro = get_object_or_404(Sellado, pk=registro_id, is_active=True)
        
        lote_salida_id = request.POST.get('lote_salida_id')
        unidades_producidas = int(request.POST.get('unidades_producidas', '0'))
        ubicacion_codigo = request.POST.get('ubicacion_destino_codigo')
        observaciones = request.POST.get('observaciones_lote', '')
        
        return registrar_produccion_bolsas_sellado(
            sellado=registro,
            lote_salida_id=lote_salida_id,
            unidades_producidas=unidades_producidas,
            ubicacion_destino_codigo=ubicacion_codigo,
            usuario=request.user,
            observaciones_lote=observaciones
        )
    
    def _registrar_produccion_doblado(self, request, registro_id):
        """Registra producción para proceso de doblado."""
        registro = get_object_or_404(Doblado, pk=registro_id, is_active=True)
        
        lote_salida_id = request.POST.get('lote_salida_id')
        kg_producidos = Decimal(request.POST.get('kg_producidos', '0'))
        ubicacion_codigo = request.POST.get('ubicacion_destino_codigo')
        observaciones = request.POST.get('observaciones_lote', '')
        
        return registrar_produccion_rollo_doblado(
            doblado=registro,
            lote_salida_id=lote_salida_id,
            kg_producidos=kg_producidos,
            ubicacion_destino_codigo=ubicacion_codigo,
            usuario=request.user,
            observaciones_lote=observaciones
        )

# =============================================
# === VISTAS PARA REGISTRO DE CONSUMOS ===
# =============================================

class RegistroConsumoView(LoginRequiredMixin, TemplateView):
    """Vista unificada para registrar consumos de materiales."""
    template_name = 'produccion/registro_consumo_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proceso_tipo = self.kwargs.get('proceso_tipo')
        registro_id = self.kwargs.get('registro_id')
        
        # Obtener el registro del proceso correspondiente
        if proceso_tipo == 'impresion':
            registro = get_object_or_404(RegistroImpresion, pk=registro_id, is_active=True)
        elif proceso_tipo == 'refilado':
            registro = get_object_or_404(Refilado, pk=registro_id, is_active=True)
        elif proceso_tipo == 'sellado':
            registro = get_object_or_404(Sellado, pk=registro_id, is_active=True)
        elif proceso_tipo == 'doblado':
            registro = get_object_or_404(Doblado, pk=registro_id, is_active=True)
        else:
            raise Http404("Proceso no válido")
        
        context.update({
            'registro': registro,
            'proceso_tipo': proceso_tipo,
            'lotes_mp_disponibles': self._get_lotes_mp_disponibles(registro.orden_produccion),
            'lotes_wip_disponibles': self._get_lotes_wip_disponibles(registro.orden_produccion),
            'page_title': f'Registrar Consumo - {proceso_tipo.title()}',
            'cancel_url': reverse(f'produccion_web:{proceso_tipo}-kanban')
        })
        
        return context
    
    def _get_lotes_mp_disponibles(self, orden_produccion):
        """Obtiene lotes de materia prima disponibles para la orden."""
        from inventario.models import LoteMateriaPrima
        return LoteMateriaPrima.objects.filter(
            cantidad_actual__gt=0,
            producto__in=orden_produccion.producto.componentes.all()
        ).select_related('producto', 'ubicacion')
    
    def _get_lotes_wip_disponibles(self, orden_produccion):
        """Obtiene lotes WIP disponibles para la orden."""
        from inventario.models import LoteProductoEnProceso
        return LoteProductoEnProceso.objects.filter(
            cantidad_actual__gt=0,
            producto=orden_produccion.producto
        ).select_related('producto', 'ubicacion')
    
    def post(self, request, *args, **kwargs):
        proceso_tipo = kwargs.get('proceso_tipo')
        registro_id = kwargs.get('registro_id')
        
        try:
            with transaction.atomic():
                # Lógica para registrar consumos según el proceso
                messages.success(request, f'Consumo registrado exitosamente en {proceso_tipo}.')
                return redirect(f'produccion_web:{proceso_tipo}-kanban')
                
        except Exception as e:
            messages.error(request, f'Error al registrar consumo: {str(e)}')
            return self.get(request, *args, **kwargs)

# =============================================
# === VISTAS PARA GESTIÓN DE DESPERDICIOS ===
# =============================================

class RegistroDesperdicioView(LoginRequiredMixin, TemplateView):
    """Vista unificada para registrar desperdicios."""
    template_name = 'produccion/registro_desperdicio_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proceso_tipo = self.kwargs.get('proceso_tipo')
        registro_id = self.kwargs.get('registro_id')
        
        # Obtener el registro del proceso correspondiente
        if proceso_tipo == 'impresion':
            registro = get_object_or_404(RegistroImpresion, pk=registro_id, is_active=True)
        elif proceso_tipo == 'refilado':
            registro = get_object_or_404(Refilado, pk=registro_id, is_active=True)
        elif proceso_tipo == 'sellado':
            registro = get_object_or_404(Sellado, pk=registro_id, is_active=True)
        elif proceso_tipo == 'doblado':
            registro = get_object_or_404(Doblado, pk=registro_id, is_active=True)
        else:
            raise Http404("Proceso no válido")
        
        context.update({
            'registro': registro,
            'proceso_tipo': proceso_tipo,
            'page_title': f'Registrar Desperdicio - {proceso_tipo.title()}',
            'cancel_url': reverse(f'produccion_web:{proceso_tipo}-kanban')
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        proceso_tipo = kwargs.get('proceso_tipo')
        registro_id = kwargs.get('registro_id')
        
        try:
            with transaction.atomic():
                # Lógica para registrar desperdicios según el proceso
                messages.success(request, f'Desperdicio registrado exitosamente en {proceso_tipo}.')
                return redirect(f'produccion_web:{proceso_tipo}-kanban')
                
        except Exception as e:
            messages.error(request, f'Error al registrar desperdicio: {str(e)}')
            return self.get(request, *args, **kwargs)