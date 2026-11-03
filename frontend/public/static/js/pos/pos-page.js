/** Pantalla de venta: catálogo, carrito y cobro. */

import { ApiError, getCategories, getCurrentCash, getCustomers, getProducts } from "../lib/api.js";
import { escapeHtml, formatMoney } from "../lib/format.js";
import { enableImageFallback, productAvatar } from "../lib/product-image.js";
import { getSession } from "../lib/session.js";
import { renderSidebar } from "../lib/sidebar.js";
import { printTicket } from "../lib/ticket.js";
import { showToast } from "../lib/toast.js";
import { allowsFraction, Cart, lineCents } from "./cart.js";
import { checkout } from "./checkout.js";
import { setupPaymentDialog } from "./payment-dialog.js";

/** @typedef {import("../lib/api.js").Product} Product */
/** @typedef {import("../lib/api.js").Category} Category */

/** @type {{ products: Product[], categories: Category[], categoryId: number|null }} */
const state = { products: [], categories: [], categoryId: null };

/** Id del cajero con sesión abierta; hasta conocerlo no se puede cobrar. */
let cashierId = 0;

/** Si la caja está abierta; cerrada no se puede cobrar (el backend también lo exige). */
let cashOpen = false;

/** @type {import("../lib/api.js").Sale|null} Última venta cobrada, para imprimir su ticket. */
let lastSale = null;
const cart = new Cart();

const el = {
    search: /** @type {HTMLInputElement} */ (document.getElementById("posSearch")),
    chips: /** @type {HTMLElement} */ (document.getElementById("categoryChips")),
    grid: /** @type {HTMLElement} */ (document.getElementById("productGrid")),
    gridEmpty: /** @type {HTMLElement} */ (document.getElementById("gridEmpty")),
    cashier: /** @type {HTMLElement} */ (document.getElementById("cashierName")),
    cashNotice: /** @type {HTMLElement} */ (document.getElementById("cashClosedNotice")),
    printLast: /** @type {HTMLButtonElement} */ (document.getElementById("btnPrintLast")),
    lines: /** @type {HTMLElement} */ (document.getElementById("cartLines")),
    cartEmpty: /** @type {HTMLElement} */ (document.getElementById("cartEmpty")),
    count: /** @type {HTMLElement} */ (document.getElementById("cartCount")),
    total: /** @type {HTMLElement} */ (document.getElementById("cartTotal")),
    charge: /** @type {HTMLButtonElement} */ (document.getElementById("btnCharge")),
    clear: /** @type {HTMLButtonElement} */ (document.getElementById("btnClearCart")),
};

// ---------- Catálogo ----------

/** @returns {Product[]} */
function visibleProducts() {
    const query = el.search.value.trim().toLowerCase();
    return state.products.filter(p => {
        if (state.categoryId && p.category_id !== state.categoryId) return false;
        return !query || [p.name, p.barcode, p.sku].some(v => (v ?? "").toLowerCase().includes(query));
    });
}

function renderChips() {
    const chip = (id, label) => {
        const pressed = state.categoryId === id;
        return `<button type="button" class="chip" data-category="${id ?? ""}" aria-pressed="${pressed}">`
            + `${escapeHtml(label)}</button>`;
    };
    // Solo categorías que tienen productos a la venta
    const used = new Set(state.products.map(p => p.category_id));
    el.chips.innerHTML = chip(null, "Todos")
        + state.categories.filter(c => used.has(c.id)).map(c => chip(c.id, c.name)).join("");
}

function renderGrid() {
    const products = visibleProducts();
    el.grid.innerHTML = products.map(p => `
        <li>
            <button type="button" class="product-tile" data-product="${p.id}">
                ${productAvatar(p, "avatar-tile")}
                <span class="tile-name">${escapeHtml(p.name)}</span>
                <span class="tile-price">${formatMoney(p.price)}${p.unit && p.unit !== "pieza" ? ` / ${escapeHtml(p.unit)}` : ""}</span>
            </button>
        </li>`).join("");

    el.gridEmpty.hidden = products.length > 0;
    el.gridEmpty.textContent = state.products.length === 0
        ? "No hay productos activos. Dalos de alta en Productos."
        : "Ningún producto coincide con la búsqueda.";
}

