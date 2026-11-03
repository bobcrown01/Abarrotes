/**
 * Página de Inventario: existencias por producto y historial de movimientos.
 *
 * ``GET /inventory`` solo trae productos que ya tienen fila de existencias. Se
 * combina con el catálogo para que también aparezcan los que aún no llevan
 * control y se les pueda registrar su primera entrada.
 */

import { getCategories, getMovements, getProducts, getStock, getUsers } from "../lib/api.js";
import { escapeHtml, formatDateTime, formatQuantity } from "../lib/format.js";
import { setupPager } from "../lib/pager.js";
import { enableImageFallback, productAvatar } from "../lib/product-image.js";
import { renderSidebar } from "../lib/sidebar.js";
import { reportError, showToast } from "../lib/toast.js";
import { setupMinStockDialog } from "./min-stock-dialog.js";
import { setupMovementDialog } from "./movement-dialog.js";

renderSidebar("inventario.html");

/** @typedef {import("../lib/api.js").Product} Product */
/** @typedef {import("../lib/api.js").Stock} Stock */
/** @typedef {import("../lib/api.js").Movement} Movement */
/** @typedef {"ok"|"bajo"|"agotado"|"sin_control"} StockLevel */

const STOCK_PAGE_SIZE = 200; // Máximo que acepta GET /inventory
const MOVEMENTS_PAGE_SIZE = 50;

/** @type {Record<StockLevel, {css: string, label: string}>} */
const LEVEL_BADGES = {
    ok: { css: "badge-success", label: "Disponible" },
    bajo: { css: "badge-warning", label: "Por surtir" },
    agotado: { css: "badge-danger", label: "Agotado" },
    sin_control: { css: "badge-muted", label: "Sin control" },
};

const MOVEMENT_LABELS = { entrada: "Entrada", salida: "Salida", ajuste: "Conteo" };

/** @type {{ products: Product[], stock: Map<number, Stock>, userNames: Map<number, string>, movementsLoaded: boolean }} */
const state = { products: [], stock: new Map(), userNames: new Map(), movementsLoaded: false };

const el = {
    summary: /** @type {HTMLElement} */ (document.getElementById("stockSummary")),
    viewStock: /** @type {HTMLElement} */ (document.getElementById("viewStock")),
    viewMovements: /** @type {HTMLElement} */ (document.getElementById("viewMovements")),
    stockPanel: /** @type {HTMLElement} */ (document.getElementById("stockPanel")),
    movementsPanel: /** @type {HTMLElement} */ (document.getElementById("movementsPanel")),
    search: /** @type {HTMLInputElement} */ (document.getElementById("stockSearch")),
    category: /** @type {HTMLSelectElement} */ (document.getElementById("stockCategory")),
    level: /** @type {HTMLSelectElement} */ (document.getElementById("stockLevel")),
    stockTable: /** @type {HTMLElement} */ (document.getElementById("stockTable")),
    stockRows: /** @type {HTMLElement} */ (document.getElementById("stockRows")),
    stockEmpty: /** @type {HTMLElement} */ (document.getElementById("stockEmpty")),
    movementType: /** @type {HTMLSelectElement} */ (document.getElementById("movementType")),
    movementsTable: /** @type {HTMLElement} */ (document.getElementById("movementsTable")),
    movementRows: /** @type {HTMLElement} */ (document.getElementById("movementRows")),
    movementsEmpty: /** @type {HTMLElement} */ (document.getElementById("movementsEmpty")),
    movementsPager: /** @type {HTMLElement} */ (document.getElementById("movementsPager")),
};

// ---------- Existencias ----------

/**
 * @param {Stock|undefined} stock
 * @returns {StockLevel}
 */
function stockLevel(stock) {
    if (!stock) return "sin_control";
    if (stock.quantity <= 0) return "agotado";
    return stock.quantity <= stock.min_stock ? "bajo" : "ok";
}

