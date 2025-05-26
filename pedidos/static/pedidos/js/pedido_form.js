// pedidos/static/pedidos/js/pedido_form.js

class PedidoFormManager {
    constructor() {
        this.formIndex = parseInt(document.getElementById('id_form-TOTAL_FORMS').value) || 0;
        this.productos = [];
        this.init();
    }

    async init() {
        await this.cargarProductos();
        this.setupEventListeners();
        this.actualizarNumeracion();
        this.calcularTotales();
    }

    async cargarProductos() {
        try {
            const response = await fetch('/api/productos/activos/');
            if (response.ok) {
                this.productos = await response.json();
            } else {
                console.error('Error al cargar productos');
                // Fallback: usar datos del template si están disponibles
                if (window.productosData) {
                    this.productos = window.productosData;
                }
            }
        } catch (error) {
            console.error('Error al cargar productos:', error);
            if (window.productosData) {
                this.productos = window.productosData;
            }
        }
    }

    setupEventListeners() {
        // Botón agregar línea
        const btnAgregar = document.getElementById('agregar-linea');
        if (btnAgregar) {
            btnAgregar.addEventListener('click', () => this.agregarLinea());
        }

        // Event listeners para líneas existentes
        this.setupLineasExistentes();

        // Validación del formulario
        const form = document.getElementById('pedido-form');
        if (form) {
            form.addEventListener('submit', (e) => this.validarFormulario(e));
        }

        // Auto-guardar (opcional)
        this.setupAutoGuardado();
    }

    setupLineasExistentes() {
        document.querySelectorAll('.linea-pedido').forEach(linea => {
            this.setupLineaEventListeners(linea);
        });
    }

    setupLineaEventListeners(linea) {
        const indice = linea.dataset.formIndex;

        // Selector de producto
        const productoSelect = linea.querySelector(`select[name="form-${indice}-producto"]`);
        if (productoSelect) {
            productoSelect.addEventListener('change', () => {
                this.onProductoChange(linea, productoSelect);
            });
        }

        // Inputs de cantidad y precio
        const cantidadInput = linea.querySelector(`input[name="form-${indice}-cantidad"]`);
        const precioInput = linea.querySelector(`input[name="form-${indice}-precio_unitario"]`);

        if (cantidadInput) {
            cantidadInput.addEventListener('input', () => {
                this.calcularSubtotal(linea);
                this.calcularTotales();
            });
        }

        if (precioInput) {
            precioInput.addEventListener('input', () => {
                this.calcularSubtotal(linea);
                this.calcularTotales();
            });
        }

        // Botón eliminar
        const btnEliminar = linea.querySelector('.btn-remove-linea');
        if (btnEliminar) {
            btnEliminar.addEventListener('click', () => this.eliminarLinea(linea));
        }
    }

    async onProductoChange(linea, select) {
        const productoId = select.value;
        if (!productoId) {
            this.limpiarInfoProducto(linea);
            return;
        }

        try {
            // Buscar producto en cache local primero
            let producto = this.productos.find(p => p.id == productoId);
            
            if (!producto) {
                // Si no está en cache, obtener de la API
                const response = await fetch(`/pedidos/api/producto-info/?producto_id=${productoId}`);
                if (response.ok) {
                    producto = await response.json();
                } else {
                    throw new Error('Producto no encontrado');
                }
            }

            this.actualizarInfoProducto(linea, producto);
        } catch (error) {
            console.error('Error al obtener información del producto:', error);
            this.mostrarError('Error al cargar información del producto');
        }
    }

    actualizarInfoProducto(linea, producto) {
        const indice = linea.dataset.formIndex;
        
        // Actualizar precio unitario
        const precioInput = linea.querySelector(`input[name="form-${indice}-precio_unitario"]`);
        if (precioInput) {
            precioInput.value = parseFloat(producto.precio_venta).toFixed(2);
        }

        // Mostrar información del producto
        const infoDiv = linea.querySelector('.producto-info');
        if (infoDiv) {
            const unidadSpan = infoDiv.querySelector('.unidad-medida');
            const precioSpan = infoDiv.querySelector('.precio-base');
            
            if (unidadSpan) unidadSpan.textContent = producto.unidad_medida || 'UN';
            if (precioSpan) precioSpan.textContent = parseFloat(producto.precio_venta).toFixed(2);
            
            infoDiv.style.display = 'block';
        }

        // Recalcular subtotal
        this.calcularSubtotal(linea);
        this.calcularTotales();
    }

