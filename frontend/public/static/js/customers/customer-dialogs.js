/** Ventanas de Clientes: alta o edición del cliente y registro de abonos. */

import {
    addCustomerPayment,
    ApiError,
    createCustomer,
    getCustomerPayments,
    updateCustomer,
} from "../lib/api.js";
import { escapeHtml, formatDateTime, formatMoney, paymentMethodLabel } from "../lib/format.js";

/** @typedef {import("../lib/api.js").Customer} Customer */

const MONEY_PATTERN = /^\d{1,10}(\.\d{1,2})?$/; // Mismo límite que el backend

/**
 * Muestra el error de una petición en la caja de error de una ventana.
 * @param {HTMLElement} box
 * @param {unknown} err
 * @param {string} fallback Mensaje si el error no es de la API.
 */
function showRequestError(box, err, fallback) {
    if (!(err instanceof ApiError)) console.error(err);
    box.textContent = err instanceof ApiError ? err.message : fallback;
    box.hidden = false;
}

/**
 * Ventana de alta o edición de un cliente.
 * @param {(message: string) => void} onSaved Se llama tras guardar.
 * @returns {{ open: (customer?: Customer) => void }} Sin cliente abre un alta.
 */
export function setupCustomerDialog(onSaved) {
    const dialog = /** @type {HTMLDialogElement} */ (document.getElementById("customerDialog"));
    const form = /** @type {HTMLFormElement} */ (document.getElementById("customerForm"));
    const title = /** @type {HTMLElement} */ (document.getElementById("customerDialogTitle"));
    const nameInput = /** @type {HTMLInputElement} */ (document.getElementById("customerName"));
    const phoneInput = /** @type {HTMLInputElement} */ (document.getElementById("customerPhone"));
    const limitInput = /** @type {HTMLInputElement} */ (document.getElementById("customerLimit"));
    const errorBox = /** @type {HTMLElement} */ (document.getElementById("customerError"));
    const saveButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnSaveCustomer"));

    /** @type {number|null} Cliente que se edita; null si es un alta. */
    let editingId = null;

    /** @param {Customer} [customer] */
    function open(customer) {
        editingId = customer?.id ?? null;
        title.textContent = customer ? "Editar cliente" : "Nuevo cliente";
        nameInput.value = customer?.name ?? "";
        phoneInput.value = customer?.phone ?? "";
        limitInput.value = String(customer?.credit_limit ?? 0);
        errorBox.hidden = true;
        dialog.showModal();
        nameInput.focus();
    }

    /** @param {SubmitEvent} event */
    async function submit(event) {
        event.preventDefault();
        errorBox.hidden = true;

        const name = nameInput.value.trim();
        const limit = limitInput.value.trim() || "0";
        if (!name || !MONEY_PATTERN.test(limit)) {
            errorBox.textContent = name ? "Revisa el límite de fiado." : "Escribe el nombre del cliente.";
            errorBox.hidden = false;
            return;
        }

        const data = { name, phone: phoneInput.value.trim() || null, credit_limit: parseFloat(limit) };
        saveButton.disabled = true;
        try {
            if (editingId === null) await createCustomer(data);
            else await updateCustomer(editingId, data);
            dialog.close();
            onSaved(editingId === null ? "Cliente creado" : "Cliente actualizado");
        } catch (err) {
            showRequestError(errorBox, err, "No se pudo guardar el cliente");
        } finally {
            saveButton.disabled = false;
        }
    }

    form.addEventListener("submit", submit);
    document.getElementById("btnCancelCustomer")?.addEventListener("click", () => dialog.close());
    document.getElementById("btnCloseCustomer")?.addEventListener("click", () => dialog.close());

    return { open };
}

/**
 * Ventana para registrar un abono y ver los anteriores.
 * @param {(message: string) => void} onSaved Se llama tras registrar.
 * @returns {{ open: (customer: Customer) => void }}
 */
export function setupAbonoDialog(onSaved) {
    const dialog = /** @type {HTMLDialogElement} */ (document.getElementById("abonoDialog"));
    const form = /** @type {HTMLFormElement} */ (document.getElementById("abonoForm"));
    const customerLabel = /** @type {HTMLElement} */ (document.getElementById("abonoCustomer"));
    const debtLabel = /** @type {HTMLElement} */ (document.getElementById("abonoDebt"));
    const amountInput = /** @type {HTMLInputElement} */ (document.getElementById("abonoAmount"));
    const methodSelect = /** @type {HTMLSelectElement} */ (document.getElementById("abonoMethod"));
    const errorBox = /** @type {HTMLElement} */ (document.getElementById("abonoError"));
    const history = /** @type {HTMLElement} */ (document.getElementById("abonoHistory"));
    const saveButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnSaveAbono"));

    /** @type {Customer|null} */
    let customer = null;

    /** Carga los abonos anteriores; si falla, igual se puede registrar uno nuevo. */
    async function loadHistory() {
        if (!customer) return;
        history.textContent = "Cargando…";
        try {
            const payments = await getCustomerPayments(customer.id);
            history.innerHTML = payments.length
                ? payments.map(p => `<li><span>${formatDateTime(p.created_at)} · ${escapeHtml(paymentMethodLabel(p.method))}</span>`
                    + `<strong>${formatMoney(p.amount)}</strong></li>`).join("")
                : '<li class="muted">Sin abonos todavía</li>';
        } catch (err) {
            if (!(err instanceof ApiError)) console.error(err);
            history.textContent = "No se pudieron cargar los abonos.";
        }
    }

    /** @param {Customer} target */
    function open(target) {
        customer = target;
        form.reset();
        customerLabel.textContent = target.name;
        debtLabel.textContent = formatMoney(target.balance);
        errorBox.hidden = true;
        dialog.showModal();
        amountInput.focus();
        loadHistory();
    }

    /** @param {SubmitEvent} event */
    async function submit(event) {
        event.preventDefault();
        if (!customer) return;
        errorBox.hidden = true;

        const text = amountInput.value.trim();
        const amount = parseFloat(text);
        if (!MONEY_PATTERN.test(text) || amount <= 0) {
            errorBox.textContent = "Escribe un importe mayor que cero.";
            errorBox.hidden = false;
            amountInput.focus();
            return;
        }

        saveButton.disabled = true;
        try {
            await addCustomerPayment(customer.id, amount, methodSelect.value);
            dialog.close();
            onSaved(`Abono de ${formatMoney(amount)} registrado a ${customer.name}`);
        } catch (err) {
            showRequestError(errorBox, err, "No se pudo registrar el abono");
        } finally {
            saveButton.disabled = false;
        }
    }

    form.addEventListener("submit", submit);
    document.getElementById("btnCancelAbono")?.addEventListener("click", () => dialog.close());
    document.getElementById("btnCloseAbono")?.addEventListener("click", () => dialog.close());

    return { open };
}
