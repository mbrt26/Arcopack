# produccion/views/impresion.py
"""
Vistas específicas para el proceso de Impresión.
Incluye vistas HTML, ViewSets y acciones específicas para el proceso de impresión.
"""

import json
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import ListView
from django.contrib import messages
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .base import (
    BaseProduccionViewSet, BaseProduccionCreateView, BaseProduccionUpdateView, 
    BaseProduccionDetailView, ValidationError, logger
)
from ..models import (
    RegistroImpresion, ParoImpresion, DesperdicioImpresion,
    ConsumoTintaImpresion, ConsumoSustratoImpresion
)
from configuracion.models import CausaParo, Maquina
from ..serializers import (
    RegistroImpresionSerializer, ConsumoImpresionSerializer, ProduccionImpresionSerializer
)
from ..forms import (
    RegistroImpresionForm, ParoImpresionFormset, DesperdicioImpresionFormset,
    ConsumoTintaImpresionFormset, ConsumoSustratoImpresionFormset, ProduccionImpresionFormset
)
from ..services import consumir_sustrato_impresion, registrar_produccion_rollo_impreso
from inventario.models import LoteProductoTerminado, LoteProductoEnProceso


# =============================================
# === VISTAS HTML PARA IMPRESIÓN ===
# =============================================

class RegistroImpresionCreateView(BaseProduccionCreateView):
    """Vista para crear un nuevo registro de impresión."""
    model = RegistroImpresion
    form_class = RegistroImpresionForm
    template_name = 'produccion/registro_impresion_form.html'
    success_url = reverse_lazy('produccion_web:registro-impresion-list')
    
    def form_valid(self, form):
        """Maneja la validación del formulario y los datos JSON de los formsets dinámicos."""
        # Obtener los datos JSON enviados desde JavaScript
        paros_data = self.request.POST.get('paros_data', '[]')
        desperdicios_data = self.request.POST.get('desperdicios_data', '[]')
        consumos_tinta_data = self.request.POST.get('consumos_tinta_data', '[]')
        consumos_sustrato_data = self.request.POST.get('consumos_sustrato_data', '[]')
        
        # Registrar información de depuración
        logger.info(f"Datos recibidos en form_valid de RegistroImpresionCreateView:")
        logger.info(f"- Paros: {paros_data}")
        logger.info(f"- Desperdicios: {desperdicios_data}")
        logger.info(f"- Consumos de tinta: {consumos_tinta_data}")
        logger.info(f"- Consumos de sustrato: {consumos_sustrato_data}")
        
        try:
            # Guardar el formulario principal dentro de una transacción
            with transaction.atomic():
                # Guardar el formulario principal
                self.object = form.save()
                logger.info(f"Objeto principal guardado: {self.object}")
                
                # Procesar los datos JSON
                self.procesar_datos_json(paros_data, desperdicios_data, consumos_tinta_data, consumos_sustrato_data)
            
            messages.success(
                self.request, 
                f'Registro de impresión creado exitosamente.'
            )
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            logger.exception(f"Error en form_valid de RegistroImpresionCreateView: {str(e)}")
            messages.error(self.request, f"Error al guardar el registro: {str(e)}")
            return self.form_invalid(form)

    
    def procesar_datos_json(self, paros_data, desperdicios_data, consumos_tinta_data, consumos_sustrato_data):
        """Procesa los datos JSON recibidos desde el formulario."""
        try:
            # Convertir los datos JSON a objetos Python
            paros = json.loads(paros_data)
            desperdicios = json.loads(desperdicios_data)
            consumos_tinta = json.loads(consumos_tinta_data)
            consumos_sustrato = json.loads(consumos_sustrato_data)
            
            # Procesar paros
            for paro in paros:
                ParoImpresion.objects.create(
                    registro_impresion=self.object,
                    hora_inicio=paro.get('horaInicio'),
                    hora_fin=paro.get('horaFin'),
                    motivo=paro.get('motivo'),
                    observaciones=paro.get('observaciones', '')
                )
            
            # Procesar desperdicios
            for desperdicio in desperdicios:
                DesperdicioImpresion.objects.create(
                    registro_impresion=self.object,
                    tipo_material=desperdicio.get('tipoMaterial'),
                    cantidad=desperdicio.get('cantidad'),
                    motivo=desperdicio.get('motivo'),
                    observaciones=desperdicio.get('observaciones', '')
                )
            
            # Procesar consumos de tinta
            for consumo in consumos_tinta:
                ConsumoTintaImpresion.objects.create(
                    registro_impresion=self.object,
                    tipo_tinta=consumo.get('tipoTinta'),
                    cantidad=consumo.get('cantidad'),
                    lote_proveedor=consumo.get('loteProveedor', ''),
                    observaciones=consumo.get('observaciones', '')
                )
            
            # Procesar consumos de sustrato
            for consumo in consumos_sustrato:
                ConsumoSustratoImpresion.objects.create(
                    registro_impresion=self.object,
                    tipo_sustrato=consumo.get('tipoSustrato'),
                    cantidad=consumo.get('cantidad'),
                    ancho=consumo.get('ancho'),
                    observaciones=consumo.get('observaciones', '')
                )
                
            logger.info(f"Datos JSON procesados correctamente para el registro {self.object.pk}")
        except Exception as e:
            logger.exception(f"Error al procesar datos JSON: {str(e)}")
            raise
    
    def get_formsets(self, context):
        """Define los formsets específicos para impresión.
        
        Nota: Estos formsets son solo para mostrar en la plantilla, pero no se usarán para procesar los datos.
        Los datos se procesarán directamente desde los campos JSON enviados desde JavaScript.
        """
        # No usamos los datos POST para los formsets, ya que los procesaremos manualmente
        # Esto evita errores de validación en los formsets
        
        # Para CreateView, no pasamos instance ya que self.object es None
        if hasattr(self, 'object') and self.object:
            # UpdateView - tenemos una instancia, pero usamos None como data
            return {
                'paro_formset': ParoImpresionFormset(None, instance=self.object, prefix='paro_formset'),
                'desperdicio_formset': DesperdicioImpresionFormset(None, instance=self.object, prefix='desperdicio_formset'),
                'consumo_tinta_formset': ConsumoTintaImpresionFormset(None, instance=self.object, prefix='consumo_tinta_formset'),
                'consumo_sustrato_formset': ConsumoSustratoImpresionFormset(None, instance=self.object, prefix='consumo_sustrato_formset'),
                'produccion_formset': ProduccionImpresionFormset(None, instance=self.object, prefix='produccion_formset'),
            }
        else:
            # CreateView - no tenemos instancia aún, usamos None como data
            return {
                'paro_formset': ParoImpresionFormset(None, prefix='paro_formset'),
                'desperdicio_formset': DesperdicioImpresionFormset(None, prefix='desperdicio_formset'),
                'consumo_tinta_formset': ConsumoTintaImpresionFormset(None, prefix='consumo_tinta_formset'),
                'consumo_sustrato_formset': ConsumoSustratoImpresionFormset(None, prefix='consumo_sustrato_formset'),
                'produccion_formset': ProduccionImpresionFormset(None, prefix='produccion_formset'),
            }
    
    def get_proceso_name(self):
        return "impresión"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar los formsets al contexto
        formsets = self.get_formsets(context)
        context.update({
            'page_title': 'Nuevo Registro de Impresión',
            'form_action': 'Crear',
            'causas_paro': CausaParo.objects.all(),  # Agregar causas de paro al contexto
            **formsets  # Agregar todos los formsets al contexto
        })
        return context