// ---------- Carrito ----------

function renderCart() {
    el.lines.innerHTML = cart.lines.map(line => {
        const p = line.product;
        const step = allowsFraction(p) ? "0.001" : "1";
        return `
            <li class="cart-line">
                <div class="line-info">
                    <span class="line-name">${escapeHtml(p.name)}</span>
                    <span class="line-unit">${formatMoney(p.price)} c/u</span>
                </div>
                <div class="qty-control">
                    <button type="button" class="qty-btn" data-dec="${p.id}" aria-label="Quitar uno de ${escapeHtml(p.name)}"><i class="fa-solid fa-minus" aria-hidden="true"></i></button>
                    <input class="qty-input" type="number" min="0" step="${step}" inputmode="decimal" value="${line.qty}" data-qty="${p.id}" aria-label="Cantidad de ${escapeHtml(p.name)}">
                    <button type="button" class="qty-btn" data-inc="${p.id}" aria-label="Agregar uno de ${escapeHtml(p.name)}"><i class="fa-solid fa-plus" aria-hidden="true"></i></button>
                </div>
                <span class="line-total">${formatMoney(lineCents(line) / 100)}</span>
                <button type="button" class="icon-btn line-remove" data-remove="${p.id}" aria-label="Eliminar ${escapeHtml(p.name)}"><i class="fa-solid fa-trash-can" aria-hidden="true"></i></button>
            </li>`;
    }).join("");

    const count = cart.itemCount;
    el.cartEmpty.hidden = !cart.isEmpty;
    el.count.textContent = `${count} artículo${count === 1 ? "" : "s"}`;
    el.total.textContent = formatMoney(cart.total);
    el.charge.textContent = cart.isEmpty ? "Cobrar" : `Cobrar ${formatMoney(cart.total)}`;
    el.charge.disabled = cart.isEmpty || !cashierId || !cashOpen;
    el.clear.disabled = cart.isEmpty;
}

/** @param {number} id */
const findProduct = id => state.products.find(p => p.id === id);

/**
 * Enter en el buscador: un código de barras exacto (lector) o un único
 * resultado se agregan directo al carrito.
 */
function addFromSearch() {
    const query = el.search.value.trim();
    if (!query) return;

    const byBarcode = state.products.find(p => p.barcode === query);
    const matches = visibleProducts();
    const product = byBarcode ?? (matches.length === 1 ? matches[0] : null);

    if (product) {
        cart.add(product);
        el.search.value = "";
        renderGrid();
    } else {
        showToast(matches.length ? "Hay varios resultados, elige uno" : `No se encontró «${query}»`);
    }
}

// ---------- Carga inicial ----------

/** @param {unknown} err @param {string} fallback */
function reportError(err, fallback) {
    if (!(err instanceof ApiError)) console.error(err);
    showToast(err instanceof ApiError ? err.message : fallback);
}

async function loadCatalog() {
    el.grid.setAttribute("aria-busy", "true");
    try {
        const [categories, products] = await Promise.all([getCategories(), getProducts()]);
        state.categories = categories;
        state.products = products
            .filter(p => p.is_active)
            .sort((a, b) => a.name.localeCompare(b.name, "es"));
        renderChips();
        renderGrid();
    } catch (err) {
        reportError(err, "No se pudo cargar el catálogo");
    } finally {
        el.grid.setAttribute("aria-busy", "false");
    }
}

/** La venta queda a nombre de quien inició sesión. */
async function loadCashier() {
    try {
        const user = await getSession();
        cashierId = user.id;
        el.cashier.textContent = user.username;
    } catch (err) {
        reportError(err, "No se pudo consultar la sesión");
    }
    renderCart();
}

