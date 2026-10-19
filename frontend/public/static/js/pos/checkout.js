/** Registra en el backend la venta armada en el carrito. */

import { addPayment, addSaleItem, cancelSale, closeSale, createSale } from "../lib/api.js";

/** @typedef {import("./cart.js").Cart} Cart */
/** @typedef {import("../lib/api.js").Sale} Sale */
/** @typedef {import("../lib/api.js").PaymentMethod} PaymentMethod */

/**
 * @typedef {Object} PaymentChoice
 * @property {PaymentMethod} method
 * @property {number|null} received Efectivo entregado (solo para efectivo).
 */

/**
 * Abre la venta, agrega las partidas, registra el pago y la cierra.
 *
 * Si algo falla después de abrirla, la venta se cancela para no dejar
 * tickets pendientes colgados. El backend no descuenta inventario hasta el
 * cierre, así que cancelar a medias no altera existencias.
 *
 * @param {Cart} cart
 * @param {number} userId Cajero.
 * @param {PaymentChoice} payment
 * @returns {Promise<Sale>} La venta cerrada.
 */
export async function checkout(cart, userId, payment) {
    const sale = await createSale(userId);

    try {
        let current = sale;
        // En serie: cada partida bloquea la venta en el backend
        for (const line of cart.lines) {
            current = await addSaleItem({ sale_id: sale.id, product_id: line.product.id, qty: line.qty });
        }

        await addPayment({
            sale_id: sale.id,
            method: payment.method,
            // El total oficial es el del backend (precios vigentes del catálogo)
            amount: current.total,
            received: payment.method === "efectivo" ? payment.received : null,
        });

        return await closeSale(sale.id);
    } catch (err) {
        await cancelSale(sale.id).catch(cancelErr =>
            console.error(`No se pudo cancelar la venta ${sale.folio}`, cancelErr),
        );
        throw err;
    }
}
