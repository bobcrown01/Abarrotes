/** Pantalla de venta: catálogo, carrito y cobro. */

import { ApiError, getCategories, getProducts, getUsers } from "../lib/api.js";
import { escapeHtml, formatMoney } from "../lib/format.js";
import { enableImageFallback, productAvatar } from "../lib/product-image.js";
import { renderSidebar } from "../lib/sidebar.js";
import { showToast } from "../lib/toast.js";
import { allowsFraction, Cart, lineCents } from "./cart.js";
import { checkout } from "./checkout.js";
import { setupPaymentDialog } from "./payment-dialog.js";

/** @typedef {import("../lib/api.js").Product} Product */
/** @typedef {import("../lib/api.js").Category} Category */

const CASHIER_KEY = "pos.cashierId";

/** @type {{ products: Product[], categories: Category[], categoryId: number|null }} */
const state = { products: [], categories: [], categoryId: null };
const cart = new Cart();

const el = {
    search: /** @type {HTMLInputElement} */ (document.getElementById("posSearch")),
    chips: /** @type {HTMLElement} */ (document.getElementById("categoryChips")),
    grid: /** @type {HTMLElement} */ (document.getElementById("productGrid")),
    gridEmpty: /** @type {HTMLElement} */ (document.getElementById("gridEmpty")),
    cashier: /** @type {HTMLSelectElement} */ (document.getElementById("cashierSelect")),
    lines: /** @type {HTMLElement} */ (document.getElementById("cartLines")),
    cartEmpty: /** @type {HTMLElement} */ (document.getElementById("cartEmpty")),
    count: /** @type {HTMLElement} */ (document.getElementById("cartCount")),
    total: /** @type {HTMLElement} */ (document.getElementById("cartTotal")),
    charge: /** @type {HTMLButtonElement} */ (document.getElementById("btnCharge")),
    clear: /** @type {HTMLButtonElement} */ (document.getElementById("btnClearCart")),
};

// ---------- Preferencias locales (solo comodidad; si fallan no pasa nada) ----------

function loadCashierId() {
    try {
        return Number(localStorage.getItem(CASHIER_KEY)) || null;
    } catch {
        return null;
    }
}

function saveCashierId(id) {
    try {
        localStorage.setItem(CASHIER_KEY, String(id));
    } catch {
        // Navegación privada o almacenamiento bloqueado: se vuelve a elegir
    }
}

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
    el.charge.disabled = cart.isEmpty || !el.cashier.value;
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

async function loadCashiers() {
    try {
        const users = (await getUsers()).filter(u => u.is_active);
        const placeholder = users.length ? "Elige cajero" : "No hay cajeros registrados";
        el.cashier.innerHTML = `<option value="">${placeholder}</option>`
            + users.map(u => `<option value="${u.id}">${escapeHtml(u.username)}</option>`).join("");

        const saved = loadCashierId();
        if (saved && users.some(u => u.id === saved)) el.cashier.value = String(saved);
        else if (users.length === 1) el.cashier.value = String(users[0].id);
    } catch (err) {
        reportError(err, "No se pudieron cargar los cajeros");
    }
    renderCart();
}

// ---------- Eventos ----------

const payment = setupPaymentDialog({
    onConfirm: async choice => {
        const sale = await checkout(cart, Number(el.cashier.value), choice);
        const change = sale.payments[0]?.change;
        cart.clear();
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

el.cashier.addEventListener("change", () => {
    if (el.cashier.value) saveCashierId(Number(el.cashier.value));
    renderCart();
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

cart.subscribe(renderCart);
enableImageFallback(el.grid);
renderSidebar("index.html");
loadCatalog();
loadCashiers();
el.search.focus();
