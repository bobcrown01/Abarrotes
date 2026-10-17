/** Utilidades de formato y seguridad para pintar datos en el DOM. */

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/**
 * Escapa texto para insertarlo como HTML sin riesgo de XSS.
 * @param {unknown} value
 * @returns {string}
 */
export function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, ch => HTML_ESCAPES[ch]);
}

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

/**
 * Formatea un importe en pesos; "—" si no hay valor.
 * @param {number|null|undefined} value
 * @returns {string}
 */
export function formatMoney(value) {
    return value === null || value === undefined ? "—" : currency.format(value);
}
