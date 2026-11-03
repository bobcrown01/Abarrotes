/**
 * Cliente HTTP de la API del POS.
 *
 * Los typedefs reflejan los esquemas Pydantic de backend/app/schemas/product.py;
 * si cambia uno, hay que actualizar el otro.
 */

const API_BASE = "/api";
const REQUEST_TIMEOUT_MS = 10000;
const HTTP_UNAUTHORIZED = 401;

/** Lleva al login recordando la pantalla actual para volver después de entrar. */
export function redirectToLogin() {
    const page = window.location.pathname.split("/").pop() || "index.html";
    window.location.href = `login.html?next=${encodeURIComponent(page)}`;
}

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

    // Sesión vencida o inexistente: se manda al login y se regresa a esta pantalla.
    // Las rutas /auth/ se excluyen para que la pantalla de login maneje sus errores.
    if (response.status === HTTP_UNAUTHORIZED && !path.startsWith("/auth/")) {
        redirectToLogin();
    }

    const body = await response.json().catch(() => null);
    if (!response.ok) throw new ApiError(errorMessage(body), response.status);
    return /** @type {T} */ (body);
}

/**
 * Arma una cadena de consulta omitiendo los valores vacíos.
 * @param {Record<string, string|number|undefined>} params
 * @returns {string} Con "?" inicial, o vacía si no hay valores.
 */
