/**
 * Ticket de venta impreso con el diálogo de impresión del navegador.
 *
 * No depende de una marca de impresora: sirve para cualquiera que el sistema
 * tenga instalada. El formato angosto (hasta 80 mm) está en app.css, ``@media print``.
 */

import { escapeHtml, formatDateTime, formatMoney, formatQuantity, paymentMethodLabel } from "./format.js";

/** @typedef {import("./api.js").Sale} Sale */

const STORE_NAME = "Abarrotes"; // Encabezado del ticket

/**
 * Arma el HTML del ticket.
 * @param {Sale} sale
 * @param {Map<number, string>} productNames Nombres por id de producto.
 * @param {string} cashier Nombre de quien vendió.
 * @returns {string} HTML.
 */
function ticketHtml(sale, productNames, cashier) {
    const items = sale.items.map(item => `
        <tr>
            <td colspan="2">${escapeHtml(productNames.get(item.product_id) ?? `Producto #${item.product_id}`)}</td>
        </tr>
        <tr>
            <td>${formatQuantity(item.qty)} x ${formatMoney(item.price)}</td>
            <td class="ticket-num">${formatMoney(item.subtotal)}</td>
        </tr>`).join("");

    const payments = sale.payments.map(p => `
        <tr>
            <td>${escapeHtml(paymentMethodLabel(p.method))}</td>
            <td class="ticket-num">${formatMoney(p.amount)}</td>
        </tr>
        ${p.change ? `<tr><td>Cambio</td><td class="ticket-num">${formatMoney(p.change)}</td></tr>` : ""}`).join("");

    // Un ticket reimpreso de una venta cancelada debe decirlo claramente
    const cancelled = sale.status === "cancelada" ? '<p class="ticket-center"><strong>*** CANCELADA ***</strong></p>' : "";

    return `
        <p class="ticket-center"><strong>${STORE_NAME}</strong></p>
        <p class="ticket-center">${escapeHtml(sale.folio ?? `#${sale.id}`)}</p>
        <p class="ticket-center">${formatDateTime(sale.created_at)}</p>
        <p class="ticket-center">Cajero: ${escapeHtml(cashier)}</p>
        ${cancelled}
        <table>${items}</table>
        <table class="ticket-sum"><tr><td><strong>TOTAL</strong></td><td class="ticket-num"><strong>${formatMoney(sale.total)}</strong></td></tr></table>
        <table>${payments}</table>
        <p class="ticket-center">¡Gracias por su compra!</p>`;
}

/**
 * Pinta el ticket y abre el diálogo de impresión.
 * @param {Sale} sale
 * @param {Map<number, string>} productNames Nombres por id de producto.
 * @param {string} cashier Nombre de quien vendió.
 */
export function printTicket(sale, productNames, cashier) {
    // Un solo contenedor por página, fuera de los diálogos, para que sea lo único que se imprime
    let container = document.getElementById("printTicket");
    if (!container) {
        container = document.createElement("div");
        container.id = "printTicket";
        document.body.append(container);
    }
    container.innerHTML = ticketHtml(sale, productNames, cashier);
    window.print();
}
