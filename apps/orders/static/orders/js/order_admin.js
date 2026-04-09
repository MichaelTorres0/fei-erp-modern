(function($) {
    'use strict';

    // Get the customer ID from the autocomplete widget or regular select
    function getCustomerId() {
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

            // Auto-fill ship-to from customer address
            var shipFields = {
                'id_ship_to_line_1': data.address_line_1,
                'id_ship_to_line_2': data.address_line_2,
                'id_ship_to_city': data.city,
                'id_ship_to_state': data.state,
                'id_ship_to_zip': data.zip_code,
                'id_ship_to_country': data.country,
            };

            for (var sfId in shipFields) {
                var $sf = $('#' + sfId);
                if ($sf.length && !$sf.val() && shipFields[sfId]) {
                    $sf.val(shipFields[sfId]);
                }
            }

            // Update credit info panel if it exists
            var $creditInfo = $('.field-credit_info_display .readonly');
            if ($creditInfo.length) {
                var available = parseFloat(data.available_credit || 0);
                var color = available > 0 ? '#28a745' : '#dc3545';
                $creditInfo.html(
                    '<div style="line-height:1.6">' +
                    'Credit Code: <b>' + (data.credit_code || '—') + '</b> &nbsp;|&nbsp; ' +
                    'Limit: <b>$' + parseFloat(data.credit_limit).toLocaleString('en-US', {minimumFractionDigits: 2}) + '</b> &nbsp;|&nbsp; ' +
                    'AR Balance: <b>$' + parseFloat(data.ar_balance).toLocaleString('en-US', {minimumFractionDigits: 2}) + '</b> &nbsp;|&nbsp; ' +
                    'Open Orders: <b>$' + parseFloat(data.open_order_amount).toLocaleString('en-US', {minimumFractionDigits: 2}) + '</b><br>' +
                    'Over 90: <b>$' + parseFloat(data.over_90_balance).toLocaleString('en-US', {minimumFractionDigits: 2}) + '</b> &nbsp;|&nbsp; ' +
                    'Available: <span style="color:' + color + '; font-weight:bold">$' + available.toLocaleString('en-US', {minimumFractionDigits: 2}) + '</span>' +
                    '</div>'
                );
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

    // Auto-assign next line number if empty
    function autoAssignLineNumber(linePrefix) {
        var $lineNum = $('#' + linePrefix + '-line_number');
        if ($lineNum.length && (!$lineNum.val() || $lineNum.val() === '0' || $lineNum.val() === '')) {
            // Find highest existing line number
            var maxLine = 0;
            $('[id$="-line_number"]').each(function() {
                var val = parseInt($(this).val()) || 0;
                if (val > maxLine) maxLine = val;
            });
            $lineNum.val(maxLine + 1);
        }
    }

    // Recalculate extension = net_price * qty_ordered
    function recalcExtension(linePrefix) {
        var netPrice = parseFloat($('#' + linePrefix + '-net_price').val()) || 0;
        var qtyOrdered = parseInt($('#' + linePrefix + '-qty_ordered').val()) || 0;
        var extension = (netPrice * qtyOrdered).toFixed(2);
        $('#' + linePrefix + '-extension').val(extension);

        // Update display if extension is readonly
        var $extDisplay = $('#' + linePrefix + '-extension');
        if ($extDisplay.is('[readonly]') || $extDisplay.closest('.readonly').length) {
            $extDisplay.text('$' + extension);
        }
    }

    $(document).ready(function() {
        // Watch for customer change — works with both Select2 autocomplete and regular selects
        // Select2 triggers standard jQuery 'change' events
        $('#id_customer').on('change', function() {
            var customerId = $(this).val();
            fillCustomerDefaults(customerId);
        });

        // Watch for product changes on inline rows
        // Use event delegation since inlines can be added dynamically
        // This covers both regular selects and Select2 autocomplete widgets
        $(document).on('change', '[id$="-product"]', function() {
            var productId = $(this).val();
            if (!productId) return;

            // Extract the line prefix (e.g., "id_lines-0" from "id_lines-0-product")
            var fieldId = $(this).attr('id');
            var linePrefix = fieldId.replace('-product', '');

            fillLinePricing(linePrefix, productId);
            autoAssignLineNumber(linePrefix);
        });

        // Watch for qty changes to recalculate extension and set qty_open
        $(document).on('change', '[id$="-qty_ordered"]', function() {
            var fieldId = $(this).attr('id');
            var linePrefix = fieldId.replace('-qty_ordered', '');
            recalcExtension(linePrefix);

            // Also set qty_open = qty_ordered when qty_ordered changes (for new lines)
            var qtyOrdered = $(this).val();
            var $qtyOpen = $('#' + linePrefix + '-qty_open');
            if ($qtyOpen.length && (!$qtyOpen.val() || $qtyOpen.val() === '0')) {
                $qtyOpen.val(qtyOrdered);
            }
        });

        // Also recalc on net_price manual change
        $(document).on('change', '[id$="-net_price"]', function() {
            var fieldId = $(this).attr('id');
            var linePrefix = fieldId.replace('-net_price', '');
            recalcExtension(linePrefix);
        });

        // Auto-fill line numbers for new inline rows when added
        $(document).on('click', '.add-row a', function() {
            setTimeout(function() {
                // Find the newest empty line number field and auto-assign
                $('[id$="-line_number"]').each(function() {
                    if (!$(this).val() || $(this).val() === '' || $(this).val() === '0') {
                        var fieldId = $(this).attr('id');
                        var linePrefix = fieldId.replace('-line_number', '');
                        autoAssignLineNumber(linePrefix);
                    }
                });
            }, 100);
        });
    });
})(django.jQuery);
