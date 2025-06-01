# produccion/views/base.py
"""
Vistas base y comunes para la app de producción.
Contiene importaciones, configuraciones y vistas generales.
"""

import logging
from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, CreateView, UpdateView, ListView
from django.db import models, transaction
from django.db.models import Q, F, Case, When, Value, BooleanField
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth import get_user_model

# Importar modelos
from configuracion.models import Proceso
from ..models import OrdenProduccion, RegistroImpresion, Refilado, Sellado, Doblado

# Importar formularios
from ..forms import (
    OrdenProduccionForm, RegistroImpresionForm, ParoImpresionFormset,
    DesperdicioImpresionFormset, ConsumoTintaImpresionFormset,
    ConsumoSustratoImpresionFormset, RegistroRefiladoForm,
    ParoRefiladoFormset, ConsumoWipRefiladoFormset, ProduccionImpresionFormset,
    ProduccionRefiladoFormSet, RegistroSelladoForm, ParoSelladoFormset,
    ConsumoWipSelladoFormset, ProduccionSelladoFormSet, RegistroDobladoForm,
    ParoDobladoFormset, ConsumoWipDobladoFormset, ProduccionDobladoFormSet
)

# Importar Serializers
from ..serializers import (
    OrdenProduccionSerializer,
    RegistroImpresionSerializer, ConsumoImpresionSerializer, ProduccionImpresionSerializer,
    RefiladoSerializer, ConsumoWipRefiladoSerializer, ConsumoMpRefiladoSerializer, ProduccionRefiladoSerializer,
    SelladoSerializer, ConsumoWipSelladoSerializer, ConsumoMpSelladoSerializer, ProduccionSelladoSerializer,
    DobladoSerializer, ConsumoWipDobladoSerializer, ConsumoMpDobladoSerializer, ProduccionDobladoSerializer,
    LoteMateriaPrimaSerializer, LoteProductoEnProcesoSerializer,
)

# Importar funciones de servicio
from ..services import (
    # Impresión
    consumir_sustrato_impresion, registrar_produccion_rollo_impreso,
    # Refilado
    consumir_rollo_entrada_refilado, consumir_mp_refilado, registrar_produccion_rollo_refilado,
    # Sellado
    consumir_rollo_entrada_sellado, consumir_mp_sellado, registrar_produccion_bolsas_sellado,
    # Doblado
    consumir_rollo_entrada_doblado, consumir_mp_doblado, registrar_produccion_rollo_doblado,
)

# Importar modelos de inventario para type hints/checks
from inventario.models import LoteProductoEnProceso, LoteProductoTerminado, LoteMateriaPrima

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseProduccionViewSet(viewsets.ModelViewSet):
    """ViewSet base para todos los procesos de producción."""
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Asigna usuario creador y actualizador."""
        serializer.save(
            creado_por=self.request.user, 
            actualizado_por=self.request.user
        )

    def perform_update(self, serializer):
        """Asigna usuario actualizador."""
        serializer.save(actualizado_por=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete: Marca como inactivo."""
        if hasattr(instance, 'is_active') and instance.is_active:
            instance.is_active = False
            instance.save(user=self.request.user)
            logger.info(f"Registro '{instance}' desactivado por usuario '{self.request.user}'.")


class BaseProduccionCreateView(LoginRequiredMixin, CreateView):
    """Vista base para crear registros de producción."""
    
    def form_valid(self, form):
        """Maneja la validación del formulario principal y formsets relacionados."""
        context = self.get_context_data()
        formsets = self.get_formsets(context)
        
        # Validar todos los formsets
        all_valid = all(formset.is_valid() for formset in formsets.values())
        
        if all_valid:
            with transaction.atomic():
                self.object = form.save()
                
                # Guardar todos los formsets
                for formset_name, formset in formsets.items():
                    formset.instance = self.object
                    formset.save()
                    
                    # Lógica especial para formsets de producción
                    if 'produccion' in formset_name:
                        setattr(formset, f'registro_{self.get_proceso_name()}', self.object)
                        formset.save()
            
            messages.success(
                self.request, 
                f'Registro de {self.get_proceso_name()} creado exitosamente.'
            )
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_formsets(self, context):
        """Método a sobrescribir por cada vista específica."""
        return {}
    
    def get_proceso_name(self):
        """Método a sobrescribir por cada vista específica."""
        return "producción"


