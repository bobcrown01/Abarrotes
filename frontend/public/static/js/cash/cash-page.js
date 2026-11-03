/** Página de Corte de caja: abrir con fondo inicial, contar el efectivo y ver cortes anteriores. */

import {
    ApiError,
    closeCash,
    getCashHistory,
    getCurrentCash,
    getUsers,
    openCash,
} from "../lib/api.js";
import { escapeHtml, formatDateTime, formatMoney, paymentMethodLabel } from "../lib/format.js";
import { setupPager } from "../lib/pager.js";
import { getSession } from "../lib/session.js";
import { renderSidebar } from "../lib/sidebar.js";
import { reportError, showToast } from "../lib/toast.js";

renderSidebar("caja.html");

/** @typedef {import("../lib/api.js").CashSession} CashSession */

const HISTORY_PAGE_SIZE = 20;
const MONEY_PATTERN = /^\d{1,10}(\.\d{1,2})?$/; // Mismo límite que el backend

/** @type {{ userNames: Map<number, string> }} */
const state = { userNames: new Map() };

const el = {
    subtitle: /** @type {HTMLElement} */ (document.getElementById("cashSubtitle")),
    openForm: /** @type {HTMLFormElement} */ (document.getElementById("openForm")),
    openingAmount: /** @type {HTMLInputElement} */ (document.getElementById("openingAmount")),
    openError: /** @type {HTMLElement} */ (document.getElementById("openError")),
    openButton: /** @type {HTMLButtonElement} */ (document.getElementById("btnOpenCash")),
    openPanel: /** @type {HTMLElement} */ (document.getElementById("openPanel")),
    openDetails: /** @type {HTMLElement} */ (document.getElementById("openDetails")),
    openTotals: /** @type {HTMLElement} */ (document.getElementById("openTotals")),
    closeForm: /** @type {HTMLFormElement} */ (document.getElementById("closeForm")),
    counted: /** @type {HTMLInputElement} */ (document.getElementById("countedAmount")),
    notes: /** @type {HTMLInputElement} */ (document.getElementById("closeNotes")),
    closeError: /** @type {HTMLElement} */ (document.getElementById("closeError")),
    closeButton: /** @type {HTMLButtonElement} */ (document.getElementById("btnCloseCash")),
    resultPanel: /** @type {HTMLElement} */ (document.getElementById("resultPanel")),
    resultDetails: /** @type {HTMLElement} */ (document.getElementById("resultDetails")),
    historyRows: /** @type {HTMLElement} */ (document.getElementById("historyRows")),
    historyEmpty: /** @type {HTMLElement} */ (document.getElementById("historyEmpty")),
    historyPager: /** @type {HTMLElement} */ (document.getElementById("historyPager")),
};

/**
 * Texto y estilo de la diferencia entre lo contado y lo esperado.
 * @param {number|null} difference
 * @returns {string} HTML.
 */
function differenceBadge(difference) {
    if (difference === null) return "—";
    if (difference === 0) return '<span class="badge badge-success">Cuadra</span>';
    const label = difference < 0 ? "Faltante" : "Sobrante";
    const css = difference < 0 ? "badge-danger" : "badge-warning";
    return `<span class="badge ${css}">${label} ${formatMoney(Math.abs(difference))}</span>`;
}

/**
 * Tabla de cobros por método de pago.
 * @param {CashSession} session
 * @returns {string} HTML.
 */
function methodTotals(session) {
    const rows = session.by_method.map(m => `
        <tr>
            <td>${escapeHtml(paymentMethodLabel(m.method))}</td>
            <td class="num">${formatMoney(m.amount)}</td>
        </tr>`).join("");
    return `
        <div class="table-wrap">
            <table class="data-table detail-table">
                <caption class="visually-hidden">Cobros por método de pago</caption>
                <thead><tr><th scope="col">Método</th><th scope="col" class="num">Cobrado</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="2" class="muted">Sin ventas todavía</td></tr>'}</tbody>
            </table>
        </div>`;
}

/**
 * Muestra la caja abierta. A un cajero la API no le envía el esperado, así cuenta a ciegas.
 * @param {CashSession} session
 */
function showOpen(session) {
    el.subtitle.textContent = "La caja está abierta";
    el.openForm.hidden = true;
    el.openPanel.hidden = false;
    el.openDetails.innerHTML = `
        <div><dt>Abrió</dt><dd>${escapeHtml(state.userNames.get(session.opened_by) ?? "—")}</dd></div>
        <div><dt>Desde</dt><dd>${formatDateTime(session.opened_at)}</dd></div>
        <div><dt>Fondo inicial</dt><dd>${formatMoney(session.opening_amount)}</dd></div>
        ${session.expected_cash === null ? "" : `
        <div><dt>Efectivo esperado</dt><dd>${formatMoney(session.expected_cash)}</dd></div>
        <div><dt>Ventas</dt><dd>${session.sales_count} · ${formatMoney(session.sales_total)}</dd></div>`}`;
    el.openTotals.innerHTML = session.expected_cash === null ? "" : methodTotals(session);
}

