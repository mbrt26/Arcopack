(function($) {
  $(function() {
    function updateLoteWip(opId) {
      $('.lote-wip-select').each(function() {
        const $select = $(this);
        $select.prop('disabled', true).html('<option>Cargando...</option>');
        if (!opId) {
          $select.html('<option>Seleccione una OP primero</option>');
          return;
        }
        $.getJSON(`/api/v1/produccion/lote-wip-json/?op_id=${opId}`)
          .done(function(data) {
            const opts = ['<option value="">---------</option>'];
            data.forEach(item => {
              opts.push(`<option value="${item.id}">${item.text}</option>`);
            });
            $select.html(opts.join('')).prop('disabled', false);
          })
          .fail(function() {
            $select.html('<option>Error cargando lotes</option>').prop('disabled', false);
          });
      });
    }

    function updateLoteMp(opId) {
      $('.lote-mp-select').each(function() {
        const $select = $(this);
        $select.prop('disabled', true).html('<option>Cargando...</option>');
        if (!opId) {
          $select.html('<option>Seleccione una OP primero</option>');
          return;
        }
        $.getJSON(`/api/v1/produccion/lote-mp-json/?op_id=${opId}`)
          .done(function(data) {
            const opts = ['<option value="">---------</option>'];
            data.forEach(item => {
              opts.push(`<option value="${item.id}">${item.text}</option>`);
            });
            $select.html(opts.join('')).prop('disabled', false);
          })
          .fail(function() {
            $select.html('<option>Error cargando lotes</option>').prop('disabled', false);
          });
      });
    }

    $('#id_orden_produccion').on('change', function() {
      updateLoteWip(this.value);
      updateLoteMp(this.value);
    });

    updateLoteWip($('#id_orden_produccion').val());
    updateLoteMp($('#id_orden_produccion').val());
  });
})(django.jQuery);
