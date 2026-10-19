/** Página de Productos: listado, filtros, alta y eliminación. */

import { ApiError, getCategories, getProducts } from "../lib/api.js";
import { escapeHtml, formatMoney } from "../lib/format.js";
import { enableImageFallback, productAvatar } from "../lib/product-image.js";
import { renderSidebar } from "../lib/sidebar.js";
import { showToast } from "../lib/toast.js";
import { setupDeleteDialog } from "./delete-dialog.js";
import { setupProductForm } from "./product-form.js";

renderSidebar("productos.html");

/** @typedef {import("../lib/api.js").Product} Product */
/** @typedef {import("../lib/api.js").Category} Category */

/** @type {{ products: Product[], categoryNames: Map<number, string> }} */
const state = { products: [], categoryNames: new Map() };

const rows = /** @type {HTMLElement} */ (document.getElementById("productRows"));
const emptyState = /** @type {HTMLElement} */ (document.getElementById("emptyState"));
const countLabel = /** @type {HTMLElement} */ (document.getElementById("productCount"));
const searchInput = /** @type {HTMLInputElement} */ (document.getElementById("searchInput"));
const categoryFilter = /** @type {HTMLSelectElement} */ (document.getElementById("categoryFilter"));
const table = /** @type {HTMLElement} */ (document.getElementById("productTable"));

/**
 * Aplica búsqueda y filtro de categoría (en el cliente: el catálogo ya está cargado).
 * @returns {Product[]}
 */
function visibleProducts() {
    const query = searchInput.value.trim().toLowerCase();
    const categoryId = Number(categoryFilter.value) || null;

    return state.products.filter(p => {
        if (categoryId && p.category_id !== categoryId) return false;
        return !query || [p.name, p.barcode, p.sku].some(v => (v ?? "").toLowerCase().includes(query));
    });
}

/**
 * @param {Product} p
 * @returns {string}
 */
function productRow(p) {
    const status = p.is_active
        ? '<span class="badge badge-success">Activo</span>'
        : '<span class="badge badge-muted">Inactivo</span>';

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
            <td>${escapeHtml(state.categoryNames.get(p.category_id) ?? "—")}</td>
            <td class="muted">${escapeHtml(p.barcode ?? "—")}</td>
            <td class="muted">${escapeHtml(p.sku ?? "—")}</td>
            <td class="num muted">${formatMoney(p.cost)}</td>
            <td class="num"><strong>${formatMoney(p.price)}</strong></td>
            <td>${status}</td>
            <td class="actions">
                <button type="button" class="icon-btn icon-btn-danger" data-delete="${p.id}" aria-label="Eliminar ${escapeHtml(p.name)}" title="Eliminar">
                    <i class="fa-solid fa-trash-can" aria-hidden="true"></i>
                </button>
            </td>
        </tr>`;
}

function render() {
    const products = visibleProducts();
    rows.innerHTML = products.map(productRow).join("");
    emptyState.hidden = products.length > 0;
    emptyState.querySelector("p").textContent = state.products.length === 0
        ? "Aún no hay productos. Crea el primero con «Nuevo producto»."
        : "Ningún producto coincide con la búsqueda.";

    const total = state.products.length;
    countLabel.textContent = `${total} producto${total === 1 ? "" : "s"}`;
}

/**
 * Muestra un error al usuario; los que no vienen de la API se registran en consola.
 * @param {unknown} err
 * @param {string} fallback Mensaje si el error no es de la API.
 */
function reportError(err, fallback) {
    if (!(err instanceof ApiError)) console.error(err);
    showToast(err instanceof ApiError ? err.message : fallback);
}

async function loadProducts() {
    table.setAttribute("aria-busy", "true");
    try {
        state.products = await getProducts();
        render();
    } catch (err) {
        countLabel.textContent = "No se pudieron cargar los productos";
        reportError(err, "Error inesperado al cargar productos");
    } finally {
        table.setAttribute("aria-busy", "false");
    }
}

/** @returns {Promise<Category[]>} */
async function loadCategories() {
    try {
        const categories = await getCategories();
        state.categoryNames = new Map(categories.map(c => [c.id, c.name]));
        categoryFilter.insertAdjacentHTML(
            "beforeend",
            categories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join(""),
        );
        return categories;
    } catch (err) {
        reportError(err, "No se pudieron cargar las categorías");
        return [];
    }
}

const form = setupProductForm({
    onCreated: () => {
        showToast("Producto creado correctamente");
        loadProducts();
    },
});

const deleteDialog = setupDeleteDialog({
    onDone: message => {
        showToast(message);
        loadProducts();
    },
});

document.getElementById("btnNewProduct")?.addEventListener("click", form.open);
searchInput.addEventListener("input", render);
categoryFilter.addEventListener("change", render);

rows.addEventListener("click", event => {
    const button = /** @type {HTMLElement} */ (event.target).closest("[data-delete]");
    if (!button) return;
    const product = state.products.find(
        p => p.id === Number(/** @type {HTMLElement} */ (button).dataset.delete),
    );
    if (product) deleteDialog.open(product);
});
enableImageFallback(rows);

// Primero categorías para poder mostrar su nombre en la tabla
loadCategories().then(categories => {
    form.setCategories(categories);
    return loadProducts();
});
