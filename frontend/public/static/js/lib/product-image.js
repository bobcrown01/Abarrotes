/**
 * Imágenes de producto guardadas en el frontend.
 *
 * Regla: la foto de un producto es ``static/img/<código de barras>.png``.
 * Si el producto no tiene código o el archivo no existe, se muestran sus
 * iniciales sobre un color de su categoría.
 */

import { escapeHtml } from "./format.js";

const IMAGE_DIR = "static/img";
const TILE_COLORS = 8; // --tile-0 … --tile-7 en app.css

/** @typedef {import("./api.js").Product} Product */

/**
 * Dos letras: iniciales de las dos primeras palabras del nombre.
 * @param {string} name
 * @returns {string}
 */
export function initials(name) {
    const words = name.trim().split(/\s+/);
    return (words.length > 1 ? words[0][0] + words[1][0] : name.slice(0, 2)).toUpperCase();
}

/**
 * Ruta esperada de la foto, o null si el producto no tiene código de barras.
 * @param {Product} product
 * @returns {string|null}
 */
export function productImageUrl(product) {
    return product.barcode ? `${IMAGE_DIR}/${encodeURIComponent(product.barcode)}.png` : null;
}

/**
 * Avatar del producto: la foto encima de las iniciales. Si la foto no carga,
 * :func:`enableImageFallback` la quita y quedan visibles las iniciales.
 * @param {Product} product
 * @param {string} [extraClass] Clase de tamaño, p. ej. "avatar-sm".
 * @returns {string} HTML.
 */
export function productAvatar(product, extraClass = "") {
    const url = productImageUrl(product);
    const img = url ? `<img src="${escapeHtml(url)}" alt="" loading="lazy" decoding="async">` : "";
    return `<span class="product-avatar tile-${product.category_id % TILE_COLORS} ${extraClass}" aria-hidden="true">`
        + `<span class="avatar-initials">${escapeHtml(initials(product.name))}</span>${img}</span>`;
}

/**
 * Quita las fotos que no existen dentro de un contenedor (un solo listener).
 * El evento ``error`` de las imágenes no burbujea, por eso se escucha en captura.
 * @param {HTMLElement} container
 */
export function enableImageFallback(container) {
    container.addEventListener(
        "error",
        event => {
            const target = event.target;
            if (target instanceof HTMLImageElement && target.closest(".product-avatar")) {
                target.remove();
            }
        },
        true,
    );
}
