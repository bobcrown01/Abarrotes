/** Ventana para definir desde cuánto un producto se marca "Por surtir". */

import { ApiError, setMinStock } from "../lib/api.js";
import { allowsFraction } from "../pos/cart.js";

/** @typedef {import("../lib/api.js").Product} Product */
/** @typedef {import("../lib/api.js").Stock} Stock */

/**
 * @param {Object} options
 * @param {(message: string) => void} options.onSaved Se llama tras guardar.
 * @returns {{ open: (product: Product, stock: Stock|undefined) => void }}
 */
export function setupMinStockDialog({ onSaved }) {
    const dialog = /** @type {HTMLDialogElement} */ (document.getElementById("minStockDialog"));
    const form = /** @type {HTMLFormElement} */ (document.getElementById("minStockForm"));
    const productLabel = /** @type {HTMLElement} */ (document.getElementById("minStockProduct"));
    const input = /** @type {HTMLInputElement} */ (document.getElementById("minStockValue"));
    const hint = /** @type {HTMLElement} */ (document.getElementById("minStockHint"));
    const errorBox = /** @type {HTMLElement} */ (document.getElementById("minStockError"));
    const saveButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnSaveMinStock"));

    /** @type {Product|null} */
    let product = null;

    /**
     * Abre la ventana con el mínimo actual del producto.
     * @param {Product} target
     * @param {Stock|undefined} stock Sin valor si aún no lleva control de existencias.
     */
    function open(target, stock) {
        product = target;
        productLabel.textContent = target.name;
        input.value = String(stock?.min_stock ?? 0);
        input.step = allowsFraction(target) ? "0.001" : "1";
        // Avisa que guardar un mínimo inicia el control de existencias en cero
        hint.textContent = stock
            ? "Con 0 nunca se marca; solo aparece como Agotado al quedarse sin existencias."
            : "Este producto aún no lleva control: empezará en 0 hasta que registres una entrada.";
        errorBox.hidden = true;
        dialog.showModal();
        input.select();
    }

    /** @param {SubmitEvent} event */
    async function submit(event) {
        event.preventDefault();
        if (!product) return;

        // Mismas reglas que el backend: no negativo y sin fracciones en piezas
        const value = Number(input.value);
        const valid = input.value !== "" && Number.isFinite(value) && value >= 0
            && (allowsFraction(product) ? Math.round(value * 1000) / 1000 === value : Number.isInteger(value));
        if (!valid) {
            errorBox.textContent = allowsFraction(product)
                ? "Escribe una cantidad con máximo tres decimales."
                : "Escribe una cantidad entera.";
            errorBox.hidden = false;
            input.focus();
            return;
        }

        errorBox.hidden = true;
        saveButton.disabled = true;
        try {
            await setMinStock(product.id, value);
            dialog.close();
            onSaved(`Mínimo de «${product.name}» actualizado`);
        } catch (err) {
            if (!(err instanceof ApiError)) console.error(err);
            errorBox.textContent = err instanceof ApiError ? err.message : "No se pudo guardar el mínimo";
            errorBox.hidden = false;
        } finally {
            saveButton.disabled = false;
        }
    }

    form.addEventListener("submit", submit);
    document.getElementById("btnCancelMinStock")?.addEventListener("click", () => dialog.close());
    document.getElementById("btnCloseMinStock")?.addEventListener("click", () => dialog.close());

    return { open };
}