class RegistroImpresionListView(ListView):
    """Vista para listar todos los registros de impresión."""
    model = RegistroImpresion
    template_name = 'produccion/registro_impresion_list.html'
    context_object_name = 'registros'
    
    def get_queryset(self):
        """Obtener todos los registros activos ordenados por fecha y hora."""
        return RegistroImpresion.objects.filter(
            is_active=True
        ).select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        ).order_by('-fecha', '-hora_inicio')


class RegistroImpresionUpdateView(BaseProduccionUpdateView):
    """Vista para actualizar un registro de impresión existente."""
    model = RegistroImpresion
    form_class = RegistroImpresionForm
    template_name = 'produccion/registro_impresion_form.html'
    success_url = reverse_lazy('produccion_web:registro-impresion-list')
    
    def form_valid(self, form):
        """Maneja la validación del formulario y los datos JSON de los formsets dinámicos."""
        # Obtener los datos JSON enviados desde JavaScript
        paros_data = self.request.POST.get('paros_data', '[]')
        desperdicios_data = self.request.POST.get('desperdicios_data', '[]')
        consumos_tinta_data = self.request.POST.get('consumos_tinta_data', '[]')
        consumos_sustrato_data = self.request.POST.get('consumos_sustrato_data', '[]')
        
        # Registrar información de depuración
        logger.info(f"Datos recibidos en form_valid de RegistroImpresionUpdateView:")
        logger.info(f"- Paros: {paros_data}")
        logger.info(f"- Desperdicios: {desperdicios_data}")
        logger.info(f"- Consumos de tinta: {consumos_tinta_data}")
        logger.info(f"- Consumos de sustrato: {consumos_sustrato_data}")
        
        try:
            # Guardar el formulario principal dentro de una transacción
            with transaction.atomic():
                # Guardar el formulario principal
                self.object = form.save()
                logger.info(f"Objeto principal actualizado: {self.object}")
                
                # Eliminar registros existentes que fueron creados manualmente
                # Esto evita duplicados cuando se envían datos JSON
                self.limpiar_registros_manuales()
                
                # Procesar los nuevos datos JSON
                self.procesar_datos_json(paros_data, desperdicios_data, consumos_tinta_data, consumos_sustrato_data)
            
            messages.success(
                self.request, 
                f'Registro de impresión actualizado exitosamente.'
            )
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            logger.exception(f"Error en form_valid de RegistroImpresionUpdateView: {str(e)}")
            messages.error(self.request, f"Error al actualizar el registro: {str(e)}")
            return self.form_invalid(form)

    
    def limpiar_registros_manuales(self):
        """Elimina los registros que fueron creados manualmente (no a través de formsets)."""
        try:
            # Obtener IDs de registros creados por formsets para preservarlos
            paro_formset = ParoImpresionFormset(instance=self.object, prefix='paro_formset')
            desperdicio_formset = DesperdicioImpresionFormset(instance=self.object, prefix='desperdicio_formset')
            consumo_tinta_formset = ConsumoTintaImpresionFormset(instance=self.object, prefix='consumo_tinta_formset')
            consumo_sustrato_formset = ConsumoSustratoImpresionFormset(instance=self.object, prefix='consumo_sustrato_formset')
            
            # Obtener IDs de registros en formsets
            paro_ids = [form.instance.pk for form in paro_formset if form.instance.pk]
            desperdicio_ids = [form.instance.pk for form in desperdicio_formset if form.instance.pk]
            consumo_tinta_ids = [form.instance.pk for form in consumo_tinta_formset if form.instance.pk]
            consumo_sustrato_ids = [form.instance.pk for form in consumo_sustrato_formset if form.instance.pk]
            
            # Eliminar registros que no están en los formsets (creados manualmente)
            ParoImpresion.objects.filter(registro_impresion=self.object).exclude(pk__in=paro_ids).delete()
            DesperdicioImpresion.objects.filter(registro_impresion=self.object).exclude(pk__in=desperdicio_ids).delete()
            ConsumoTintaImpresion.objects.filter(registro_impresion=self.object).exclude(pk__in=consumo_tinta_ids).delete()
            ConsumoSustratoImpresion.objects.filter(registro_impresion=self.object).exclude(pk__in=consumo_sustrato_ids).delete()
            
            logger.info(f"Registros manuales eliminados para el registro {self.object.pk}")
        except Exception as e:
            logger.exception(f"Error al limpiar registros manuales: {str(e)}")
            raise
    
    def procesar_datos_json(self, paros_data, desperdicios_data, consumos_tinta_data, consumos_sustrato_data):
        """Procesa los datos JSON recibidos desde el formulario."""
        try:
            # Convertir los datos JSON a objetos Python
            paros = json.loads(paros_data)
            desperdicios = json.loads(desperdicios_data)
            consumos_tinta = json.loads(consumos_tinta_data)
            consumos_sustrato = json.loads(consumos_sustrato_data)
            
            # Procesar paros
            for paro in paros:
                ParoImpresion.objects.create(
                    registro_impresion=self.object,
                    hora_inicio=paro.get('horaInicio'),
                    hora_fin=paro.get('horaFin'),
                    motivo=paro.get('motivo'),
                    observaciones=paro.get('observaciones', '')
                )
            
            # Procesar desperdicios
            for desperdicio in desperdicios:
                DesperdicioImpresion.objects.create(
                    registro_impresion=self.object,
                    tipo_material=desperdicio.get('tipoMaterial'),
                    cantidad=desperdicio.get('cantidad'),
                    motivo=desperdicio.get('motivo'),
                    observaciones=desperdicio.get('observaciones', '')
                )
            
            # Procesar consumos de tinta
            for consumo in consumos_tinta:
                ConsumoTintaImpresion.objects.create(
                    registro_impresion=self.object,
                    tipo_tinta=consumo.get('tipoTinta'),
                    cantidad=consumo.get('cantidad'),
                    lote_proveedor=consumo.get('loteProveedor', ''),
                    observaciones=consumo.get('observaciones', '')
                )
            
            # Procesar consumos de sustrato
            for consumo in consumos_sustrato:
                ConsumoSustratoImpresion.objects.create(
                    registro_impresion=self.object,
                    tipo_sustrato=consumo.get('tipoSustrato'),
                    cantidad=consumo.get('cantidad'),
                    ancho=consumo.get('ancho'),
                    observaciones=consumo.get('observaciones', '')
                )
                
            logger.info(f"Datos JSON procesados correctamente para el registro {self.object.pk}")
        except Exception as e:
            logger.exception(f"Error al procesar datos JSON: {str(e)}")
            raise
    
    def get_formsets(self, context):
        """Define los formsets específicos para impresión.
        
        Nota: Estos formsets son solo para mostrar en la plantilla, pero no se usarán para procesar los datos.
        Los datos se procesarán directamente desde los campos JSON enviados desde JavaScript.
        """
        # No usamos los datos POST para los formsets, ya que los procesaremos manualmente
        # Esto evita errores de validación en los formsets
        return {
            'paro_formset': ParoImpresionFormset(None, instance=self.object, prefix='paro_formset'),
            'desperdicio_formset': DesperdicioImpresionFormset(None, instance=self.object, prefix='desperdicio_formset'),
            'consumo_tinta_formset': ConsumoTintaImpresionFormset(None, instance=self.object, prefix='consumo_tinta_formset'),
            'consumo_sustrato_formset': ConsumoSustratoImpresionFormset(None, instance=self.object, prefix='consumo_sustrato_formset'),
            'produccion_formset': ProduccionImpresionFormset(None, instance=self.object, prefix='produccion_formset'),
        }
    
    def get_proceso_name(self):
        return "impresión"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': f'Editar Registro de Impresión - {self.object.orden_produccion.op_numero}',
            'form_action': 'Actualizar',
            'causas_paro': CausaParo.objects.all(),  # Agregar causas de paro al contexto
            **self.get_formsets(context)
        })
        return context


