// pedidos.js - Funcionalidades esenciales para el módulo de pedidos en HTML

document.addEventListener('DOMContentLoaded', function() {
    
    // Funciones de utilidad para pedidos
    window.pedidosUtils = {
        
        // Confirmar eliminación
        confirmDelete: function(message) {
            return confirm(message || '¿Está seguro de que desea eliminar este elemento?');
        },
        
        // Imprimir pedido
        printPedido: function() {
            window.print();
        },
        
        // Exportar (redirigir a URL de exportación)
        exportToPDF: function(pedidoId) {
            window.location.href = `/pedidos/${pedidoId}/pdf/`;
        },
        
        // Cambiar estado de pedido
        cambiarEstado: function(pedidoId, nuevoEstado) {
            if (confirm('¿Está seguro de cambiar el estado del pedido?')) {
                // Crear y enviar formulario
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/pedidos/${pedidoId}/cambiar-estado/`;
                
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = csrfToken;
                form.appendChild(csrfInput);
                
                const estadoInput = document.createElement('input');
                estadoInput.type = 'hidden';
                estadoInput.name = 'nuevo_estado';
                estadoInput.value = nuevoEstado;
                form.appendChild(estadoInput);
                
                document.body.appendChild(form);
                form.submit();
            }
        },
        
        // Filtrar tabla (búsqueda simple)
        filtrarTabla: function(input, tabla) {
            const filter = input.value.toLowerCase();
            const rows = tabla.getElementsByTagName('tr');
            
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                const text = row.textContent || row.innerText;
                
                if (text.toLowerCase().indexOf(filter) > -1) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            }
        }
    };
    
    // Auto-submit para filtros de select
    document.querySelectorAll('.auto-submit').forEach(function(select) {
        select.addEventListener('change', function() {
            this.form.submit();
        });
    });
    
    // Confirmar acciones de eliminación
    document.querySelectorAll('.confirm-delete').forEach(function(element) {
        element.addEventListener('click', function(e) {
            if (!window.pedidosUtils.confirmDelete()) {
                e.preventDefault();
            }
        });
    });
    
    // Búsqueda en tiempo real (opcional)
    const searchInput = document.getElementById('search-table');
    const targetTable = document.getElementById('pedidos-table');
    if (searchInput && targetTable) {
        searchInput.addEventListener('keyup', function() {
            window.pedidosUtils.filtrarTabla(this, targetTable);
        });
    }
});

// Funciones globales para botones
function cambiarEstadoPedido(pedidoId, nuevoEstado) {
    window.pedidosUtils.cambiarEstado(pedidoId, nuevoEstado);
}

function exportarReporte(formato) {
    const form = document.getElementById('filtros-form');
    if (form) {
        const params = new URLSearchParams(new FormData(form));
        params.append('formato', formato);
        window.location.href = `/pedidos/reportes/?${params.toString()}`;
    }
}