/** @returns {Product[]} */
function visibleProducts() {
    const query = el.search.value.trim().toLowerCase();
    const categoryId = Number(el.category.value) || null;
    const level = el.level.value;

    return state.products.filter(p => {
        if (categoryId && p.category_id !== categoryId) return false;
        if (level && stockLevel(state.stock.get(p.id)) !== level) return false;
        return !query || [p.name, p.barcode, p.sku].some(v => (v ?? "").toLowerCase().includes(query));
    });
}

/**
 * @param {Product} p
 * @returns {string}
 */
function stockRow(p) {
    const stock = state.stock.get(p.id);
    const badge = LEVEL_BADGES[stockLevel(stock)];
    return `
        <tr>
            <td>
                <div class="product-cell">
                    ${productAvatar(p, "avatar-sm")}
                    <div>
                        <div class="product-title">${escapeHtml(p.name)}</div>
                        <div class="product-unit">${escapeHtml(p.unit ?? "pieza")}</div>
                    </div>
                </div>
            </td>
            <td class="num"><strong>${stock ? formatQuantity(stock.quantity) : "—"}</strong></td>
            <td class="num muted">${stock ? formatQuantity(stock.min_stock) : "—"}</td>
            <td><span class="badge ${badge.css}">${badge.label}</span></td>
            <td class="actions">
                <button type="button" class="btn btn-ghost btn-small manager-only" data-min="${p.id}" aria-label="Definir mínimo de ${escapeHtml(p.name)}">Mínimo</button>
                <button type="button" class="btn btn-ghost btn-small manager-only" data-move="${p.id}" aria-label="Registrar movimiento de ${escapeHtml(p.name)}">Movimiento</button>
            </td>
        </tr>`;
}

function renderStock() {
    const products = visibleProducts();
    el.stockRows.innerHTML = products.map(stockRow).join("");
    el.stockEmpty.hidden = products.length > 0;
    el.stockEmpty.querySelector("p").textContent = state.products.length === 0
        ? "No hay productos activos. Dalos de alta en Productos."
        : "Ningún producto coincide con los filtros.";

    const levels = state.products.map(p => stockLevel(state.stock.get(p.id)));
    const low = levels.filter(l => l === "bajo").length;
    const out = levels.filter(l => l === "agotado").length;
    el.summary.textContent = `${state.products.length} productos · ${low} por surtir · ${out} agotados`;
}

/**
 * Trae todas las existencias (la API las entrega por páginas).
 * @returns {Promise<Stock[]>}
 */
async function fetchAllStock() {
    const all = [];
    for (let offset = 0; ; offset += STOCK_PAGE_SIZE) {
        const page = await getStock({ limit: STOCK_PAGE_SIZE, offset });
        all.push(...page);
        if (page.length < STOCK_PAGE_SIZE) return all;
    }
}

async function loadStock() {
    el.stockTable.setAttribute("aria-busy", "true");
    try {
        const [products, stock] = await Promise.all([getProducts(), fetchAllStock()]);
        state.products = products
            .filter(p => p.is_active)
            .sort((a, b) => a.name.localeCompare(b.name, "es"));
        state.stock = new Map(stock.map(s => [s.product_id, s]));
        renderStock();
    } catch (err) {
        el.summary.textContent = "No se pudo cargar el inventario";
        reportError(err, "Error inesperado al cargar el inventario");
    } finally {
        el.stockTable.setAttribute("aria-busy", "false");
    }
}

// ---------- Movimientos ----------

/**
 * @param {Movement} m
 * @returns {string}
 */
function movementRow(m) {
    return `
        <tr>
            <td class="muted">${formatDateTime(m.created_at)}</td>
            <td>${escapeHtml(m.product_name)}</td>
            <td>${escapeHtml(MOVEMENT_LABELS[m.type] ?? m.type)}</td>
            <td class="num"><strong>${formatQuantity(m.quantity)}</strong></td>
            <td class="muted">${escapeHtml(m.reason ?? "—")}</td>
            <td class="muted">${escapeHtml(state.userNames.get(m.user_id) ?? "—")}</td>
        </tr>`;
}