class BaseProduccionUpdateView(LoginRequiredMixin, UpdateView):
    """Vista base para actualizar registros de producción."""
    
    def get_queryset(self):
        return self.model.objects.filter(is_active=True)
    
    def form_valid(self, form):
        """Maneja la validación del formulario principal y formsets relacionados."""
        context = self.get_context_data()
        formsets = self.get_formsets(context)
        
        # Validar todos los formsets
        all_valid = all(formset.is_valid() for formset in formsets.values())
        
        if all_valid:
            with transaction.atomic():
                self.object = form.save()
                
                # Guardar todos los formsets
                for formset_name, formset in formsets.items():
                    formset.instance = self.object
                    formset.save()
            
            messages.success(
                self.request, 
                f'Registro de {self.get_proceso_name()} actualizado exitosamente.'
            )
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_formsets(self, context):
        """Método a sobrescribir por cada vista específica."""
        return {}
    
    def get_proceso_name(self):
        """Método a sobrescribir por cada vista específica."""
        return "producción"


class BaseProduccionDetailView(LoginRequiredMixin, TemplateView):
    """Vista base para mostrar detalles de registros de producción."""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registro_id = kwargs.get('pk')
        
        # Obtener el registro con relaciones optimizadas
        registro = get_object_or_404(
            self.get_queryset(),
            pk=registro_id,
            is_active=True
        )
        
        # Obtener lotes producidos
        lotes_data = self.get_lotes_producidos(registro)
        
        # Calcular totales
        totales = self.calculate_totales(registro, lotes_data)
        
        # Calcular métricas de tiempo
        metricas_tiempo = self.calculate_metricas_tiempo(registro)
        
        context.update({
            'registro': registro,
            'page_title': f'Registro {self.get_proceso_name().title()} - {registro.orden_produccion.op_numero}',
            **lotes_data,
            **totales,
            **metricas_tiempo
        })
        
        return context
    
    def get_queryset(self):
        """Método a sobrescribir por cada vista específica."""
        raise NotImplementedError
    
    def get_lotes_producidos(self, registro):
        """Método a sobrescribir por cada vista específica."""
        return {}
    
    def calculate_totales(self, registro, lotes_data):
        """Método a sobrescribir por cada vista específica."""
        return {}
    
    def calculate_metricas_tiempo(self, registro):
        """Calcula métricas de tiempo comunes para todos los procesos."""
        tiempo_total_minutos = 0
        tiempo_paro_minutos = 0
        
        if registro.hora_inicio and registro.hora_final:
            from datetime import datetime
            inicio = datetime.combine(registro.fecha, registro.hora_inicio)
            final = datetime.combine(registro.fecha, registro.hora_final)
            tiempo_total_minutos = (final - inicio).total_seconds() / 60
            
            # Calcular tiempo de paros según el tipo de proceso
            paros_attr = f'paros_{self.get_proceso_name().lower()}'
            if hasattr(registro, paros_attr):
                paros = getattr(registro, paros_attr).all()
                for paro in paros:
                    if paro.hora_inicio_paro and paro.hora_final_paro:
                        inicio_paro = datetime.combine(registro.fecha, paro.hora_inicio_paro)
                        final_paro = datetime.combine(registro.fecha, paro.hora_final_paro)
                        tiempo_paro_minutos += (final_paro - inicio_paro).total_seconds() / 60
        
        tiempo_productivo_minutos = tiempo_total_minutos - tiempo_paro_minutos
        eficiencia_tiempo = (tiempo_productivo_minutos / tiempo_total_minutos * 100) if tiempo_total_minutos > 0 else 0
        
        return {
            'tiempo_total_minutos': tiempo_total_minutos,
            'tiempo_paro_minutos': tiempo_paro_minutos,
            'tiempo_productivo_minutos': tiempo_productivo_minutos,
            'eficiencia_tiempo': round(eficiencia_tiempo, 2),
        }
    
    def get_proceso_name(self):
        """Método a sobrescribir por cada vista específica."""
        return "producción"