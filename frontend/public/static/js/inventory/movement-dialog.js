/** Ventana para registrar una entrada, una salida o un conteo físico. */

import { ApiError, createMovement } from "../lib/api.js";
import { formatQuantity } from "../lib/format.js";
import { allowsFraction } from "../pos/cart.js";

/** @typedef {import("../lib/api.js").Product} Product */
/** @typedef {import("../lib/api.js").MovementType} MovementType */

/** @type {Record<MovementType, {label: string, hint: string}>} */
const TYPE_TEXT = {
    entrada: { label: "Cantidad que entra", hint: "Se suma a las existencias." },
    salida: { label: "Cantidad que sale", hint: "Se resta de las existencias (merma, caducidad, consumo)." },
    ajuste: { label: "Cantidad contada", hint: "Las existencias quedan exactamente en esta cantidad." },
};

/**
 * @param {Object} options
 * @param {(message: string) => void} options.onSaved Se llama tras registrar.
 * @returns {{ open: (product: Product, quantity: number|null) => void }}
 */
export function setupMovementDialog({ onSaved }) {
    const dialog = /** @type {HTMLDialogElement} */ (document.getElementById("movementDialog"));
    const form = /** @type {HTMLFormElement} */ (document.getElementById("movementForm"));
    const productLabel = /** @type {HTMLElement} */ (document.getElementById("movementProduct"));
    const currentLabel = /** @type {HTMLElement} */ (document.getElementById("movementCurrent"));
    const quantityLabel = /** @type {HTMLElement} */ (document.getElementById("movementQuantityLabel"));
    const quantityInput = /** @type {HTMLInputElement} */ (document.getElementById("movementQuantity"));
    const hint = /** @type {HTMLElement} */ (document.getElementById("movementHint"));
    const errorBox = /** @type {HTMLElement} */ (document.getElementById("movementError"));
    const saveButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnSaveMovement"));

    /** @type {Product|null} */
    let product = null;

    /** @returns {MovementType} */
    function selectedType() {
        return /** @type {MovementType} */ (new FormData(form).get("type"));
    }

    function syncTypeText() {
        const text = TYPE_TEXT[selectedType()];
        quantityLabel.textContent = text.label;
        hint.textContent = text.hint;
    }

    /** @param {string} message */
    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
    }

    /**
     * @returns {string|null} Mensaje de error, o null si la cantidad es válida.
     */
    function quantityError() {
        const value = Number(quantityInput.value);
        const isCount = selectedType() === "ajuste";
        if (quantityInput.value === "" || !Number.isFinite(value) || value < 0 || (!isCount && value === 0)) {
            return isCount ? "Escribe la cantidad contada" : "La cantidad debe ser mayor que cero";
        }
        if (product && !allowsFraction(product) && !Number.isInteger(value)) {
            return "Este producto se maneja en cantidades enteras";
        }
        if (Math.round(value * 1000) / 1000 !== value) return "Usa máximo tres decimales";
        return null;
    }

    /**
     * @param {Product} target
     * @param {number|null} quantity Existencias actuales; null si aún no lleva control.
     */
    function open(target, quantity) {
        product = target;
        form.reset();

        productLabel.textContent = target.name;
        currentLabel.textContent = quantity === null
            ? "Aún sin control de existencias: este movimiento lo inicia."
            : `Existencias actuales: ${formatQuantity(quantity)}`;
        quantityInput.step = allowsFraction(target) ? "0.001" : "1";
        quantityInput.removeAttribute("aria-invalid");
        errorBox.hidden = true;
        syncTypeText();
        dialog.showModal();
        quantityInput.focus();
    }

    /** @param {SubmitEvent} event */
    async function submit(event) {
        event.preventDefault();
        if (!product) return;

        const invalid = quantityError();
        if (invalid) {
            quantityInput.setAttribute("aria-invalid", "true");
            showError(invalid);
            quantityInput.focus();
            return;
        }

        quantityInput.removeAttribute("aria-invalid");
        errorBox.hidden = true;
        saveButton.disabled = true;
        const reason = String(new FormData(form).get("reason") ?? "").trim();
        try {
            await createMovement({
                product_id: product.id,
                type: selectedType(),
                quantity: Number(quantityInput.value),
                reason: reason || null,
            });
            dialog.close();
            onSaved(`Inventario de «${product.name}» actualizado`);
        } catch (err) {
            if (!(err instanceof ApiError)) console.error(err);
            showError(err instanceof ApiError ? err.message : "No se pudo registrar el movimiento");
        } finally {
            saveButton.disabled = false;
        }
    }

    form.addEventListener("submit", submit);
    form.addEventListener("change", event => {
        if (/** @type {HTMLInputElement} */ (event.target).name === "type") syncTypeText();
    });
    document.getElementById("btnCancelMovement")?.addEventListener("click", () => dialog.close());
    document.getElementById("btnCloseMovement")?.addEventListener("click", () => dialog.close());

    return { open };
}