class RegistroImpresionDetailView(BaseProduccionDetailView):
    """Vista para mostrar detalles de un registro de impresión."""
    template_name = 'produccion/registro_impresion_detail.html'
    
    def get_queryset(self):
        return RegistroImpresion.objects.select_related(
            'orden_produccion', 'maquina', 'operario_principal'
        ).prefetch_related(
            'paros_impresion', 'desperdicios_impresion', 'consumo_tintas',
            'consumos_sustrato'
        )
    
    def get_lotes_producidos(self, registro):
        """Obtiene información de lotes producidos en impresión."""
        from django.contrib.contenttypes.models import ContentType
        from inventario.models import LoteProductoEnProceso, LoteProductoTerminado
        
        # Obtener el ContentType para RegistroImpresion
        ct = ContentType.objects.get_for_model(registro.__class__)
        
        # Buscar lotes WIP que tienen a este registro como proceso_origen
        lotes_wip = LoteProductoEnProceso.objects.filter(
            proceso_origen_content_type=ct,
            proceso_origen_object_id=registro.id
        ).select_related('ubicacion', 'producto_terminado')
        
        # Buscar lotes PT que tienen a este registro como proceso_origen
        lotes_pt = LoteProductoTerminado.objects.filter(
            proceso_final_content_type=ct,
            proceso_final_object_id=registro.id
        ).select_related('ubicacion', 'producto_terminado')
        
        # Convertir a lista de diccionarios para usar en calculate_totales
        lotes_data = [
            {
                'tipo': 'WIP',
                'lote_id': lote.lote_id,
                'cantidad_producida': lote.cantidad_producida_primaria
            } for lote in lotes_wip
        ] + [
            {
                'tipo': 'PT',
                'lote_id': lote.lote_id,
                'cantidad_producida': lote.cantidad_producida
            } for lote in lotes_pt
        ]
        
        return {
            'lotes_wip': lotes_wip,
            'lotes_pt': lotes_pt,
            'lotes_data': lotes_data,
            'total_lotes': lotes_wip.count() + lotes_pt.count()
        }
    
    def calculate_totales(self, registro, lotes_data):
        """Calcula totales específicos para impresión."""
        # Calcular total de sustrato consumido
        total_sustrato_kg = sum(
            consumo.cantidad_kg_consumida for consumo in registro.consumos_sustrato.all()
        )
        
        # Calcular total de tinta consumida
        total_tinta_kg = sum(
            consumo.cantidad_kg for consumo in registro.consumo_tintas.all()
        )
        
        # Calcular total producido - usando lotes_data['lotes_data'] de get_lotes_producidos
        # Los lotes de producción están asociados mediante GenericForeignKey
        total_producido_kg = sum(
            lote.get('cantidad_producida', 0) for lote in lotes_data.get('lotes_data', [])
        )
        
        # Calcular total de desperdicio
        total_desperdicio = sum(
            desperdicio.cantidad_kg for desperdicio in registro.desperdicios_impresion.all()
        )
        
        # Calcular eficiencia de material
        eficiencia_material = (total_producido_kg / total_sustrato_kg * 100) if total_sustrato_kg > 0 else 0
        
        return {
            'total_sustrato_kg': total_sustrato_kg,
            'total_tinta_kg': total_tinta_kg,
            'total_producido_kg': total_producido_kg,
            'total_desperdicio': total_desperdicio,
            'eficiencia_material': round(eficiencia_material, 2),
        }
    
    def get_proceso_name(self):
        return "impresión"