/** Muestra la caja cerrada, lista para abrirse. */
function showClosed() {
    el.subtitle.textContent = "La caja está cerrada: ábrela para poder cobrar";
    el.openPanel.hidden = true;
    el.openForm.hidden = false;
    el.openingAmount.value = "";
    el.openingAmount.focus();
}

/**
 * Muestra el resultado de un corte recién hecho.
 * @param {CashSession} session
 */
function showResult(session) {
    el.resultPanel.hidden = false;
    el.resultDetails.innerHTML = `
        <dl class="detail-meta">
            <div><dt>Efectivo esperado</dt><dd>${formatMoney(session.expected_cash)}</dd></div>
            <div><dt>Efectivo contado</dt><dd>${formatMoney(session.counted_amount)}</dd></div>
            <div><dt>Resultado</dt><dd>${differenceBadge(session.difference)}</dd></div>
            <div><dt>Ventas</dt><dd>${session.sales_count} · ${formatMoney(session.sales_total)}</dd></div>
        </dl>
        ${methodTotals(session)}`;
}

/**
 * @param {CashSession} s
 * @returns {string}
 */
function historyRow(s) {
    return `
        <tr>
            <td class="muted">${s.closed_at ? formatDateTime(s.closed_at) : "—"}</td>
            <td>${escapeHtml(state.userNames.get(s.closed_by) ?? "—")}</td>
            <td class="num">${formatMoney(s.sales_total)}</td>
            <td class="num">${formatMoney(s.expected_cash)}</td>
            <td class="num">${formatMoney(s.counted_amount)}</td>
            <td class="num">${differenceBadge(s.difference)}</td>
            <td class="muted">${escapeHtml(s.notes ?? "—")}</td>
        </tr>`;
}

const historyPager = setupPager({
    container: el.historyPager,
    limit: HISTORY_PAGE_SIZE,
    fetchPage: getCashHistory,
    onPage: sessions => {
        el.historyRows.innerHTML = sessions.map(historyRow).join("");
        el.historyEmpty.hidden = sessions.length > 0;
    },
});

/**
 * Valida un importe tecleado y lo regresa como número.
 * @param {HTMLInputElement} input
 * @returns {number|null} Null si no es un importe válido.
 */
function readMoney(input) {
    return MONEY_PATTERN.test(input.value.trim()) ? parseFloat(input.value) : null;
}

/** @param {SubmitEvent} event */
async function submitOpen(event) {
    event.preventDefault();
    el.openError.hidden = true;
    const amount = readMoney(el.openingAmount);
    if (amount === null) {
        el.openError.textContent = "Escribe el fondo inicial; si no hay, escribe 0.";
        el.openError.hidden = false;
        el.openingAmount.focus();
        return;
    }
    el.openButton.disabled = true;
    try {
        const session = await openCash(amount);
        el.resultPanel.hidden = true;
        showOpen(session);
        showToast("Caja abierta");
    } catch (err) {
        if (!(err instanceof ApiError)) console.error(err);
        el.openError.textContent = err instanceof ApiError ? err.message : "No se pudo abrir la caja";
        el.openError.hidden = false;
    } finally {
        el.openButton.disabled = false;
    }
}

/** @param {SubmitEvent} event */
async function submitClose(event) {
    event.preventDefault();
    el.closeError.hidden = true;
    const amount = readMoney(el.counted);
    if (amount === null) {
        el.closeError.textContent = "Escribe el efectivo que contaste en la caja.";
        el.closeError.hidden = false;
        el.counted.focus();
        return;
    }
    el.closeButton.disabled = true;
    try {
        const session = await closeCash(amount, el.notes.value.trim() || null);
        el.closeForm.reset();
        showClosed();
        showResult(session);
        showToast("Corte de caja guardado");
        if (document.documentElement.hasAttribute("data-can-manage")) await historyPager.load(0);
    } catch (err) {
        if (!(err instanceof ApiError)) console.error(err);
        el.closeError.textContent = err instanceof ApiError ? err.message : "No se pudo hacer el corte";
        el.closeError.hidden = false;
    } finally {
        el.closeButton.disabled = false;
    }
}

el.openForm.addEventListener("submit", submitOpen);
el.closeForm.addEventListener("submit", submitClose);
el.historyPager.addEventListener("pagererror", event => {
    reportError(/** @type {CustomEvent} */ (event).detail, "No se pudieron cargar los cortes");
});

/** Carga el estado de la caja y, a los roles de administración, el historial. */
async function start() {
    try {
        const [user, users] = await Promise.all([getSession(), getUsers()]);
        state.userNames = new Map(users.map(u => [u.id, u.username]));

        const { session } = await getCurrentCash();
        if (session) showOpen(session);
        else showClosed();

        if (user.can_manage) await historyPager.load();
    } catch (err) {
        el.subtitle.textContent = "No se pudo consultar la caja";
        reportError(err, "Error inesperado al consultar la caja");
    }
}

start();
