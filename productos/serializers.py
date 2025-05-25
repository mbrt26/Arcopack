# productos/serializers.py

from rest_framework import serializers
from .models import ProductoTerminado
# Importar modelos relacionados si se usan para validación o representación anidada aquí
# from configuracion.models import CategoriaProducto, EstadoProducto # etc.
# from produccion.models import OrdenProduccion # Para validación de código

class ProductoTerminadoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo ProductoTerminado.
    Convierte instancias de ProductoTerminado a/desde formatos como JSON.
    """

    # Opcional: Mostrar nombres de relaciones en lugar de solo IDs (ejemplos)
    # Hacer esto solo si es necesario para la API de lectura, puede añadir complejidad.
    # categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    # estado_nombre = serializers.CharField(source='estado.nombre', read_only=True)
    # unidad_medida_codigo = serializers.CharField(source='unidad_medida.codigo', read_only=True)

    class Meta:
        model = ProductoTerminado # El modelo que este serializer representa
        # fields = '__all__' # Incluir todos los campos del modelo automáticamente
        # O especificar campos explícitamente (mejor para control):
        fields = [
            # Campos Principales
            'id', # DRF añade 'url' si usamos HyperlinkedModelSerializer o Routers
            'codigo', 'nombre', 'tipo_materia_prima', 'estado', 'unidad_medida',
            'cuenta_contable', 'comercializable', 'categoria', 'subcategoria', 'servicio',
            # Especificaciones Generales
            'medida_en', 'tipo_material', 'calibre_um', 'largo', 'ancho',
            'factor_decimal', 'ancho_rollo', 'metros_lineales', 'lamina',
            'extrusion_doble', 'cantidad_xml', 'largo_material', 'tratamiento',
            'tipo_tinta', 'pistas', 'programa_lamina', 'color',
            # Sellado
            'sellado_peso_millar', 'sellado_tipo', 'sellado_fuelle_lateral',
            'sellado_fuelle_superior', 'sellado_fuelle_fondo', 'sellado_solapa_cm',
            'sellado_troquel_tipo', 'sellado_troquel_medida', 'sellado_zipper_tipo',
            'sellado_zipper_medida', 'sellado_valvula_tipo', 'sellado_valvula_medida',
            'sellado_ultrasonido', 'sellado_ultrasonido_pos', 'sellado_precorte',
            'sellado_precorte_medida',
            # Impresión
            'imp_tipo_impresion', 'imp_rodillo', 'imp_repeticiones',
            # Auditoría (usualmente solo lectura en API)
            'is_active', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',
            # Opcional: Campos calculados de solo lectura (si se añaden arriba)
            # 'categoria_nombre', 'estado_nombre', 'unidad_medida_codigo',
        ]
        read_only_fields = ( # Campos que no se pueden establecer al crear/actualizar vía API
            'id', 'creado_en', 'actualizado_en', 'creado_por', 'actualizado_por',
            # 'categoria_nombre', 'estado_nombre', 'unidad_medida_codigo', # Si se añaden arriba
        )

    # --- Validación Personalizada (Opcional aquí, a menudo mejor en Vistas/Servicios) ---
    # def validate_codigo(self, value):
    #     """Validación específica para el campo código."""
    #     # Ejemplo: asegurar formato específico
    #     # if not value.startswith('PROD'):
    #     #     raise serializers.ValidationError("El código debe empezar con 'PROD'.")
    #     # Prevenir cambio si hay OPs (MEJOR HACER ESTO EN LA VISTA antes de llamar a save)
    #     # instance = self.instance # El producto existente (en caso de update)
    #     # if instance and instance.codigo != value:
    #     #     if OrdenProduccion.objects.filter(producto=instance).exists():
    #     #          raise serializers.ValidationError("No se puede cambiar código si producto tiene OPs.")
    #     return value

    # def validate(self, data):
    #     """Validación a nivel de objeto completo."""
    #     # Ejemplo: validación condicional de sellado
    #     ultrasonido = data.get('sellado_ultrasonido', getattr(self.instance, 'sellado_ultrasonido', False))
    #     ultrasonido_pos = data.get('sellado_ultrasonido_pos', getattr(self.instance, 'sellado_ultrasonido_pos', None))
    #     if ultrasonido and ultrasonido_pos is None:
    #         raise serializers.ValidationError({'sellado_ultrasonido_pos': 'Posición requerida si usa ultrasonido.'})
    #     # ... (otras validaciones condicionales) ...
    #     return data