    limpiarInfoProducto(linea) {
        const indice = linea.dataset.formIndex;
        
        // Limpiar precio
        const precioInput = linea.querySelector(`input[name="form-${indice}-precio_unitario"]`);
        if (precioInput) {
            precioInput.value = '';
        }

        // Ocultar información
        const infoDiv = linea.querySelector('.producto-info');
        if (infoDiv) {
            infoDiv.style.display = 'none';
        }

        this.calcularSubtotal(linea);
        this.calcularTotales();
    }

    calcularSubtotal(linea) {
        const indice = linea.dataset.formIndex;
        const cantidadInput = linea.querySelector(`input[name="form-${indice}-cantidad"]`);
        const precioInput = linea.querySelector(`input[name="form-${indice}-precio_unitario"]`);
        const subtotalDisplay = linea.querySelector('.subtotal-display');

        if (cantidadInput && precioInput && subtotalDisplay) {
            const cantidad = parseFloat(cantidadInput.value) || 0;
            const precio = parseFloat(precioInput.value) || 0;
            const subtotal = cantidad * precio;

            subtotalDisplay.value = this.formatearMoneda(subtotal);
        }
    }

    calcularTotales() {
        let totalGeneral = 0;
        let totalLineas = 0;
        let totalItems = 0;

        document.querySelectorAll('.linea-pedido:not([style*="display: none"])').forEach(linea => {
            const indice = linea.dataset.formIndex;
            const cantidadInput = linea.querySelector(`input[name="form-${indice}-cantidad"]`);
            const precioInput = linea.querySelector(`input[name="form-${indice}-precio_unitario"]`);

            if (cantidadInput && precioInput) {
                const cantidad = parseFloat(cantidadInput.value) || 0;
                const precio = parseFloat(precioInput.value) || 0;
                const subtotal = cantidad * precio;

                totalGeneral += subtotal;
                totalItems += cantidad;
                totalLineas++;
            }
        });

        // Actualizar displays
        const totalPedidoEl = document.getElementById('total-pedido');
        const contadorLineasEl = document.getElementById('contador-lineas');
        const totalItemsEl = document.getElementById('total-items');

        if (totalPedidoEl) totalPedidoEl.textContent = this.formatearMoneda(totalGeneral);
        if (contadorLineasEl) contadorLineasEl.textContent = totalLineas;
        if (totalItemsEl) totalItemsEl.textContent = totalItems.toFixed(2);
    }

