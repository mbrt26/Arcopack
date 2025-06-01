# produccion/views/__init__.py

# Importar todas las vistas para mantener compatibilidad con URLs existentes

# Vistas base y comunes
from .base import *
from .common import *

# Vistas de Orden de Producción
from .orden_produccion import (
    OrdenProduccionViewSet,
    orden_produccion_list_view,
    orden_produccion_detail_view,
    anular_orden_view,
    OrdenProduccionCreateView,
    OrdenProduccionUpdateView,
)

# Vistas de Impresión
from .impresion import (
    RegistroImpresionViewSet,
    RegistroImpresionCreateView,
    RegistroImpresionUpdateView,
    RegistroImpresionDetailView,
)

# Vistas de Refilado
from .refilado import (
    RefiladoViewSet,
    RegistroRefiladoCreateView,
    RegistroRefiladoUpdateView,
    RegistroRefiladoDetailView,
)

# Vistas de Sellado
from .sellado import (
    SelladoViewSet,
    RegistroSelladoCreateView,
    RegistroSelladoUpdateView,
    RegistroSelladoDetailView,
)

# Vistas de Doblado
from .doblado import (
    DobladoViewSet,
    RegistroDobladoCreateView,
    RegistroDobladoUpdateView,
    RegistroDobladoDetailView,
)

# Vistas Kanban
from .kanban import (
    KanbanBaseView,
    ImpresionKanbanView,
    RefiladoKanbanView,
    SelladoKanbanView,
    DobladoKanbanView,
)

# APIs y ViewSets
from .api import (
    LoteMPDisponibleViewSet,
    LoteWIPDisponibleViewSet,
    lote_wip_json_api,
    lote_mp_json_api,
)

# Vistas de resultados y procesos
from .reportes import (
    ProcesoListView,
    ResultadosProduccionView,
    ResumenProduccionView,
)