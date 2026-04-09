(function($) {
    'use strict';

    // Get the customer ID from the autocomplete widget or regular select
    function getCustomerId() {
        // Try autocomplete widget first (used when autocomplete_fields is set)
        var $select = $('#id_customer');
        if ($select.length && $select.val()) {
            return $select.val();
        }
        return null;
    }

    // Auto-fill customer defaults on the order header
    function fillCustomerDefaults(customerId) {
        if (!customerId) return;

        $.getJSON('/api/v1/orders/lookup/customer-defaults/?customer_id=' + customerId, function(data) {
            // Only fill if the field is currently empty
            var fields = {
                'id_terms': data.terms_code,
                'id_freight_terms': data.freight_terms,
                'id_salesman': data.salesman,
                'id_affiliation': data.affiliation,
                'id_ship_via': data.default_ship_via,
                'id_territory_1': data.territory_1,
                'id_territory_2': data.territory_2,
                'id_territory_3': data.territory_3,
                'id_email': data.email,
            };

            for (var fieldId in fields) {
                var $field = $('#' + fieldId);
                if ($field.length && !$field.val()) {
                    $field.val(fields[fieldId]);
                }
            }
        });
    }

    // Auto-fill pricing on an order line when product is selected
    function fillLinePricing(linePrefix, productId) {
        var customerId = getCustomerId();
        if (!customerId || !productId) return;

        $.getJSON('/api/v1/orders/lookup/pricing/?customer_id=' + customerId + '&product_id=' + productId, function(data) {
            $('#' + linePrefix + '-unit_price').val(data.unit_price);
            $('#' + linePrefix + '-discount_1').val(data.discount_1);
            $('#' + linePrefix + '-discount_2').val(data.discount_2);
            $('#' + linePrefix + '-net_price').val(data.net_price);
            $('#' + linePrefix + '-cost').val(data.cost);

            // Calculate extension if qty is present
            recalcExtension(linePrefix);
        });
    }

    // Recalculate extension = net_price * qty_ordered
    function recalcExtension(linePrefix) {
        var netPrice = parseFloat($('#' + linePrefix + '-net_price').val()) || 0;
        var qtyOrdered = parseInt($('#' + linePrefix + '-qty_ordered').val()) || 0;
        var extension = (netPrice * qtyOrdered).toFixed(2);
        $('#' + linePrefix + '-extension').val(extension);
    }

    $(document).ready(function() {
        // Watch for customer change (select2/autocomplete triggers 'change')
        $('#id_customer').on('change', function() {
            var customerId = $(this).val();
            fillCustomerDefaults(customerId);
        });

        // Watch for product changes on inline rows
        // Use event delegation since inlines can be added dynamically
        $(document).on('change', '[id$="-product"]', function() {
            var productId = $(this).val();
            if (!productId) return;

            // Extract the line prefix (e.g., "id_lines-0" from "id_lines-0-product")
            var fieldId = $(this).attr('id');
            var linePrefix = fieldId.replace('-product', '');

            fillLinePricing(linePrefix, productId);
        });

        // Watch for qty changes to recalculate extension
        $(document).on('change', '[id$="-qty_ordered"]', function() {
            var fieldId = $(this).attr('id');
            var linePrefix = fieldId.replace('-qty_ordered', '');
            recalcExtension(linePrefix);
        });

        // Also set qty_open = qty_ordered when qty_ordered changes (for new lines)
        $(document).on('change', '[id$="-qty_ordered"]', function() {
            var fieldId = $(this).attr('id');
            var linePrefix = fieldId.replace('-qty_ordered', '');
            var qtyOrdered = $(this).val();
            var $qtyOpen = $('#' + linePrefix + '-qty_open');
            // Only auto-set if qty_open is empty or 0
            if ($qtyOpen.length && (!$qtyOpen.val() || $qtyOpen.val() === '0')) {
                $qtyOpen.val(qtyOrdered);
            }
        });
    });
})(django.jQuery);
