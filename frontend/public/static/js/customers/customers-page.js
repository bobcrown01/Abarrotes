/** Página de Clientes: lista, cuentas de fiado y abonos. */

import { getCustomers } from "../lib/api.js";
import { escapeHtml, formatMoney } from "../lib/format.js";
import { renderSidebar } from "../lib/sidebar.js";
import { reportError, showToast } from "../lib/toast.js";
import { setupAbonoDialog, setupCustomerDialog } from "./customer-dialogs.js";

renderSidebar("clientes.html");

/** @typedef {import("../lib/api.js").Customer} Customer */

/** @type {{ customers: Customer[] }} */
const state = { customers: [] };

const table = /** @type {HTMLElement} */ (document.getElementById("customerTable"));
const rows = /** @type {HTMLElement} */ (document.getElementById("customerRows"));
const emptyState = /** @type {HTMLElement} */ (document.getElementById("customerEmpty"));
const summary = /** @type {HTMLElement} */ (document.getElementById("customerSummary"));
const search = /** @type {HTMLInputElement} */ (document.getElementById("customerSearch"));
const filter = /** @type {HTMLSelectElement} */ (document.getElementById("customerFilter"));

/**
 * Aplica búsqueda y filtro en el cliente: la lista ya está cargada.
 * @returns {Customer[]}
 */
function visibleCustomers() {
    const query = search.value.trim().toLowerCase();
    return state.customers.filter(c => {
        if (filter.value === "debt" && c.balance <= 0) return false;
        return !query || [c.name, c.phone].some(v => (v ?? "").toLowerCase().includes(query));
    });
}

/**
 * @param {Customer} c
 * @returns {string} Renglón de la tabla. El abono solo se ofrece si el cliente debe algo.
 */
function customerRow(c) {
    const name = escapeHtml(c.name);
    const debt = c.balance > 0
        ? `<span class="badge badge-warning">${formatMoney(c.balance)}</span>`
        : formatMoney(c.balance);
    const abono = c.balance > 0
        ? `<button type="button" class="btn btn-ghost btn-small" data-abono="${c.id}" aria-label="Registrar abono de ${name}">Abonar</button>`
        : "";
    return `
        <tr>
            <td><span class="product-title">${name}</span></td>
            <td class="muted">${escapeHtml(c.phone ?? "—")}</td>
            <td class="num">${debt}</td>
            <td class="num muted">${formatMoney(c.credit_limit)}</td>
            <td class="num">${formatMoney(Math.max(c.credit_limit - c.balance, 0))}</td>
            <td class="actions">
                ${abono}
                <button type="button" class="icon-btn manager-only" data-edit="${c.id}" aria-label="Editar ${name}" title="Editar">
                    <i class="fa-solid fa-pen" aria-hidden="true"></i>
                </button>
            </td>
        </tr>`;
}

/** Pinta la tabla y el total de arriba: cuántos clientes y cuánto deben en conjunto. */
function render() {
    const customers = visibleCustomers();
    rows.innerHTML = customers.map(customerRow).join("");
    emptyState.hidden = customers.length > 0;
    emptyState.querySelector("p").textContent = state.customers.length === 0
        ? "Aún no hay clientes."
        : "Ningún cliente coincide con la búsqueda.";

    const total = state.customers.length;
    const debt = state.customers.reduce((sum, c) => sum + Math.round(c.balance * 100), 0) / 100;
    summary.textContent = `${total} cliente${total === 1 ? "" : "s"} · Te deben ${formatMoney(debt)}`;
}

async function loadCustomers() {
    table.setAttribute("aria-busy", "true");
    try {
        state.customers = await getCustomers();
        render();
    } catch (err) {
        summary.textContent = "No se pudieron cargar los clientes";
        reportError(err, "Error inesperado al cargar los clientes");
    } finally {
        table.setAttribute("aria-busy", "false");
    }
}

/** @param {string} message */
function afterSave(message) {
    showToast(message);
    loadCustomers();
}

const customerDialog = setupCustomerDialog(afterSave);
const abonoDialog = setupAbonoDialog(afterSave);

document.getElementById("btnNewCustomer")?.addEventListener("click", () => customerDialog.open());
search.addEventListener("input", render);
filter.addEventListener("change", render);

// Cada renglón tiene dos acciones: abonar y editar
rows.addEventListener("click", event => {
    const target = /** @type {HTMLElement} */ (event.target);
    const abono = /** @type {HTMLElement|null} */ (target.closest("[data-abono]"));
    const edit = /** @type {HTMLElement|null} */ (target.closest("[data-edit]"));
    const customer = state.customers.find(c => c.id === Number(abono?.dataset.abono ?? edit?.dataset.edit));
    if (!customer) return;
    if (abono) abonoDialog.open(customer);
    else customerDialog.open(customer);
});

loadCustomers();
