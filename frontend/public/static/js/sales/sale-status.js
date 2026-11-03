/** Presentación del estado de una venta, compartida por la lista y el detalle. */

const STATUS_BADGES = {
    pagada: { css: "badge-success", label: "Pagada" },
    pendiente: { css: "badge-warning", label: "Pendiente" },
    cancelada: { css: "badge-muted", label: "Cancelada" },
};

/**
 * @param {string} status
 * @returns {string} HTML de la etiqueta.
 */
export function statusBadge(status) {
    const badge = STATUS_BADGES[status] ?? { css: "badge-muted", label: "—" };
    return `<span class="badge ${badge.css}">${badge.label}</span>`;
}
