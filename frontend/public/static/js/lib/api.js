/**
 * Cliente HTTP de la API del POS.
 *
 * Los typedefs reflejan los esquemas Pydantic de backend/app/schemas/product.py;
 * si cambia uno, hay que actualizar el otro.
 */

const API_BASE = "/api";
const REQUEST_TIMEOUT_MS = 10000;

/**
 * @typedef {Object} Category
 * @property {number} id
 * @property {string} name
 */

/**
 * @typedef {"pieza"|"kg"|"litro"|"paquete"|"caja"} Unit
 */

/**
 * @typedef {Object} ProductCreate
 * @property {string} name
 * @property {number} category_id
 * @property {string|null} barcode
 * @property {string|null} sku
 * @property {number} price
 * @property {number|null} cost
 * @property {Unit} unit
 * @property {boolean} is_active
 */

/**
 * @typedef {ProductCreate & {id: number}} Product
 */

/** Error de la API con un mensaje listo para mostrarse al usuario. */
export class ApiError extends Error {
    /**
     * @param {string} message Mensaje para el usuario.
     * @param {number} status Código HTTP (0 si no hubo respuesta).
     */
    constructor(message, status) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

/**
 * Extrae un mensaje legible de una respuesta de error de FastAPI.
 * @param {unknown} body Cuerpo JSON de la respuesta.
 * @returns {string}
 */
function errorMessage(body) {
    const detail = /** @type {{detail?: unknown}} */ (body)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "Datos inválidos: " + detail.map(e => e.msg).join(", ");
    return "Error al comunicarse con el servidor";
}

/**
 * Hace una petición JSON a la API.
 * @template T
 * @param {string} path Ruta relativa a /api.
 * @param {RequestInit} [options]
 * @returns {Promise<T>}
 * @throws {ApiError}
 */
async function request(path, options = {}) {
    let response;
    try {
        response = await fetch(API_BASE + path, {
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
            ...options,
        });
    } catch (err) {
        const timedOut = err instanceof DOMException && err.name === "TimeoutError";
        throw new ApiError(
            timedOut ? "El servidor tardó demasiado en responder" : "Sin conexión con el servidor",
            0,
        );
    }

    const body = await response.json().catch(() => null);
    if (!response.ok) throw new ApiError(errorMessage(body), response.status);
    return /** @type {T} */ (body);
}

/** @returns {Promise<Category[]>} */
export const getCategories = () => request("/categories");

/** @returns {Promise<Product[]>} */
export const getProducts = () => request("/products");

/**
 * @param {ProductCreate} data
 * @returns {Promise<Product>}
 */
export const createProduct = data =>
    request("/products", { method: "POST", body: JSON.stringify(data) });