# =============================================
# === VIEWSET PARA REGISTRO DE IMPRESIÓN ===
# =============================================

class RegistroImpresionViewSet(BaseProduccionViewSet):
    """ViewSet para Registros de Impresión."""
    queryset = RegistroImpresion.objects.filter(is_active=True).select_related(
        'orden_produccion', 'maquina', 'operario_principal'
    )
    serializer_class = RegistroImpresionSerializer

    @action(detail=True, methods=['post'], url_path='consumir-sustrato')
    def consumir_sustrato(self, request, pk=None):
        """Acción para consumir sustrato en el proceso de impresión."""
        registro = self.get_object()
        serializer = ConsumoImpresionSerializer(
            data=request.data,
            context={'registro_impresion': registro}  # Pasar el registro para filtrar lotes
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = consumir_sustrato_impresion(
                        registro_impresion=registro,
                        lote_sustrato_id=serializer.validated_data['lote_consumido'].lote_id,
                        cantidad_kg=serializer.validated_data['cantidad_kg'],
                        usuario=request.user
                    )
                return Response({
                    'status': 'success',
                    'message': f'Consumo registrado exitosamente. Lote: {lote.lote_id}'
                }, status=status.HTTP_200_OK)
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.exception(f"Error inesperado en consumir_sustrato: {e}")
                return Response({
                    'status': 'error',
                    'message': 'Error interno del servidor'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='registrar-produccion')
    def registrar_produccion(self, request, pk=None):
        """Acción para registrar producción del proceso de impresión."""
        registro = self.get_object()
        serializer = ProduccionImpresionSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    lote = registrar_produccion_rollo_impreso(
                        registro_impresion=registro,
                        lote_salida_id=serializer.validated_data['lote_salida_id'],
                        kg_producidos=serializer.validated_data['kg_producidos'],
                        metros_producidos=serializer.validated_data.get('metros_producidos'),
                        ubicacion_destino_codigo=serializer.validated_data['ubicacion_destino_codigo'],
                        usuario=request.user,
                        observaciones_lote=serializer.validated_data.get('observaciones_lote', '')
                    )
                
                tipo_lote = 'PT' if isinstance(lote, LoteProductoTerminado) else 'WIP'
                return Response({
                    'status': 'success',
                    'message': f'Producción registrada exitosamente. Lote: {lote.lote_id}',
                    'tipo_lote': tipo_lote,
                    'lote_creado_id': lote.lote_id,
                    'detalle': 'El tipo de lote (WIP/PT) se determina automáticamente según la secuencia de procesos de la OP.'
                }, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.exception(f"Error inesperado en registrar_produccion: {e}")
                return Response({
                    'status': 'error',
                    'message': 'Error interno del servidor'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)