const movementsPager = setupPager({
    container: el.movementsPager,
    limit: MOVEMENTS_PAGE_SIZE,
    fetchPage: page => getMovements({
        ...page,
        type: /** @type {import("../lib/api.js").MovementType|undefined} */ (el.movementType.value || undefined),
    }),
    onPage: movements => {
        el.movementRows.innerHTML = movements.map(movementRow).join("");
        el.movementsEmpty.hidden = movements.length > 0;
        el.movementsEmpty.querySelector("p").textContent = el.movementType.value
            ? "No hay movimientos de este tipo."
            : "Todavía no hay movimientos de inventario.";
    },
});

/** @param {number} [page] Página a cargar; por omisión la actual. */
async function loadMovements(page) {
    el.movementsTable.setAttribute("aria-busy", "true");
    try {
        await movementsPager.load(page);
        state.movementsLoaded = true;
    } catch (err) {
        reportError(err, "No se pudieron cargar los movimientos");
    } finally {
        el.movementsTable.setAttribute("aria-busy", "false");
    }
}

/** @param {boolean} showMovements */
function switchView(showMovements) {
    el.viewStock.setAttribute("aria-pressed", String(!showMovements));
    el.viewMovements.setAttribute("aria-pressed", String(showMovements));
    el.stockPanel.hidden = showMovements;
    el.movementsPanel.hidden = !showMovements;
    // El historial se pide hasta que se necesita: menos carga para la Raspberry
    if (showMovements && !state.movementsLoaded) loadMovements();
}

// ---------- Eventos ----------

const movementDialog = setupMovementDialog({
    onSaved: message => {
        showToast(message);
        loadStock();
        state.movementsLoaded = false;
    },
});

// Al guardar un mínimo se recargan las existencias para recalcular "Por surtir"
const minStockDialog = setupMinStockDialog({
    onSaved: message => {
        showToast(message);
        loadStock();
    },
});

el.search.addEventListener("input", renderStock);
el.category.addEventListener("change", renderStock);
el.level.addEventListener("change", renderStock);
el.viewStock.addEventListener("click", () => switchView(false));
el.viewMovements.addEventListener("click", () => switchView(true));
el.movementType.addEventListener("change", () => loadMovements(0));

el.movementsPager.addEventListener("pagererror", event => {
    reportError(/** @type {CustomEvent} */ (event).detail, "No se pudieron cargar los movimientos");
});

// Cada renglón tiene dos acciones: registrar un movimiento o definir el mínimo
el.stockRows.addEventListener("click", event => {
    const target = /** @type {HTMLElement} */ (event.target);
    const moveButton = /** @type {HTMLElement|null} */ (target.closest("[data-move]"));
    const minButton = /** @type {HTMLElement|null} */ (target.closest("[data-min]"));
    const id = Number(moveButton?.dataset.move ?? minButton?.dataset.min);
    const product = state.products.find(p => p.id === id);
    if (!product) return;
    if (moveButton) movementDialog.open(product, state.stock.get(id)?.quantity ?? null);
    else minStockDialog.open(product, state.stock.get(id));
});

enableImageFallback(el.stockRows);

// ---------- Carga inicial ----------

/** Filtros y nombres son secundarios: si fallan, las existencias igual se muestran. */
async function loadSecondary() {
    const [categories, users] = await Promise.allSettled([getCategories(), getUsers()]);
    if (categories.status === "fulfilled") {
        el.category.insertAdjacentHTML(
            "beforeend",
            categories.value.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join(""),
        );
    }
    if (users.status === "fulfilled") {
        state.userNames = new Map(users.value.map(u => [u.id, u.username]));
    }
}

loadSecondary();
loadStock();
