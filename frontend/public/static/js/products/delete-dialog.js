/**
 * Confirmación para eliminar un producto.
 *
 * Si el backend responde 409 (el producto tiene ventas o inventario), la
 * misma ventana ofrece desactivarlo, que conserva el historial.
 */

import { ApiError, deactivateProduct, deleteProduct } from "../lib/api.js";

/** @typedef {import("../lib/api.js").Product} Product */

const HTTP_CONFLICT = 409;

/**
 * @param {Object} options
 * @param {(message: string) => void} options.onDone Se llama tras eliminar o desactivar.
 * @returns {{ open: (product: Product) => void }}
 */
export function setupDeleteDialog({ onDone }) {
    const dialog = /** @type {HTMLDialogElement} */ (document.getElementById("deleteDialog"));
    const title = /** @type {HTMLElement} */ (document.getElementById("deleteTitle"));
    const message = /** @type {HTMLElement} */ (document.getElementById("deleteMessage"));
    const errorBox = /** @type {HTMLElement} */ (document.getElementById("deleteError"));
    const confirmButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnConfirmDelete"));

    /** @type {Product|null} */
    let product = null;
    /** @type {"delete"|"deactivate"} */
    let mode = "delete";

    function show(nextMode) {
        mode = nextMode;
        // Se usa textContent: el nombre viene de la base y no debe interpretarse como HTML
        const name = product?.name ?? "";
        errorBox.hidden = true;

        if (mode === "delete") {
            title.textContent = "Eliminar producto";
            message.textContent = `¿Eliminar «${name}»? Esta acción no se puede deshacer.`;
            confirmButton.textContent = "Eliminar";
            confirmButton.className = "btn btn-danger";
        } else {
            title.textContent = "No se puede eliminar";
            message.textContent = `«${name}» tiene ventas o movimientos de inventario. `
                + "Puedes desactivarlo: deja de aparecer en Vender pero se conserva su historial.";
            confirmButton.textContent = "Desactivar";
            confirmButton.className = "btn btn-primary";
        }
    }

    /** @param {Product} target */
    function open(target) {
        product = target;
        show("delete");
        dialog.showModal();
        // El foco empieza en Cancelar: evita borrar con un Enter accidental
        document.getElementById("btnCancelDelete")?.focus();
    }

    async function confirm() {
        if (!product) return;
        confirmButton.disabled = true;
        try {
            if (mode === "delete") {
                await deleteProduct(product.id);
                dialog.close();
                onDone(`«${product.name}» se eliminó`);
            } else {
                await deactivateProduct(product.id);
                dialog.close();
                onDone(`«${product.name}» se desactivó`);
            }
        } catch (err) {
            if (err instanceof ApiError && err.status === HTTP_CONFLICT && mode === "delete") {
                // Ya inactivo: no hay nada más que ofrecer
                if (product.is_active) {
                    show("deactivate");
                } else {
                    errorBox.textContent = "Tiene historial y ya está inactivo; no se puede eliminar.";
                    errorBox.hidden = false;
                }
            } else {
                if (!(err instanceof ApiError)) console.error(err);
                errorBox.textContent = err instanceof ApiError ? err.message : "Error inesperado";
                errorBox.hidden = false;
            }
        } finally {
            confirmButton.disabled = false;
        }
    }

    confirmButton.addEventListener("click", confirm);
    document.getElementById("btnCancelDelete")?.addEventListener("click", () => dialog.close());

    return { open };
}
