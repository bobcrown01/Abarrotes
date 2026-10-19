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

/**
 * Elimina un producto sin historial. Responde 409 si tiene ventas o inventario.
 * @param {number} productId
 * @returns {Promise<null>}
 */
export const deleteProduct = productId => request(`/products/${productId}`, { method: "DELETE" });

/**
 * Desactiva un producto: deja de venderse pero conserva su historial.
 * @param {number} productId
 * @returns {Promise<Product>}
 */
export const deactivateProduct = productId =>
    request(`/products/${productId}/deactivate`, { method: "POST" });

// ---------- Usuarios y ventas (backend/app/schemas/user.py y sale.py) ----------

/**
 * @typedef {Object} User
 * @property {number} id
 * @property {string} username
 * @property {number|null} role_id
 * @property {boolean} is_active
 */

/**
 * @typedef {"efectivo"|"debito"|"credito"|"transferencia"|"monedero"|"venta_credito"|"link_pago"} PaymentMethod
 */

/**
 * @typedef {Object} PaymentCreate
 * @property {number} sale_id
 * @property {PaymentMethod} method
 * @property {number} amount
 * @property {number|null} [received]
 * @property {string|null} [reference]
 */

/**
 * @typedef {Object} Sale
 * @property {number} id
 * @property {string} folio
 * @property {"pendiente"|"pagada"|"cancelada"} status
 * @property {number} total
 * @property {number} amount_paid
 * @property {{id: number, product_id: number, qty: number, price: number, subtotal: number}[]} items
 * @property {{id: number, method: string, amount: number, change: number|null}[]} payments
 */

/** @returns {Promise<User[]>} */
export const getUsers = () => request("/users");

/**
 * @param {number} userId Cajero que hace la venta.
 * @returns {Promise<Sale>}
 */
export const createSale = userId =>
    request("/sales", { method: "POST", body: JSON.stringify({ user_id: userId }) });

/**
 * El precio no se envía: el backend usa el del catálogo.
 * @param {{sale_id: number, product_id: number, qty: number}} item
 * @returns {Promise<Sale>}
 */
export const addSaleItem = item =>
    request("/sales/items", { method: "POST", body: JSON.stringify(item) });

/**
 * @param {PaymentCreate} payment
 * @returns {Promise<Sale>}
 */
export const addPayment = payment =>
    request("/sales/payments", { method: "POST", body: JSON.stringify(payment) });

/**
 * @param {number} saleId
 * @returns {Promise<Sale>}
 */
export const closeSale = saleId => request(`/sales/${saleId}/close`, { method: "POST" });

/**
 * @param {number} saleId
 * @returns {Promise<Sale>}
 */
export const cancelSale = saleId => request(`/sales/${saleId}/cancel`, { method: "POST" });
