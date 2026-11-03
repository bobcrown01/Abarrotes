/** Página de Ventas: historial paginado, detalle y cancelación. */

import { getProducts, getSales, getSalesSummary, getUsers } from "../lib/api.js";
import { dayStartIso, escapeHtml, formatDateTime, formatMoney, todayInputValue } from "../lib/format.js";
import { setupPager } from "../lib/pager.js";
import { renderSidebar } from "../lib/sidebar.js";
import { reportError, showToast } from "../lib/toast.js";
import { setupSaleDialog } from "./sale-dialog.js";
import { statusBadge } from "./sale-status.js";

renderSidebar("ventas.html");

/** @typedef {import("../lib/api.js").SaleSummary} SaleSummary */

const PAGE_SIZE = 50;

/** @type {{ productNames: Map<number, string>, userNames: Map<number, string> }} */
const state = { productNames: new Map(), userNames: new Map() };

const table = /** @type {HTMLElement} */ (document.getElementById("salesTable"));
const rows = /** @type {HTMLElement} */ (document.getElementById("salesRows"));
const emptyState = /** @type {HTMLElement} */ (document.getElementById("salesEmpty"));
const pagerElement = /** @type {HTMLElement} */ (document.getElementById("salesPager"));
const summary = /** @type {HTMLElement} */ (document.getElementById("salesSummary"));
const filters = {
    form: /** @type {HTMLFormElement} */ (document.getElementById("salesFilters")),
    from: /** @type {HTMLInputElement} */ (document.getElementById("filterFrom")),
    to: /** @type {HTMLInputElement} */ (document.getElementById("filterTo")),
    status: /** @type {HTMLSelectElement} */ (document.getElementById("filterStatus")),
    folio: /** @type {HTMLInputElement} */ (document.getElementById("filterFolio")),
};

/**
 * @param {SaleSummary} sale
 * @returns {string}
 */
function saleRow(sale) {
    const folio = escapeHtml(sale.folio ?? `#${sale.id}`);
    return `
        <tr>
            <td><strong>${folio}</strong></td>
            <td class="muted">${formatDateTime(sale.created_at)}</td>
            <td>${escapeHtml(state.userNames.get(sale.user_id) ?? "—")}</td>
            <td>${statusBadge(sale.status)}</td>
            <td class="num"><strong>${formatMoney(sale.total)}</strong></td>
            <td class="actions">
                <button type="button" class="btn btn-ghost btn-small" data-sale="${sale.id}" aria-label="Ver venta ${folio}">Ver</button>
            </td>
        </tr>`;
}

/**
 * Lee los filtros de la pantalla y los pasa al formato de la API.
 * @returns {import("../lib/api.js").SaleFilters}
 */
function currentFilters() {
    return {
        status: filters.status.value || undefined,
        folio: filters.folio.value.trim() || undefined,
        start: dayStartIso(filters.from.value),
        // "Hasta" incluye todo el día elegido: se pide hasta el inicio del siguiente
        end: dayStartIso(filters.to.value, 1),
    };
}

const pager = setupPager({
    container: pagerElement,
    limit: PAGE_SIZE,
    fetchPage: page => getSales({ ...currentFilters(), ...page }),
    onPage: sales => {
        rows.innerHTML = sales.map(saleRow).join("");
        emptyState.hidden = sales.length > 0;
        emptyState.querySelector("p").textContent = "No hay ventas con estos filtros.";
    },
});

/** Actualiza el total de arriba: número de ventas pagadas e importe con los filtros actuales. */
async function loadSummary() {
    const { count, total } = await getSalesSummary(currentFilters());
    summary.textContent = `${count} venta${count === 1 ? "" : "s"} pagada${count === 1 ? "" : "s"} · ${formatMoney(total)}`;
}

/**
 * Carga la lista y el total.
 * @param {number} [page] Página a cargar; por omisión la actual.
 */
async function loadSales(page) {
    table.setAttribute("aria-busy", "true");
    try {
        await Promise.all([pager.load(page), loadSummary()]);
    } catch (err) {
        summary.textContent = "No se pudieron cargar las ventas";
        reportError(err, "No se pudieron cargar las ventas");
    } finally {
        table.setAttribute("aria-busy", "false");
    }
}

/** Los nombres mejoran la lectura, pero la lista funciona sin ellos. */
async function loadNames() {
    const [products, users] = await Promise.allSettled([getProducts(), getUsers()]);
    if (products.status === "fulfilled") {
        state.productNames = new Map(products.value.map(p => [p.id, p.name]));
    }
    if (users.status === "fulfilled") {
        state.userNames = new Map(users.value.map(u => [u.id, u.username]));
    }
}

const saleDialog = setupSaleDialog({
    productNames: () => state.productNames,
    userNames: () => state.userNames,
    onCancelled: message => {
        showToast(message);
        loadSales();
    },
});

rows.addEventListener("click", event => {
    const button = /** @type {HTMLElement} */ (event.target).closest("[data-sale]");
    if (button) saleDialog.open(Number(/** @type {HTMLElement} */ (button).dataset.sale));
});

// Cualquier cambio de filtro regresa a la primera página
filters.form.addEventListener("change", () => loadSales(0));
filters.form.addEventListener("submit", event => {
    event.preventDefault();
    loadSales(0);
});

// "Ver todas" quita las fechas y los demás filtros
document.getElementById("btnFilterAll")?.addEventListener("click", () => {
    filters.form.reset();
    filters.from.value = "";
    filters.to.value = "";
    loadSales(0);
});

pagerElement.addEventListener("pagererror", event => {
    reportError(/** @type {CustomEvent} */ (event).detail, "No se pudieron cargar las ventas");
});

// Empieza mostrando las ventas de hoy, lo que más se consulta en la caja
filters.from.value = todayInputValue();
filters.to.value = todayInputValue();

loadNames().then(() => loadSales());
