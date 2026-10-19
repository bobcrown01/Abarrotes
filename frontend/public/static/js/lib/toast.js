/** Aviso flotante breve; el contenedor usa aria-live para lectores de pantalla. */

const DURATION_MS = 3000;
let timer = 0;

/**
 * Muestra un mensaje temporal.
 * @param {string} message
 */
export function showToast(message) {
    const toast = /** @type {HTMLElement} */ (document.getElementById("toast"));
    toast.textContent = message;
    toast.hidden = false;
    clearTimeout(timer);
    timer = setTimeout(() => { toast.hidden = true; }, DURATION_MS);
}