/** Carga los clientes para la opción de fiado; si falla, lo demás se puede cobrar igual. */
async function loadCustomers() {
    try {
        payment.setCustomers(await getCustomers());
    } catch (err) {
        reportError(err, "No se pudieron cargar los clientes");
    }
}

/** Consulta si la caja está abierta y avisa si hace falta abrirla. */
async function loadCashState() {
    try {
        cashOpen = (await getCurrentCash()).session !== null;
        el.cashNotice.hidden = cashOpen;
    } catch (err) {
        reportError(err, "No se pudo consultar la caja");
    }
    renderCart();
}

// ---------- Eventos ----------

const payment = setupPaymentDialog({
    onConfirm: async choice => {
        const sale = await checkout(cart, cashierId, choice);
        const change = sale.payments[0]?.change;
        // Se guarda la última venta y los nombres, porque el carrito se vacía enseguida
        lastSale = sale;
        el.printLast.hidden = false;
        cart.clear();
        // Si fue a fiado, la deuda del cliente cambió: se recarga su crédito disponible
        if (choice.customerId) loadCustomers();
        showToast(`Venta ${sale.folio} registrada${change ? ` · Cambio ${formatMoney(change)}` : ""}`);
        el.search.focus();
    },
});

el.search.addEventListener("input", renderGrid);
el.search.addEventListener("keydown", e => {
    if (e.key === "Enter") {
        e.preventDefault();
        addFromSearch();
    }
});

el.chips.addEventListener("click", e => {
    const chip = /** @type {HTMLElement} */ (e.target).closest("[data-category]");
    if (!chip) return;
    state.categoryId = Number(/** @type {HTMLElement} */ (chip).dataset.category) || null;
    renderChips();
    renderGrid();
});

el.grid.addEventListener("click", e => {
    const tile = /** @type {HTMLElement} */ (e.target).closest("[data-product]");
    const product = tile && findProduct(Number(/** @type {HTMLElement} */ (tile).dataset.product));
    if (product) cart.add(product);
});

el.lines.addEventListener("click", e => {
    const target = /** @type {HTMLElement} */ (e.target).closest("button");
    if (!target) return;
    const { inc, dec, remove } = target.dataset;
    if (inc) cart.add(/** @type {Product} */ (findProduct(Number(inc))), 1);
    if (dec) cart.add(/** @type {Product} */ (findProduct(Number(dec))), -1);
    if (remove) cart.remove(Number(remove));
});

el.lines.addEventListener("change", e => {
    const input = /** @type {HTMLInputElement} */ (e.target);
    if (input.dataset.qty) cart.setQty(Number(input.dataset.qty), parseFloat(input.value) || 0);
});

// Imprime el ticket de la última venta con los nombres del catálogo ya cargado
el.printLast.addEventListener("click", () => {
    if (!lastSale) return;
    printTicket(lastSale, new Map(state.products.map(p => [p.id, p.name])), el.cashier.textContent ?? "");
});

el.clear.addEventListener("click", () => cart.clear());
el.charge.addEventListener("click", () => payment.open(cart.total));

// Atajos: "/" enfoca el buscador; F12 cobra
document.addEventListener("keydown", e => {
    const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement;
    if (e.key === "/" && !typing) {
        e.preventDefault();
        el.search.focus();
    } else if (e.key === "F12" && !el.charge.disabled) {
        e.preventDefault();
        el.charge.click();
    }
});

// El carrito vive en memoria: avisa antes de perder una venta en curso al
// cambiar de pantalla desde el menú
window.addEventListener("beforeunload", e => {
    if (!cart.isEmpty) e.preventDefault();
});

cart.subscribe(renderCart);
enableImageFallback(el.grid);
renderSidebar("index.html");
loadCatalog();
loadCashier();
loadCashState();
loadCustomers();
el.search.focus();
