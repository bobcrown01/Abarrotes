/**
 * Paginación "anterior / siguiente" para listas de la API, que no informa el
 * total de registros. Para saber si hay otra página se pide un registro de más.
 */

/**
 * @template T
 * @param {Object} options
 * @param {HTMLElement} options.container Elemento donde se pintan los botones.
 * @param {number} options.limit Registros por página.
 * @param {(page: {limit: number, offset: number}) => Promise<T[]>} options.fetchPage
 * @param {(rows: T[]) => void} options.onPage Recibe los registros de la página.
 * @returns {{ load: (page?: number) => Promise<void>, current: () => number }}
 *     ``load`` lanza el error de ``fetchPage`` para que lo muestre quien llama.
 */
export function setupPager({ container, limit, fetchPage, onPage }) {
    let page = 0;

    container.innerHTML = `
        <button type="button" class="btn btn-ghost" data-step="-1">Anterior</button>
        <span aria-live="polite"></span>
        <button type="button" class="btn btn-ghost" data-step="1">Siguiente</button>`;

    const previous = /** @type {HTMLButtonElement} */ (container.querySelector('[data-step="-1"]'));
    const next = /** @type {HTMLButtonElement} */ (container.querySelector('[data-step="1"]'));
    const label = /** @type {HTMLElement} */ (container.querySelector("span"));

    /** @param {number} [target] Página a cargar (desde 0); por omisión la actual. */
    async function load(target = page) {
        const rows = await fetchPage({ limit: limit + 1, offset: target * limit });
        page = target;
        previous.disabled = page === 0;
        next.disabled = rows.length <= limit;
        label.textContent = `Página ${page + 1}`;
        container.hidden = page === 0 && rows.length <= limit;
        onPage(rows.slice(0, limit));
    }

    container.addEventListener("click", event => {
        const button = /** @type {HTMLElement} */ (event.target).closest("[data-step]");
        if (!button) return;
        load(page + Number(/** @type {HTMLElement} */ (button).dataset.step)).catch(err => {
            container.dispatchEvent(new CustomEvent("pagererror", { detail: err }));
        });
    });

    return { load, current: () => page };
}