function toQuery(params) {
    const entries = Object.entries(params)
        .filter(([, value]) => value !== undefined && value !== "")
        .map(([key, value]) => [key, String(value)]);
    return entries.length ? `?${new URLSearchParams(entries)}` : "";
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
 * Guarda los cambios de un producto. Responde 409 si el código de barras ya lo usa otro.
 * @param {number} productId
 * @param {ProductCreate} data
 * @returns {Promise<Product>}
 */
export const updateProduct = (productId, data) =>
    request(`/products/${productId}`, { method: "PUT", body: JSON.stringify(data) });

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
 * @property {number|null} user_id
 * @property {string} created_at
 * @property {{id: number, product_id: number, qty: number, price: number, subtotal: number}[]} items
 * @property {{id: number, method: string, amount: number, change: number|null}[]} payments
 */

/**
 * @typedef {Object} SaleSummary
 * @property {number} id
 * @property {string|null} folio
 * @property {"pendiente"|"pagada"|"cancelada"} status
 * @property {number|null} user_id
 * @property {number} total
 * @property {string} created_at
 */

/** @returns {Promise<User[]>} */
export const getUsers = () => request("/users");

/**
 * @param {number} userId Cajero que hace la venta.
 * @param {number|null} [customerId] Cliente, obligatorio si la venta es a fiado.
 * @returns {Promise<Sale>}
 */
export const createSale = (userId, customerId = null) =>
    request("/sales", {
        method: "POST",
        body: JSON.stringify({ user_id: userId, customer_id: customerId }),
    });

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

/**
 * @typedef {Object} SaleFilters
 * @property {string} [status] pendiente, pagada o cancelada.
 * @property {string} [folio] Coincidencia parcial.
 * @property {string} [start] Instante ISO 8601 (incluido).
 * @property {string} [end] Instante ISO 8601 (excluido).
 */

/**
 * Ventas más recientes primero.
 * @param {SaleFilters & {limit: number, offset: number}} filters
 * @returns {Promise<SaleSummary[]>}
 */
export const getSales = filters => request(`/sales${toQuery(filters)}`);

/**
 * Número y total de las ventas pagadas que coinciden con los filtros.
 * @param {SaleFilters} filters
 * @returns {Promise<{count: number, total: number}>}
 */
export const getSalesSummary = filters => request(`/sales/summary${toQuery(filters)}`);

/**
 * @param {number} saleId
 * @returns {Promise<Sale>}
 */
export const getSale = saleId => request(`/sales/${saleId}`);

// ---------- Inventario (backend/app/schemas/inventory.py) ----------

/**
 * @typedef {"entrada"|"salida"|"ajuste"} MovementType
 */

/**
 * @typedef {Object} Stock
 * @property {number} product_id
 * @property {string} product_name
 * @property {number} quantity
 * @property {number} min_stock
 * @property {number|null} max_stock
 * @property {string|null} unit
 * @property {boolean} is_active
 */

/**
 * @typedef {Object} Movement
 * @property {number} movement_id
 * @property {number} product_id
 * @property {string} product_name
 * @property {MovementType} type
 * @property {number} quantity
 * @property {string|null} reason
 * @property {string} created_at
 * @property {number|null} user_id
 */

/**
 * @typedef {Object} MovementCreate
 * @property {number} product_id
 * @property {MovementType} type
 * @property {number} quantity Un ajuste fija las existencias en este valor.
 * @property {string|null} reason
 */

/**
 * Existencias de los productos que ya llevan inventario.
 * @param {{limit: number, offset: number}} page
 * @returns {Promise<Stock[]>}
 */
export const getStock = page => request(`/inventory${toQuery(page)}`);

/**
 * @param {{limit: number, offset: number, type?: MovementType}} filters
 * @returns {Promise<Movement[]>}
 */
export const getMovements = filters => request(`/inventory/movements${toQuery(filters)}`);

/**
 * Responde 409 si una salida deja existencias negativas.
 * @param {MovementCreate} data
 * @returns {Promise<unknown>}
 */
export const createMovement = data =>
    request("/inventory/movements", { method: "POST", body: JSON.stringify(data) });

/**
 * Define desde cuánto un producto se marca "Por surtir".
 * @param {number} productId
 * @param {number} minStock
 * @returns {Promise<Stock>}
 */
export const setMinStock = (productId, minStock) =>
    request(`/inventory/${productId}/min-stock`, {
        method: "PUT",
        body: JSON.stringify({ min_stock: minStock }),
    });

// ---------- Clientes y fiado (backend/app/schemas/customer.py) ----------

/**
 * @typedef {Object} Customer
 * @property {number} id
 * @property {string} name
 * @property {string|null} phone
 * @property {number} credit_limit Máximo que se le puede fiar.
 * @property {number} balance Lo que debe.
 */

/**
 * @typedef {Object} CustomerPayment
 * @property {number} id
 * @property {number} amount
 * @property {string} method
 * @property {number|null} user_id
 * @property {string} created_at
 */

/** @returns {Promise<Customer[]>} */
export const getCustomers = () => request("/customers");

/**
 * @param {{name: string, phone: string|null, credit_limit: number}} data
 * @returns {Promise<Customer>}
 */
export const createCustomer = data =>
    request("/customers", { method: "POST", body: JSON.stringify(data) });

/**
 * @param {number} customerId
 * @param {{name: string, phone: string|null, credit_limit: number}} data
 * @returns {Promise<Customer>}
 */
export const updateCustomer = (customerId, data) =>
    request(`/customers/${customerId}`, { method: "PUT", body: JSON.stringify(data) });

/**
 * Registra un abono. Responde 409 si excede la deuda o si la caja está cerrada.
 * @param {number} customerId
 * @param {number} amount
 * @param {string} method
 * @returns {Promise<CustomerPayment>}
 */
export const addCustomerPayment = (customerId, amount, method) =>
    request(`/customers/${customerId}/payments`, {
        method: "POST",
        body: JSON.stringify({ amount, method }),
    });

/**
 * Abonos de un cliente, los más recientes primero.
 * @param {number} customerId
 * @returns {Promise<CustomerPayment[]>}
 */
export const getCustomerPayments = customerId => request(`/customers/${customerId}/payments`);

// ---------- Reportes (backend/app/schemas/report.py) ----------

/**
 * @typedef {Object} SalesReport
 * @property {number} sales_count
 * @property {number} sales_total
 * @property {number} average_ticket
 * @property {number} profit Solo de productos con costo capturado.
 * @property {number} revenue_without_cost Venta que quedó fuera del cálculo de ganancia.
 * @property {{product_id: number, name: string, quantity: number, total: number}[]} top_products
 * @property {{product_id: number, name: string}[]} idle_products
 * @property {number} idle_total
 */

/**
 * Resumen de ventas del periodo (solo administración).
 * @param {{start?: string, end?: string}} range Instantes ISO 8601.
 * @returns {Promise<SalesReport>}
 */
export const getSalesReport = range => request(`/reports/sales${toQuery(range)}`);

// ---------- Caja (backend/app/schemas/cash.py) ----------

/**
 * Con la caja abierta, a un cajero no le llegan expected_cash, sales_total ni by_method.
 * @typedef {Object} CashSession
 * @property {number} id
 * @property {number|null} opened_by
 * @property {string} opened_at
 * @property {number} opening_amount
 * @property {number|null} closed_by
 * @property {string|null} closed_at
 * @property {number|null} counted_amount
 * @property {number|null} expected_cash
 * @property {number|null} difference Contado menos esperado.
 * @property {number|null} sales_total
 * @property {number|null} sales_count
 * @property {{method: string, amount: number}[]} by_method
 * @property {string|null} notes
 */

/**
 * Caja abierta, o session null si está cerrada.
 * @returns {Promise<{session: CashSession|null}>}
 */
export const getCurrentCash = () => request("/cash/current");

/**
 * Abre la caja. Responde 409 si ya está abierta.
 * @param {number} openingAmount Fondo inicial.
 * @returns {Promise<CashSession>}
 */
export const openCash = openingAmount =>
    request("/cash/open", { method: "POST", body: JSON.stringify({ opening_amount: openingAmount }) });

/**
 * Hace el corte. Responde 409 si la caja está cerrada.
 * @param {number} countedAmount Efectivo contado.
 * @param {string|null} notes
 * @returns {Promise<CashSession>}
 */
export const closeCash = (countedAmount, notes) =>
    request("/cash/close", {
        method: "POST",
        body: JSON.stringify({ counted_amount: countedAmount, notes }),
    });

/**
 * Cortes hechos, los más recientes primero (solo administración).
 * @param {{limit: number, offset: number}} page
 * @returns {Promise<CashSession[]>}
 */
export const getCashHistory = page => request(`/cash/sessions${toQuery(page)}`);

// ---------- Sesión (backend/app/schemas/auth.py) ----------

/**
 * @typedef {Object} CurrentUser
 * @property {number} id
 * @property {string} username
 * @property {string|null} role
 * @property {boolean} can_manage Puede cancelar ventas, ajustar inventario y cambiar el catálogo.
 */

/**
 * Indica si falta crear el primer administrador.
 * @returns {Promise<{needs_setup: boolean}>}
 */
export const getAuthStatus = () => request("/auth/status");

/**
 * Abre sesión; el backend guarda el token en una cookie que JavaScript no puede leer.
 * @param {string} username
 * @param {string} password Contraseña o PIN.
 * @returns {Promise<CurrentUser>}
 */
export const login = (username, password) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });

/**
 * Crea el primer administrador y le abre sesión.
 * @param {string} username
 * @param {string} password
 * @returns {Promise<CurrentUser>}
 */
export const setupAdmin = (username, password) =>
    request("/auth/setup", { method: "POST", body: JSON.stringify({ username, password }) });

/**
 * Cierra la sesión en el servidor.
 * @returns {Promise<null>}
 */
export const logout = () => request("/auth/logout", { method: "POST" });

/**
 * Usuario de la sesión. Responde 401 si no hay sesión.
 * @returns {Promise<CurrentUser>}
 */
export const getMe = () => request("/auth/me");

// ---------- Estado del sistema ----------

/**
 * Indica si responden el servidor y la base de datos. No lanza errores.
 * @returns {Promise<boolean>}
 */
export const checkHealth = () => request("/health/db").then(() => true, () => false);
