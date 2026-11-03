/**
 * Detalle de una venta con la opción de cancelarla.
 *
 * Cancelar pide una segunda confirmación dentro de la misma ventana porque
 * cambia el corte del día y, si la venta estaba pagada, regresa el inventario.
 */

import { ApiError, cancelSale, getSale } from "../lib/api.js";
import {
    escapeHtml,
    formatDateTime,
    formatMoney,
    formatQuantity,
    paymentMethodLabel,
} from "../lib/format.js";
import { printTicket } from "../lib/ticket.js";
import { statusBadge } from "./sale-status.js";

/** @typedef {import("../lib/api.js").Sale} Sale */

/**
 * @param {Object} options
 * @param {() => Map<number, string>} options.productNames Nombres por id de producto.
 * @param {() => Map<number, string>} options.userNames Nombres por id de usuario.
 * @param {(message: string) => void} options.onCancelled Se llama tras cancelar.
 * @returns {{ open: (saleId: number) => Promise<void> }}
 */
export function setupSaleDialog({ productNames, userNames, onCancelled }) {
    const dialog = /** @type {HTMLDialogElement} */ (document.getElementById("saleDialog"));
    const title = /** @type {HTMLElement} */ (document.getElementById("saleTitle"));
    const detail = /** @type {HTMLElement} */ (document.getElementById("saleDetail"));
    const errorBox = /** @type {HTMLElement} */ (document.getElementById("saleError"));
    const secondary = /** @type {HTMLButtonElement} */ (document.getElementById("btnSaleSecondary"));
    const cancelButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnSaleCancel"));
    const printButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnSalePrint"));

    /** @type {Sale|null} */
    let sale = null;
    let confirming = false;

    /** @param {string} message */
    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
    }

    /** @param {Sale} current @returns {string} */
    function detailHtml(current) {
        const items = current.items.map(item => `
            <tr>
                <td>${escapeHtml(productNames().get(item.product_id) ?? `Producto #${item.product_id}`)}</td>
                <td class="num">${formatQuantity(item.qty)}</td>
                <td class="num">${formatMoney(item.price)}</td>
                <td class="num">${formatMoney(item.subtotal)}</td>
            </tr>`).join("");

        const payments = current.payments.map(p => `
            <tr>
                <td>${escapeHtml(paymentMethodLabel(p.method))}</td>
                <td class="num">${formatMoney(p.amount)}</td>
                <td class="num">${formatMoney(p.change)}</td>
            </tr>`).join("");

        return `
            <dl class="detail-meta">
                <div><dt>Fecha</dt><dd>${formatDateTime(current.created_at)}</dd></div>
                <div><dt>Estado</dt><dd>${statusBadge(current.status)}</dd></div>
                <div><dt>Cajero</dt><dd>${escapeHtml(userNames().get(current.user_id) ?? "—")}</dd></div>
            </dl>
            <div class="table-wrap">
                <table class="data-table detail-table">
                    <caption class="visually-hidden">Productos de la venta</caption>
                    <thead><tr>
                        <th scope="col">Producto</th>
                        <th scope="col" class="num">Cant.</th>
                        <th scope="col" class="num">Precio</th>
                        <th scope="col" class="num">Importe</th>
                    </tr></thead>
                    <tbody>${items || '<tr><td colspan="4" class="muted">Sin productos</td></tr>'}</tbody>
                </table>
            </div>
            ${payments ? `
            <div class="table-wrap">
                <table class="data-table detail-table">
                    <caption class="visually-hidden">Pagos de la venta</caption>
                    <thead><tr>
                        <th scope="col">Pago</th>
                        <th scope="col" class="num">Importe</th>
                        <th scope="col" class="num">Cambio</th>
                    </tr></thead>
                    <tbody>${payments}</tbody>
                </table>
            </div>` : ""}
            <div class="detail-total"><span>Total</span><strong>${formatMoney(current.total)}</strong></div>`;
    }

    function showDetail() {
        confirming = false;
        if (!sale) return;
        title.textContent = `Venta ${sale.folio ?? sale.id}`;
        detail.innerHTML = detailHtml(sale);
        secondary.textContent = "Cerrar";
        cancelButton.textContent = "Cancelar venta";
        cancelButton.hidden = sale.status === "cancelada";
        // Reimpresión: solo tiene sentido en una venta con productos
        printButton.hidden = sale.items.length === 0;
    }

    function showConfirm() {
        if (!sale) return;
        confirming = true;
        title.textContent = `Cancelar venta ${sale.folio ?? sale.id}`;
        const message = document.createElement("p");
        message.className = "dialog-message";
        message.textContent = sale.status === "pagada"
            ? `Se cancelará la venta por ${formatMoney(sale.total)} y sus productos regresarán al inventario. `
                + "Si ya cobraste, devuelve el dinero al cliente. Esta acción no se puede deshacer."
            : "Se cancelará esta venta pendiente. Esta acción no se puede deshacer.";
        detail.replaceChildren(message);
        secondary.textContent = "No cancelar";
        cancelButton.textContent = "Sí, cancelar venta";
        printButton.hidden = true;
        // El foco empieza en la opción segura: evita cancelar con un Enter accidental
        secondary.focus();
    }

    async function confirmCancel() {
        if (!sale) return;
        cancelButton.disabled = true;
        errorBox.hidden = true;
        try {
            const cancelled = await cancelSale(sale.id);
            dialog.close();
            onCancelled(`Venta ${cancelled.folio ?? cancelled.id} cancelada`);
        } catch (err) {
            if (!(err instanceof ApiError)) console.error(err);
            showError(err instanceof ApiError ? err.message : "No se pudo cancelar la venta");
        } finally {
            cancelButton.disabled = false;
        }
    }

    /** @param {number} saleId */
    async function open(saleId) {
        sale = null;
        confirming = false;
        title.textContent = "Venta";
        detail.textContent = "Cargando…";
        errorBox.hidden = true;
        secondary.textContent = "Cerrar";
        cancelButton.hidden = true;
        printButton.hidden = true;
        dialog.showModal();
        secondary.focus();

        try {
            sale = await getSale(saleId);
            showDetail();
        } catch (err) {
            if (!(err instanceof ApiError)) console.error(err);
            detail.textContent = "";
            showError(err instanceof ApiError ? err.message : "No se pudo cargar la venta");
        }
    }

    // Se cierra antes de imprimir: un <dialog> modal queda encima de la impresión
    printButton.addEventListener("click", () => {
        if (!sale) return;
        dialog.close();
        printTicket(sale, productNames(), userNames().get(sale.user_id) ?? "—");
    });

    cancelButton.addEventListener("click", () => {
        errorBox.hidden = true;
        if (confirming) confirmCancel();
        else showConfirm();
    });

    secondary.addEventListener("click", () => {
        errorBox.hidden = true;
        if (confirming) showDetail();
        else dialog.close();
    });

    document.getElementById("btnCloseSale")?.addEventListener("click", () => dialog.close());

    return { open };
}
