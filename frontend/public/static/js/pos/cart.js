/**
 * Carrito de la venta en curso. Solo lógica, sin DOM.
 *
 * Los importes se calculan en centavos enteros para evitar errores de
 * redondeo de float (0.1 + 0.2). El total definitivo lo calcula el backend;
 * este es el que ve el cajero mientras arma la venta.
 */

/** @typedef {import("../lib/api.js").Product} Product */

/**
 * @typedef {Object} CartLine
 * @property {Product} product
 * @property {number} qty
 */

/**
 * Importe de una línea en centavos.
 * @param {CartLine} line
 * @returns {number}
 */
export function lineCents(line) {
    return Math.round(line.product.price * 100 * line.qty);
}

/** Unidades que se venden por peso o volumen y aceptan fracciones. */
const FRACTIONAL_UNITS = new Set(["kg", "litro"]);

/**
 * @param {Product} product
 * @returns {boolean}
 */
export function allowsFraction(product) {
    return FRACTIONAL_UNITS.has(product.unit ?? "pieza");
}

export class Cart {
    /** @type {Map<number, CartLine>} */
    #lines = new Map();

    /** @type {Set<() => void>} */
    #listeners = new Set();

    /**
     * Se llama cada vez que cambia el carrito.
     * @param {() => void} listener
     */
    subscribe(listener) {
        this.#listeners.add(listener);
    }

    #notify() {
        this.#listeners.forEach(listener => listener());
    }

    /** @returns {CartLine[]} En el orden en que se agregaron. */
    get lines() {
        return [...this.#lines.values()];
    }

    get isEmpty() {
        return this.#lines.size === 0;
    }

    /** Número de artículos (las fracciones de kg cuentan como 1). */
    get itemCount() {
        return this.lines.reduce((sum, l) => sum + (allowsFraction(l.product) ? 1 : l.qty), 0);
    }

    /** Total en pesos. */
    get total() {
        return this.lines.reduce((sum, l) => sum + lineCents(l), 0) / 100;
    }

    /**
     * Agrega un producto; si ya está, suma la cantidad.
     * @param {Product} product
     * @param {number} [qty=1]
     */
    add(product, qty = 1) {
        const line = this.#lines.get(product.id);
        this.setQty(product.id, (line?.qty ?? 0) + qty, product);
    }

    /**
     * Fija la cantidad de una línea; 0 o menos la elimina.
     * @param {number} productId
     * @param {number} qty
     * @param {Product} [product] Necesario si la línea todavía no existe.
     */
    setQty(productId, qty, product) {
        const target = product ?? this.#lines.get(productId)?.product;
        if (!target) return;

        // Máximo tres decimales, igual que el backend (Numeric 14,3)
        const clean = allowsFraction(target) ? Math.round(qty * 1000) / 1000 : Math.round(qty);
        if (!Number.isFinite(clean) || clean <= 0) {
            this.#lines.delete(productId);
        } else {
            this.#lines.set(productId, { product: target, qty: clean });
        }
        this.#notify();
    }

    /** @param {number} productId */
    remove(productId) {
        this.#lines.delete(productId);
        this.#notify();
    }

    clear() {
        this.#lines.clear();
        this.#notify();
    }
}