    agregarLinea() {
        const container = document.getElementById('lineas-container');
        if (!container) return;

        // Crear nueva línea basada en el template
        const nuevaLinea = this.crearNuevaLinea();
        container.appendChild(nuevaLinea);

        // Incrementar contador
        this.formIndex++;
        document.getElementById('id_form-TOTAL_FORMS').value = this.formIndex;

        // Setup event listeners para la nueva línea
        this.setupLineaEventListeners(nuevaLinea);

        // Actualizar numeración
        this.actualizarNumeracion();

        // Hacer scroll a la nueva línea
        nuevaLinea.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    crearNuevaLinea() {
        const div = document.createElement('div');
        div.className = 'linea-pedido';
        div.dataset.formIndex = this.formIndex;

        div.innerHTML = `
            <div class="row align-items-center">
                <div class="col-md-1">
                    <strong class="numero-linea">#${this.formIndex + 1}</strong>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Producto *</label>
                    <select name="form-${this.formIndex}-producto" class="form-select" required>
                        <option value="">Seleccione un producto...</option>
                        ${this.productos.map(p => 
                            `<option value="${p.id}">${p.codigo} - ${p.nombre}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Cantidad *</label>
                    <input type="number" name="form-${this.formIndex}-cantidad" class="form-control" 
                           step="0.01" min="0" required>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Precio Unit.</label>
                    <input type="number" name="form-${this.formIndex}-precio_unitario" class="form-control" 
                           step="0.01" min="0">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Subtotal</label>
                    <input type="text" class="form-control subtotal-display" readonly value="$0.00">
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn-remove-linea" title="Eliminar línea">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-12">
                    <label class="form-label">Especificaciones Técnicas</label>
                    <textarea name="form-${this.formIndex}-especificaciones_tecnicas" 
                              class="form-control" rows="2"></textarea>
                </div>
            </div>
            <div class="producto-info" style="display: none;">
                <div class="row">
                    <div class="col-md-6">
                        <small><strong>Unidad:</strong> <span class="unidad-medida">-</span></small>
                    </div>
                    <div class="col-md-6">
                        <small><strong>Precio Base:</strong> $<span class="precio-base">-</span></small>
                    </div>
                </div>
            </div>
        `;

        return div;
    }

    eliminarLinea(linea) {
        const deleteInput = linea.querySelector('input[name$="-DELETE"]');
        
        if (deleteInput) {
            // Línea existente: marcar para eliminación
            deleteInput.checked = true;
            linea.style.display = 'none';
        } else {
            // Línea nueva: eliminar del DOM
            linea.remove();
        }

        this.actualizarNumeracion();
        this.calcularTotales();
    }

    actualizarNumeracion() {
        const lineasVisibles = document.querySelectorAll('.linea-pedido:not([style*="display: none"])');
        lineasVisibles.forEach((linea, index) => {
            const numeroLinea = linea.querySelector('.numero-linea');
            if (numeroLinea) {
                numeroLinea.textContent = `#${index + 1}`;
            }
        });
    }

    validarFormulario(event) {
        const lineasVisibles = document.querySelectorAll('.linea-pedido:not([style*="display: none"])');
        
        if (lineasVisibles.length === 0) {
            event.preventDefault();
            this.mostrarError('Debe agregar al menos una línea al pedido.');
            return false;
        }

        // Validar cada línea
        let errores = [];
        lineasVisibles.forEach((linea, index) => {
            const indice = linea.dataset.formIndex;
            const producto = linea.querySelector(`select[name="form-${indice}-producto"]`);
            const cantidad = linea.querySelector(`input[name="form-${indice}-cantidad"]`);

            if (!producto?.value) {
                errores.push(`Línea ${index + 1}: Debe seleccionar un producto`);
            }

            if (!cantidad?.value || parseFloat(cantidad.value) <= 0) {
                errores.push(`Línea ${index + 1}: Debe especificar una cantidad válida`);
            }
        });

        if (errores.length > 0) {
            event.preventDefault();
            this.mostrarError('Errores en el formulario:\n' + errores.join('\n'));
            return false;
        }

        return true;
    }

    setupAutoGuardado() {
        // Implementar auto-guardado cada 30 segundos para borradores
        setInterval(() => {
            if (this.debeAutoGuardar()) {
                this.autoGuardar();
            }
        }, 30000);
    }

    debeAutoGuardar() {
        // Solo auto-guardar si hay cambios y es un borrador
        const estadoSelect = document.querySelector('select[name="estado"]');
        return estadoSelect && estadoSelect.value === 'BORRADOR';
    }

    async autoGuardar() {
        try {
            const formData = new FormData(document.getElementById('pedido-form'));
            const response = await fetch(window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                this.mostrarMensaje('Borrador guardado automáticamente', 'success');
            }
        } catch (error) {
            console.log('Error en auto-guardado:', error);
        }
    }

    formatearMoneda(valor) {
        return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: 'COP',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(valor);
    }

    mostrarError(mensaje) {
        alert(mensaje); // Básico, se puede mejorar con modals
    }

    mostrarMensaje(mensaje, tipo = 'info') {
        // Implementar sistema de notificaciones toast
        console.log(`${tipo}: ${mensaje}`);
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    new PedidoFormManager();
});