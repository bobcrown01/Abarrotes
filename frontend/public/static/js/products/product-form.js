/** Panel lateral con el formulario de alta de producto. */

/* El mismo panel sirve para editar: openEdit() lo abre con los datos del producto. */

import { ApiError, createProduct, updateProduct } from "../lib/api.js";
import { escapeHtml, formatMoney } from "../lib/format.js";

/** @typedef {import("../lib/api.js").Category} Category */
/** @typedef {import("../lib/api.js").ProductCreate} ProductCreate */

/**
 * Conecta el formulario con la API.
 * @param {Object} options
 * @param {() => void} options.onCreated Se llama después de guardar con éxito.
 * @param {() => void} [options.onUpdated] Se llama después de guardar una edición.
 * @returns {{ open: () => void, setCategories: (categories: Category[]) => void }}
 *     También regresa ``openEdit(product)`` para editar un producto existente.
 */
export function setupProductForm({ onCreated, onUpdated }) {
    const drawer = /** @type {HTMLElement} */ (document.getElementById("productDrawer"));
    const overlay = /** @type {HTMLElement} */ (document.getElementById("drawerOverlay"));
    const form = /** @type {HTMLFormElement} */ (document.getElementById("productForm"));
    const errorBox = /** @type {HTMLElement} */ (document.getElementById("formError"));
    const marginHint = /** @type {HTMLElement} */ (document.getElementById("marginHint"));
    const saveButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnSave"));
    const title = /** @type {HTMLElement} */ (document.getElementById("drawerTitle"));
    const fields = /** @type {HTMLFormControlsCollection & Record<string, HTMLInputElement>} */ (
        form.elements
    );

    /** @type {HTMLElement|null} Elemento que abrió el panel, para devolverle el foco. */
    let opener = null;

    /** @type {number|null} Producto que se está editando; null si es un alta. */
    let editingId = null;

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
    }

    function clearErrors() {
        errorBox.hidden = true;
        form.querySelectorAll("[aria-invalid]").forEach(el => el.removeAttribute("aria-invalid"));
    }

    function open() {
        editingId = null;
        title.textContent = "Nuevo producto";
        form.reset();
        marginHint.textContent = "";
        show();
    }

    /**
     * Abre el panel con los datos actuales del producto para cambiarlos.
     * @param {import("../lib/api.js").Product} product
     */
    function openEdit(product) {
        editingId = product.id;
        title.textContent = "Editar producto";
        form.reset();
        fields.name.value = product.name;
        fields.category_id.value = String(product.category_id);
        fields.barcode.value = product.barcode ?? "";
        fields.sku.value = product.sku ?? "";
        fields.price.value = String(product.price);
        fields.cost.value = product.cost === null ? "" : String(product.cost);
        fields.unit.value = product.unit ?? "pieza";
        fields.is_active.checked = product.is_active;
        updateMargin();
        show();
    }

    /** Muestra el panel, ya sea para un alta o para una edición. */
    function show() {
        opener = /** @type {HTMLElement|null} */ (document.activeElement);
        clearErrors();
        overlay.hidden = false;
        drawer.hidden = false;
        // Un frame para que la transición CSS arranque después de mostrarlo
        requestAnimationFrame(() => drawer.classList.add("open"));
        fields.name.focus();
    }

    function close() {
        drawer.classList.remove("open");
        overlay.hidden = true;
        drawer.hidden = true;
        opener?.focus();
    }

    function updateMargin() {
        const price = parseFloat(fields.price.value);
        const cost = parseFloat(fields.cost.value);
        if (price > 0 && cost >= 0) {
            const margin = ((price - cost) / price) * 100;
            marginHint.textContent =
                `Ganancia: ${formatMoney(price - cost)} (${margin.toFixed(1)}% de margen)`;
        } else {
            marginHint.textContent = "";
        }
    }

    /** @returns {ProductCreate} */
    function readForm() {
        const cost = fields.cost.value.trim();
        return {
            name: fields.name.value.trim(),
            category_id: Number(fields.category_id.value),
            barcode: fields.barcode.value.trim() || null,
            sku: fields.sku.value.trim() || null,
            price: parseFloat(fields.price.value),
            cost: cost === "" ? null : parseFloat(cost),
            unit: /** @type {ProductCreate["unit"]} */ (fields.unit.value),
            is_active: fields.is_active.checked,
        };
    }

    /**
     * Valida en el cliente lo mismo que valida el backend, para avisar antes.
     * @param {ProductCreate} data
     * @returns {HTMLElement[]} Campos inválidos.
     */
    function findInvalidFields(data) {
        // Se valida el texto tecleado: comparar floats falla con montos como 0.07
        const MONEY_PATTERN = /^\d{1,10}(\.\d{1,2})?$/;
        const invalid = [];
        if (!data.name) invalid.push(fields.name);
        if (!data.category_id) invalid.push(fields.category_id);
        if (!MONEY_PATTERN.test(fields.price.value.trim())) invalid.push(fields.price);
        if (data.cost !== null && !MONEY_PATTERN.test(fields.cost.value.trim())) {
            invalid.push(fields.cost);
        }
        return invalid;
    }

    async function submit(event) {
        event.preventDefault();
        clearErrors();

        const data = readForm();
        const invalid = findInvalidFields(data);
        if (invalid.length > 0) {
            invalid.forEach(el => el.setAttribute("aria-invalid", "true"));
            showError("Revisa los campos marcados en rojo.");
            invalid[0].focus();
            return;
        }

        saveButton.disabled = true;
        saveButton.textContent = "Guardando…";
        try {
            // Alta o edición, según con qué se abrió el panel
            if (editingId === null) {
                await createProduct(data);
                close();
                onCreated();
            } else {
                await updateProduct(editingId, data);
                close();
                onUpdated?.();
            }
        } catch (err) {
            showError(err instanceof ApiError ? err.message : "Error inesperado al guardar");
            if (!(err instanceof ApiError)) console.error(err);
        } finally {
            saveButton.disabled = false;
            saveButton.textContent = "Guardar producto";
        }
    }

    /** @param {Category[]} categories */
    function setCategories(categories) {
        fields.category_id.insertAdjacentHTML(
            "beforeend",
            categories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join(""),
        );
    }

    form.addEventListener("submit", submit);
    fields.price.addEventListener("input", updateMargin);
    fields.cost.addEventListener("input", updateMargin);
    document.getElementById("btnCloseDrawer")?.addEventListener("click", close);
    document.getElementById("btnCancel")?.addEventListener("click", close);
    overlay.addEventListener("click", close);
    document.addEventListener("keydown", e => {
        if (e.key === "Escape" && !drawer.hidden) close();
    });

    return { open, openEdit, setCategories };
}
