/** Aviso flotante breve; el contenedor usa aria-live para lectores de pantalla. */

import { ApiError } from "./api.js";

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

/**
 * Muestra un error al usuario; los que no vienen de la API se registran en consola.
 * @param {unknown} err
 * @param {string} fallback Mensaje si el error no es de la API.
 */
export function reportError(err, fallback) {
    if (!(err instanceof ApiError)) console.error(err);
    showToast(err instanceof ApiError ? err.message : fallback);
}
