// pedidos.js - Funcionalidades JavaScript para el módulo de pedidos

document.addEventListener('DOMContentLoaded', function() {
    
    // Inicializar funcionalidades
    initFormsetHandlers();
    initProductSelect();
    initEstadoChangeHandler();
    initCalculationHandlers();
    
    // Manejar formsets dinámicos para líneas de pedido
    function initFormsetHandlers() {
        const formsetContainer = document.getElementById('lineas-formset');
        if (!formsetContainer) return;
        
        const addButton = document.getElementById('add-linea');
        const totalFormsInput = document.getElementById('id_lineas-TOTAL_FORMS');
        
        if (addButton) {
            addButton.addEventListener('click', function(e) {
                e.preventDefault();
                addFormsetForm();
            });
        }
        
        // Agregar handlers a las líneas existentes
        updateFormsetHandlers();
        
        function addFormsetForm() {
            const totalForms = parseInt(totalFormsInput.value);
            const formTemplate = document.querySelector('.linea-form-template');
            
            if (!formTemplate) return;
            
            // Clonar el template
            const newForm = formTemplate.cloneNode(true);
            newForm.classList.remove('linea-form-template', 'd-none');
            newForm.classList.add('linea-form');
            
            // Actualizar los names e ids de los campos
            const inputs = newForm.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                const name = input.getAttribute('name');
                const id = input.getAttribute('id');
                
                if (name) {
                    input.setAttribute('name', name.replace(/__prefix__/g, totalForms));
                }
                if (id) {
                    input.setAttribute('id', id.replace(/__prefix__/g, totalForms));
                }
                
                // Limpiar valores
                if (input.type !== 'hidden') {
                    input.value = '';
                }
            });
            
            // Agregar al contenedor
            formsetContainer.appendChild(newForm);
            
            // Actualizar contador
            totalFormsInput.value = totalForms + 1;
            
            // Agregar handlers a la nueva línea
            updateFormsetHandlers();
            
            // Enfocar el primer campo
            const firstInput = newForm.querySelector('select, input:not([type="hidden"])');
            if (firstInput) {
                firstInput.focus();
            }
        }
        
        function updateFormsetHandlers() {
            // Botones de eliminar
            document.querySelectorAll('.delete-linea').forEach(button => {
                button.removeEventListener('click', deleteFormsetForm);
                button.addEventListener('click', deleteFormsetForm);
            });
            
            // Selectores de producto
            document.querySelectorAll('.producto-select').forEach(select => {
                select.removeEventListener('change', onProductoChange);
                select.addEventListener('change', onProductoChange);
            });
            
            // Campos de cantidad y precio
            document.querySelectorAll('.cantidad-input, .precio-input, .descuento-input').forEach(input => {
                input.removeEventListener('input', calculateLineTotal);
                input.addEventListener('input', calculateLineTotal);
            });
        }
        
        function deleteFormsetForm(e) {
            e.preventDefault();
            const lineaForm = e.target.closest('.linea-form');
            
            if (lineaForm) {
                // Marcar como eliminado si ya existe en BD
                const deleteInput = lineaForm.querySelector('input[name$="-DELETE"]');
                if (deleteInput) {
                    deleteInput.checked = true;
                    lineaForm.style.display = 'none';
                } else {
                    // Eliminar completamente si es nuevo
                    lineaForm.remove();
                }
                
                calculatePedidoTotal();
            }
        }
    }
    
    // Manejar selección de productos
    function initProductSelect() {
        document.querySelectorAll('.producto-select').forEach(select => {
            select.addEventListener('change', onProductoChange);
        });
    }
    
    function onProductoChange(e) {
        const productoId = e.target.value;
        const lineaForm = e.target.closest('.linea-form');
        
        if (!productoId || !lineaForm) return;
        
        // Obtener información del producto
        fetch(`/pedidos/api/producto-info/?producto_id=${productoId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error:', data.error);
                    return;
                }
                
                // Actualizar precio unitario
                const precioInput = lineaForm.querySelector('.precio-input');
                if (precioInput && data.precio_venta) {
                    precioInput.value = data.precio_venta;
                }
                
                // Actualizar unidad de medida (si hay un campo para mostrar)
                const unidadSpan = lineaForm.querySelector('.unidad-medida');
                if (unidadSpan && data.unidad_medida) {
                    unidadSpan.textContent = data.unidad_medida;
                }
                
                // Recalcular total de la línea
                calculateLineTotal.call(precioInput);
            })
            .catch(error => {
                console.error('Error fetching producto info:', error);
            });
    }
    
    // Manejar cambios de estado
    function initEstadoChangeHandler() {
        const estadoSelect = document.getElementById('id_nuevo_estado');
        const facturacionFields = document.querySelectorAll('.facturacion-field');
        
        if (estadoSelect) {
            estadoSelect.addEventListener('change', function() {
                const nuevoEstado = this.value;
                
                facturacionFields.forEach(field => {
                    if (nuevoEstado === 'FACTURADO') {
                        field.style.display = 'block';
                        field.querySelector('input').required = true;
                    } else {
                        field.style.display = 'none';
                        field.querySelector('input').required = false;
                    }
                });
            });
        }
    }
    
    // Cálculos automáticos
    function initCalculationHandlers() {
        document.querySelectorAll('.cantidad-input, .precio-input, .descuento-input').forEach(input => {
            input.addEventListener('input', calculateLineTotal);
        });
    }
    
    function calculateLineTotal() {
        const lineaForm = this.closest('.linea-form');
        if (!lineaForm) return;
        
        const cantidad = parseFloat(lineaForm.querySelector('.cantidad-input').value) || 0;
        const precio = parseFloat(lineaForm.querySelector('.precio-input').value) || 0;
        const descuento = parseFloat(lineaForm.querySelector('.descuento-input').value) || 0;
        
        const subtotalBruto = cantidad * precio;
        const valorDescuento = (subtotalBruto * descuento) / 100;
        const subtotalNeto = subtotalBruto - valorDescuento;
        
        // Actualizar displays de totales
        const subtotalDisplay = lineaForm.querySelector('.subtotal-display');
        if (subtotalDisplay) {
            subtotalDisplay.textContent = `$${subtotalNeto.toFixed(2)}`;
        }
        
        // Recalcular total del pedido
        calculatePedidoTotal();
    }
    
    function calculatePedidoTotal() {
        let total = 0;
        
        document.querySelectorAll('.linea-form:not([style*="display: none"])').forEach(form => {
            const deleteInput = form.querySelector('input[name$="-DELETE"]');
            if (deleteInput && deleteInput.checked) return;
            
            const cantidad = parseFloat(form.querySelector('.cantidad-input').value) || 0;
            const precio = parseFloat(form.querySelector('.precio-input').value) || 0;
            const descuento = parseFloat(form.querySelector('.descuento-input').value) || 0;
            
            const subtotalBruto = cantidad * precio;
            const valorDescuento = (subtotalBruto * descuento) / 100;
            const subtotalNeto = subtotalBruto - valorDescuento;
            
            total += subtotalNeto;
        });
        
        // Actualizar display del total
        const totalDisplay = document.getElementById('pedido-total');
        if (totalDisplay) {
            totalDisplay.textContent = `$${total.toFixed(2)}`;
        }
    }
    
    // Funciones de utilidad
    window.pedidosUtils = {
        
        // Confirmar eliminación
        confirmDelete: function(message) {
            return confirm(message || '¿Está seguro de que desea eliminar este elemento?');
        },
        
        // Imprimir pedido
        printPedido: function() {
            window.print();
        },
        
        // Exportar a PDF (placeholder para futura implementación)
        exportToPDF: function(pedidoId) {
            alert('Funcionalidad de exportación a PDF será implementada próximamente');
        },
        
        // Validar formulario antes de enviar
        validateForm: function(form) {
            const lineasValidas = form.querySelectorAll('.linea-form:not([style*="display: none"])');
            let hasValidLines = false;
            
            lineasValidas.forEach(linea => {
                const deleteInput = linea.querySelector('input[name$="-DELETE"]');
                if (deleteInput && deleteInput.checked) return;
                
                const producto = linea.querySelector('.producto-select').value;
                const cantidad = linea.querySelector('.cantidad-input').value;
                const precio = linea.querySelector('.precio-input').value;
                
                if (producto && cantidad && precio) {
                    hasValidLines = true;
                }
            });
            
            if (!hasValidLines) {
                alert('Debe agregar al menos una línea válida al pedido');
                return false;
            }
            
            return true;
        }
    };
    
    // Interceptar envío del formulario para validar
    const pedidoForm = document.getElementById('pedido-form');
    if (pedidoForm) {
        pedidoForm.addEventListener('submit', function(e) {
            if (!window.pedidosUtils.validateForm(this)) {
                e.preventDefault();
            }
        });
    }
    
    // Calcular total inicial
    calculatePedidoTotal();
});

// Funciones para manejo de estados
function cambiarEstadoPedido(pedidoId, nuevoEstado) {
    if (!confirm(`¿Está seguro de cambiar el estado del pedido?`)) {
        return;
    }
    
    // Aquí se podría hacer una petición AJAX
    // Por ahora redirigimos al formulario
    window.location.href = `/pedidos/pedido/${pedidoId}/cambiar-estado/`;
}

// Funciones para reportes
function exportarReporte(formato) {
    const form = document.getElementById('filtros-form');
    if (form) {
        const params = new URLSearchParams(new FormData(form));
        params.append('formato', formato);
        
        window.location.href = `/pedidos/reportes/?${params.toString()}`;
    }
}