/** Ventana de cobro: método de pago, efectivo recibido y cambio. */

import { escapeHtml, formatMoney } from "../lib/format.js";

/** @typedef {import("./checkout.js").PaymentChoice} PaymentChoice */

/** Billetes para los botones de cobro rápido. */
const BILLS = [20, 50, 100, 200, 500, 1000];
const MAX_QUICK_BUTTONS = 4;

/**
 * Montos sugeridos: el exacto y los billetes que alcanzan a cubrir el total.
 * @param {number} total
 * @returns {number[]}
 */
export function quickCashOptions(total) {
    const options = new Set([total]);
    for (const bill of BILLS) {
        if (options.size >= MAX_QUICK_BUTTONS) break;
        const rounded = Math.ceil(total / bill) * bill;
        if (rounded > total) options.add(rounded);
    }
    return [...options].sort((a, b) => a - b);
}

/**
 * Conecta la ventana de cobro.
 * @param {Object} options
 * @param {(payment: PaymentChoice) => Promise<void>} options.onConfirm Registra la
 *     venta; si lanza un error, la ventana sigue abierta y lo muestra.
 * @returns {{ open: (total: number) => void }}
 *     También regresa ``setCustomers(customers)`` con los clientes a los que se puede fiar.
 */
export function setupPaymentDialog({ onConfirm }) {
    const dialog = /** @type {HTMLDialogElement} */ (document.getElementById("paymentDialog"));
    const form = /** @type {HTMLFormElement} */ (document.getElementById("paymentForm"));
    const totalLabel = /** @type {HTMLElement} */ (document.getElementById("payTotal"));
    const cashSection = /** @type {HTMLElement} */ (document.getElementById("cashSection"));
    const receivedInput = /** @type {HTMLInputElement} */ (document.getElementById("cashReceived"));
    const quickButtons = /** @type {HTMLElement} */ (document.getElementById("quickCash"));
    const changeLabel = /** @type {HTMLElement} */ (document.getElementById("cashChange"));
    const errorBox = /** @type {HTMLElement} */ (document.getElementById("payError"));
    const confirmButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnConfirmPay"));

    const creditSection = /** @type {HTMLElement} */ (document.getElementById("creditSection"));
    const creditSelect = /** @type {HTMLSelectElement} */ (document.getElementById("creditCustomer"));
    const creditHint = /** @type {HTMLElement} */ (document.getElementById("creditHint"));

    let total = 0;

    /** @type {import("../lib/api.js").Customer[]} Clientes para la opción de fiado. */
    let customers = [];

    /**
     * Lo que aún se le puede fiar al cliente elegido.
     * @returns {number|null} Null si no hay cliente elegido.
     */
    function availableCredit() {
        const customer = customers.find(c => c.id === Number(creditSelect.value));
        return customer ? customer.credit_limit - customer.balance : null;
    }

    /** Muestra el crédito disponible; regresa si alcanza para esta venta. */
    function updateCredit() {
        const available = availableCredit();
        if (available === null) {
            creditHint.textContent = customers.length ? "" : "No hay clientes: dalos de alta en Clientes.";
            return false;
        }
        const enough = available >= total;
        creditHint.textContent = `Disponible: ${formatMoney(available)}${enough ? "" : " · No alcanza para esta venta"}`;
        return enough;
    }

    /** @returns {PaymentChoice["method"]} */
    const selectedMethod = () =>
        /** @type {PaymentChoice["method"]} */ (new FormData(form).get("method") ?? "efectivo");

    /** @returns {number|null} */
    function received() {
        const value = parseFloat(receivedInput.value);
        return Number.isFinite(value) ? value : null;
    }

    function update() {
        const isCash = selectedMethod() === "efectivo";
        cashSection.hidden = !isCash;

        // Fiado: exige un cliente con crédito suficiente
        const isCredit = selectedMethod() === "venta_credito";
        creditSection.hidden = !isCredit;
        const creditBlocked = isCredit && !updateCredit();

        const cash = received();
        const short = creditBlocked || (isCash && (cash === null || cash < total));
        changeLabel.textContent = isCash && cash !== null && cash >= total
            ? formatMoney(cash - total)
            : "—";
        confirmButton.disabled = short;
    }

    function open(newTotal) {
        total = newTotal;
        form.reset();
        errorBox.hidden = true;
        totalLabel.textContent = formatMoney(total);
        confirmButton.textContent = `Cobrar ${formatMoney(total)}`;

        quickButtons.innerHTML = quickCashOptions(total)
            .map(amount => `<button type="button" class="chip" data-amount="${amount}">`
                + `${amount === total ? "Exacto" : formatMoney(amount)}</button>`)
            .join("");

        update();
        dialog.showModal();
        receivedInput.focus();
    }

    async function submit(event) {
        event.preventDefault();
        const method = selectedMethod();

        confirmButton.disabled = true;
        confirmButton.textContent = "Registrando venta…";
        errorBox.hidden = true;
        try {
            await onConfirm({
                method,
                received: method === "efectivo" ? received() : null,
                customerId: method === "venta_credito" ? Number(creditSelect.value) : null,
            });
            dialog.close();
        } catch (err) {
            errorBox.textContent = err instanceof Error ? err.message : "Error al registrar la venta";
            errorBox.hidden = false;
        } finally {
            confirmButton.textContent = `Cobrar ${formatMoney(total)}`;
            update();
        }
    }

    quickButtons.addEventListener("click", event => {
        const button = /** @type {HTMLElement} */ (event.target).closest("[data-amount]");
        if (!button) return;
        receivedInput.value = /** @type {HTMLElement} */ (button).dataset.amount ?? "";
        update();
        confirmButton.focus();
    });
    form.addEventListener("input", update);
    form.addEventListener("submit", submit);
    document.getElementById("btnCancelPay")?.addEventListener("click", () => dialog.close());

    /**
     * Carga la lista de clientes para fiar; conserva el elegido si sigue existiendo.
     * @param {import("../lib/api.js").Customer[]} list
     */
    function setCustomers(list) {
        customers = list;
        const chosen = creditSelect.value;
        creditSelect.innerHTML = '<option value="">Elige un cliente</option>'
            + list.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
        creditSelect.value = list.some(c => String(c.id) === chosen) ? chosen : "";
    }

    return { open, setCustomers };
}
