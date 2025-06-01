# configuracion/urls.py

from django.urls import path
from . import views

app_name = 'configuracion_web'

urlpatterns = [
    # Dashboard principal de administración
    path('administracion/', views.AdministracionDashboardView.as_view(), name='administracion-dashboard'),
    
    # Unidades de medida
    path('unidades-medida/', views.UnidadMedidaListView.as_view(), name='unidad-medida-list'),
    path('unidades-medida/nueva/', views.UnidadMedidaCreateView.as_view(), name='unidad-medida-create'),
    path('unidades-medida/<int:pk>/editar/', views.UnidadMedidaUpdateView.as_view(), name='unidad-medida-update'),
    path('unidades-medida/<int:pk>/eliminar/', views.UnidadMedidaDeleteView.as_view(), name='unidad-medida-delete'),
    
    # Categorías de materia prima
    path('categorias-mp/', views.CategoriaMPListView.as_view(), name='categoria-mp-list'),
    path('categorias-mp/nueva/', views.CategoriaMPCreateView.as_view(), name='categoria-mp-create'),
    path('categorias-mp/<int:pk>/editar/', views.CategoriaMPUpdateView.as_view(), name='categoria-mp-update'),
    path('categorias-mp/<int:pk>/eliminar/', views.CategoriaMPDeleteView.as_view(), name='categoria-mp-delete'),
    
    # Ubicaciones
    path('ubicaciones/', views.UbicacionListView.as_view(), name='ubicacion-list'),
    path('ubicaciones/nueva/', views.UbicacionCreateView.as_view(), name='ubicacion-create'),
    path('ubicaciones/<int:pk>/editar/', views.UbicacionUpdateView.as_view(), name='ubicacion-update'),
    path('ubicaciones/<int:pk>/eliminar/', views.UbicacionDeleteView.as_view(), name='ubicacion-delete'),
    
    # Procesos
    path('procesos/', views.ProcesoListView.as_view(), name='proceso-list'),
    path('procesos/nuevo/', views.ProcesoCreateView.as_view(), name='proceso-create'),
    path('procesos/<int:pk>/editar/', views.ProcesoUpdateView.as_view(), name='proceso-update'),
    path('procesos/<int:pk>/eliminar/', views.ProcesoDeleteView.as_view(), name='proceso-delete'),
    
    # Máquinas
    path('maquinas/', views.MaquinaListView.as_view(), name='maquina-list'),
    path('maquinas/nueva/', views.MaquinaCreateView.as_view(), name='maquina-create'),
    path('maquinas/<int:pk>/editar/', views.MaquinaUpdateView.as_view(), name='maquina-update'),
    path('maquinas/<int:pk>/eliminar/', views.MaquinaDeleteView.as_view(), name='maquina-delete'),
    
    # Proveedores
    path('proveedores/', views.ProveedorListView.as_view(), name='proveedor-list'),
    path('proveedores/nuevo/', views.ProveedorCreateView.as_view(), name='proveedor-create'),
    path('proveedores/<int:pk>/editar/', views.ProveedorUpdateView.as_view(), name='proveedor-update'),
    path('proveedores/<int:pk>/eliminar/', views.ProveedorDeleteView.as_view(), name='proveedor-delete'),
    
    # Rodillos Anilox
    path('rodillos-anilox/', views.RodilloAniloxListView.as_view(), name='rodillo-anilox-list'),
    path('rodillos-anilox/nuevo/', views.RodilloAniloxCreateView.as_view(), name='rodillo-anilox-create'),
    path('rodillos-anilox/<int:pk>/editar/', views.RodilloAniloxUpdateView.as_view(), name='rodillo-anilox-update'),
    
    # Causas de Paro
    path('causas-paro/', views.CausaParoListView.as_view(), name='causa-paro-list'),
    path('causas-paro/nueva/', views.CausaParoCreateView.as_view(), name='causa-paro-create'),
    path('causas-paro/<int:pk>/editar/', views.CausaParoUpdateView.as_view(), name='causa-paro-update'),
    
    # Tipos de Desperdicio
    path('tipos-desperdicio/', views.TipoDesperdicioListView.as_view(), name='tipo-desperdicio-list'),
    path('tipos-desperdicio/nuevo/', views.TipoDesperdicioCreateView.as_view(), name='tipo-desperdicio-create'),
    path('tipos-desperdicio/<int:pk>/editar/', views.TipoDesperdicioUpdateView.as_view(), name='tipo-desperdicio-update'),
    
    # Láminas
    path('laminas/', views.LaminaListView.as_view(), name='lamina-list'),
    path('laminas/nueva/', views.LaminaCreateView.as_view(), name='lamina-create'),
    path('laminas/<int:pk>/editar/', views.LaminaUpdateView.as_view(), name='lamina-update'),
    
    # Tratamientos
    path('tratamientos/', views.TratamientoListView.as_view(), name='tratamiento-list'),
    path('tratamientos/nuevo/', views.TratamientoCreateView.as_view(), name='tratamiento-create'),
    path('tratamientos/<int:pk>/editar/', views.TratamientoUpdateView.as_view(), name='tratamiento-update'),
    
    # Tipos de Tinta
    path('tipos-tinta/', views.TipoTintaListView.as_view(), name='tipo-tinta-list'),
    path('tipos-tinta/nuevo/', views.TipoTintaCreateView.as_view(), name='tipo-tinta-create'),
    path('tipos-tinta/<int:pk>/editar/', views.TipoTintaUpdateView.as_view(), name='tipo-tinta-update'),
    
    # Programas de Lámina
    path('programas-lamina/', views.ProgramaLaminaListView.as_view(), name='programa-lamina-list'),
    path('programas-lamina/nuevo/', views.ProgramaLaminaCreateView.as_view(), name='programa-lamina-create'),
    path('programas-lamina/<int:pk>/editar/', views.ProgramaLaminaUpdateView.as_view(), name='programa-lamina-update'),
    
    # Tipos de Sellado
    path('tipos-sellado/', views.TipoSelladoListView.as_view(), name='tipo-sellado-list'),
    path('tipos-sellado/nuevo/', views.TipoSelladoCreateView.as_view(), name='tipo-sellado-create'),
    path('tipos-sellado/<int:pk>/editar/', views.TipoSelladoUpdateView.as_view(), name='tipo-sellado-update'),
    
    # Tipos de Troquel
    path('tipos-troquel/', views.TipoTroquelListView.as_view(), name='tipo-troquel-list'),
    path('tipos-troquel/nuevo/', views.TipoTroquelCreateView.as_view(), name='tipo-troquel-create'),
    path('tipos-troquel/<int:pk>/editar/', views.TipoTroquelUpdateView.as_view(), name='tipo-troquel-update'),
    
    # Tipos de Zipper
    path('tipos-zipper/', views.TipoZipperListView.as_view(), name='tipo-zipper-list'),
    path('tipos-zipper/nuevo/', views.TipoZipperCreateView.as_view(), name='tipo-zipper-create'),
    path('tipos-zipper/<int:pk>/editar/', views.TipoZipperUpdateView.as_view(), name='tipo-zipper-update'),
    
    # Tipos de Válvula
    path('tipos-valvula/', views.TipoValvulaListView.as_view(), name='tipo-valvula-list'),
    path('tipos-valvula/nuevo/', views.TipoValvulaCreateView.as_view(), name='tipo-valvula-create'),
    path('tipos-valvula/<int:pk>/editar/', views.TipoValvulaUpdateView.as_view(), name='tipo-valvula-update'),
    
    # Tipos de Impresión
    path('tipos-impresion/', views.TipoImpresionListView.as_view(), name='tipo-impresion-list'),
    path('tipos-impresion/nuevo/', views.TipoImpresionCreateView.as_view(), name='tipo-impresion-create'),
    path('tipos-impresion/<int:pk>/editar/', views.TipoImpresionUpdateView.as_view(), name='tipo-impresion-update'),
    
    # Servicios
    path('servicios/', views.ServicioListView.as_view(), name='servicio-list'),
    path('servicios/nuevo/', views.ServicioCreateView.as_view(), name='servicio-create'),
    path('servicios/<int:pk>/editar/', views.ServicioUpdateView.as_view(), name='servicio-update'),
    
    # SubLíneas
    path('sublineas/', views.SubLineaListView.as_view(), name='sublinea-list'),
    path('sublineas/nueva/', views.SubLineaCreateView.as_view(), name='sublinea-create'),
    path('sublineas/<int:pk>/editar/', views.SubLineaUpdateView.as_view(), name='sublinea-update'),
    
    # Estados de Producto
    path('estados-producto/', views.EstadoProductoListView.as_view(), name='estado-producto-list'),
    path('estados-producto/nuevo/', views.EstadoProductoCreateView.as_view(), name='estado-producto-create'),
    path('estados-producto/<int:pk>/editar/', views.EstadoProductoUpdateView.as_view(), name='estado-producto-update'),
    
    # Categorías de Producto
    path('categorias-producto/', views.CategoriaProductoListView.as_view(), name='categoria-producto-list'),
    path('categorias-producto/nueva/', views.CategoriaProductoCreateView.as_view(), name='categoria-producto-create'),
    path('categorias-producto/<int:pk>/editar/', views.CategoriaProductoUpdateView.as_view(), name='categoria-producto-update'),
    
    # Tipos de Materia Prima
    path('tipos-materia-prima/', views.TipoMateriaPrimaListView.as_view(), name='tipo-materia-prima-list'),
    path('tipos-materia-prima/nuevo/', views.TipoMateriaPrimaCreateView.as_view(), name='tipo-materia-prima-create'),
    path('tipos-materia-prima/<int:pk>/editar/', views.TipoMateriaPrimaUpdateView.as_view(), name='tipo-materia-prima-update'),
    
    # Tipos de Material
    path('tipos-material/', views.TipoMaterialListView.as_view(), name='tipo-material-list'),
    path('tipos-material/nuevo/', views.TipoMaterialCreateView.as_view(), name='tipo-material-create'),
    path('tipos-material/<int:pk>/editar/', views.TipoMaterialUpdateView.as_view(), name='tipo-material-update'),
    
    # Cuentas Contables
    path('cuentas-contables/', views.CuentaContableListView.as_view(), name='cuenta-contable-list'),
    path('cuentas-contables/nueva/', views.CuentaContableCreateView.as_view(), name='cuenta-contable-create'),
    path('cuentas-contables/<int:pk>/editar/', views.CuentaContableUpdateView.as_view(), name='cuenta-contable-update'),
]