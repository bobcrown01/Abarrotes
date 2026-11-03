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

/**
 * Fecha de hoy en la zona de la tienda, como la usa un ``<input type="date">``.
 * @returns {string} AAAA-MM-DD.
 */
export function todayInputValue() {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${now.getFullYear()}-${month}-${day}`;
}

/**
 * Convierte un día local en el instante en que empieza, para filtrar en la API.
 * @param {string} day Fecha AAAA-MM-DD.
 * @param {number} [plusDays=0] Días a sumar; con 1 da el final (excluido) de ese día.
 * @returns {string|undefined} Instante ISO 8601 en UTC; undefined si no hay fecha.
 */
export function dayStartIso(day, plusDays = 0) {
    if (!day) return undefined;
    const [year, month, date] = day.split("-").map(Number);
    return new Date(year, month - 1, date + plusDays).toISOString();
}

const METHOD_LABELS = {
    efectivo: "Efectivo",
    debito: "Débito",
    credito: "Crédito",
    transferencia: "Transferencia",
    monedero: "Monedero",
    venta_credito: "Fiado",
    link_pago: "Link de pago",
    // Abonos a cuentas de fiado, como aparecen en el corte de caja
    abono_efectivo: "Abono en efectivo",
    abono_debito: "Abono con débito",
    abono_credito: "Abono con crédito",
    abono_transferencia: "Abono por transferencia",
};

/**
 * Nombre legible de un método de pago.
 * @param {string} method
 * @returns {string}
 */
export function paymentMethodLabel(method) {
    return METHOD_LABELS[method] ?? method;
}

const quantity = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 3 });

/**
 * Formatea una cantidad (piezas o kg) con hasta tres decimales.
 * @param {number} value
 * @returns {string}
 */
export function formatQuantity(value) {
    return quantity.format(value);
}

const dateTime = new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" });

/**
 * Formatea una fecha de la API en la hora local del navegador.
 * La base guarda TIMESTAMP sin zona con el reloj UTC del contenedor de
 * PostgreSQL, por lo que una fecha sin zona se interpreta como UTC.
 * @param {string} value Fecha ISO 8601.
 * @returns {string}
 */
export function formatDateTime(value) {
    const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
    const date = new Date(hasZone ? value : `${value}Z`);
    return Number.isNaN(date.getTime()) ? "—" : dateTime.format(date);
}
