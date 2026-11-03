/**
 * Página de Reportes: cuánto se vendió, cuánto se ganó, lo más vendido y lo
 * que no se movió en un periodo. Solo para roles de administración.
 */

import { getSalesReport } from "../lib/api.js";
import { dayStartIso, escapeHtml, formatMoney, formatQuantity, todayInputValue } from "../lib/format.js";
import { renderSidebar } from "../lib/sidebar.js";
import { reportError } from "../lib/toast.js";

renderSidebar("reportes.html");

const el = {
    period: /** @type {HTMLElement} */ (document.getElementById("reportPeriod")),
    presets: /** @type {HTMLElement} */ (document.querySelector(".report-presets")),
    from: /** @type {HTMLInputElement} */ (document.getElementById("reportFrom")),
    to: /** @type {HTMLInputElement} */ (document.getElementById("reportTo")),
    stats: /** @type {HTMLElement} */ (document.getElementById("reportStats")),
    total: /** @type {HTMLElement} */ (document.getElementById("statTotal")),
    count: /** @type {HTMLElement} */ (document.getElementById("statCount")),
    average: /** @type {HTMLElement} */ (document.getElementById("statAverage")),
    profit: /** @type {HTMLElement} */ (document.getElementById("statProfit")),
    costWarning: /** @type {HTMLElement} */ (document.getElementById("costWarning")),
    topRows: /** @type {HTMLElement} */ (document.getElementById("topRows")),
    idleRows: /** @type {HTMLElement} */ (document.getElementById("idleRows")),
    idleMore: /** @type {HTMLElement} */ (document.getElementById("idleMore")),
};

/**
 * Fecha local N días antes de hoy, para los atajos de periodo.
 * @param {number} days
 * @returns {string} AAAA-MM-DD.
 */
function daysAgo(days) {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

/**
 * Marca el atajo elegido; con un rango libre no queda ninguno marcado.
 * @param {number|null} days
 */
function markPreset(days) {
    el.presets.querySelectorAll("[data-days]").forEach(chip => {
        chip.setAttribute("aria-pressed", String(Number(/** @type {HTMLElement} */ (chip).dataset.days) === days));
    });
}

/**
 * Pinta el reporte recibido.
 * @param {import("../lib/api.js").SalesReport} report
 */
function render(report) {
    el.total.textContent = formatMoney(report.sales_total);
    el.count.textContent = String(report.sales_count);
    el.average.textContent = formatMoney(report.average_ticket);
    el.profit.textContent = formatMoney(report.profit);

    // Aviso honesto: la ganancia no incluye lo vendido de productos sin costo capturado
    el.costWarning.hidden = report.revenue_without_cost === 0;
    el.costWarning.textContent = `La ganancia no incluye ${formatMoney(report.revenue_without_cost)} vendidos `
        + "de productos sin costo capturado. Captúralo en Productos para que el cálculo sea completo.";

    el.topRows.innerHTML = report.top_products.length
        ? report.top_products.map((p, i) => `
            <tr>
                <td class="muted">${i + 1}</td>
                <td>${escapeHtml(p.name)}</td>
                <td class="num">${formatQuantity(p.quantity)}</td>
                <td class="num"><strong>${formatMoney(p.total)}</strong></td>
            </tr>`).join("")
        : '<tr><td colspan="4" class="muted">Sin ventas en el periodo</td></tr>';

    el.idleRows.innerHTML = report.idle_products.length
        ? report.idle_products.map(p => `<tr><td>${escapeHtml(p.name)}</td></tr>`).join("")
        : '<tr><td class="muted">Todos los productos activos se vendieron</td></tr>';
    const hidden = report.idle_total - report.idle_products.length;
    el.idleMore.hidden = hidden <= 0;
    el.idleMore.textContent = `Y ${hidden} producto${hidden === 1 ? "" : "s"} más sin ventas.`;
}

/** Pide el reporte del periodo elegido. */
async function load() {
    el.stats.setAttribute("aria-busy", "true");
    el.period.textContent = el.from.value === el.to.value
        ? `Del ${el.from.value}`
        : `Del ${el.from.value || "inicio"} al ${el.to.value || "hoy"}`;
    try {
        render(await getSalesReport({
            start: dayStartIso(el.from.value),
            // "Hasta" incluye todo el día elegido
            end: dayStartIso(el.to.value, 1),
        }));
    } catch (err) {
        el.period.textContent = "No se pudo cargar el reporte";
        reportError(err, "Error inesperado al cargar el reporte");
    } finally {
        el.stats.setAttribute("aria-busy", "false");
    }
}

/**
 * Aplica un atajo: los últimos N días, contando hoy.
 * @param {number} days
 */
function applyPreset(days) {
    el.from.value = daysAgo(days - 1);
    el.to.value = todayInputValue();
    markPreset(days);
    load();
}

el.presets.addEventListener("click", event => {
    const chip = /** @type {HTMLElement} */ (event.target).closest("[data-days]");
    if (chip) applyPreset(Number(/** @type {HTMLElement} */ (chip).dataset.days));
});

// Un rango escrito a mano desmarca los atajos
[el.from, el.to].forEach(input => input.addEventListener("change", () => {
    markPreset(null);
    load();
}));

applyPreset(7);
