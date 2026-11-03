/** Menú lateral compartido por todas las páginas (un solo lugar para editarlo). */

/*
 * Sigue el orden de trabajo de un punto de venta: primero lo que se usa en
 * cada cobro, luego el catálogo y al final la administración. Una opción sin
 * ``href`` todavía no tiene pantalla y se muestra deshabilitada.
 */

import { checkHealth } from "./api.js";
import { escapeHtml } from "./format.js";
import { applyRole, getSession, signOut } from "./session.js";

const HEALTH_INTERVAL_MS = 30000;
const SELL_PAGE = "index.html";

/**
 * @typedef {Object} NavItem
 * @property {string} [href] Página de destino; sin ella queda deshabilitada.
 * @property {string} icon Clase de Font Awesome.
 * @property {string} label
 * @property {string} [shortcut] Tecla de acceso directo.
 * @property {boolean} [managerOnly] Solo se muestra a roles de administración.
 */

/** @type {{ title: string, items: NavItem[] }[]} */
const NAV_GROUPS = [
    {
        title: "Operación",
        items: [
            { href: SELL_PAGE, icon: "fa-cash-register", label: "Vender", shortcut: "F1" },
            { href: "ventas.html", icon: "fa-receipt", label: "Ventas" },
            // Va en Operación: el cajero abre y cierra caja en cada turno
            { href: "caja.html", icon: "fa-calculator", label: "Corte de caja" },
        ],
    },
    {
        title: "Catálogo",
        items: [
            { href: "productos.html", icon: "fa-box", label: "Productos" },
            { href: "inventario.html", icon: "fa-boxes-stacked", label: "Inventario" },
        ],
    },
    {
        title: "Administración",
        items: [
            { href: "clientes.html", icon: "fa-users", label: "Clientes" },
            // Solo para roles de administración: muestra ganancias y costos
            { href: "reportes.html", icon: "fa-chart-line", label: "Reportes", managerOnly: true },
            { icon: "fa-gear", label: "Configuración" },
        ],
    },
];

/**
 * @param {NavItem} item
 * @param {string} activeHref
 * @returns {string} HTML.
 */
function navItem({ href, icon, label, shortcut, managerOnly }, activeHref) {
    const iconHtml = `<i class="fa-solid ${icon}" aria-hidden="true"></i>`;
    const name = `<span class="nav-label">${escapeHtml(label)}</span>`;

    // Sin tabindex: una opción que no hace nada no debe recibir el foco
    if (!href) {
        return `<span class="nav-item nav-item-soon" role="link" aria-disabled="true" `
            + `aria-label="${escapeHtml(label)}, próximamente" title="Próximamente">`
            + `${iconHtml}${name}<small class="nav-soon" aria-hidden="true">Pronto</small></span>`;
    }

    const current = href === activeHref ? ' aria-current="page"' : "";
    const keys = shortcut ? ` aria-keyshortcuts="${shortcut}"` : "";
    const hint = shortcut ? `<kbd class="nav-kbd" aria-hidden="true">${shortcut}</kbd>` : "";
    const roleClass = managerOnly ? " manager-only" : "";
    return `<a class="nav-item${roleClass}" href="${href}"${current}${keys}>${iconHtml}${name}${hint}</a>`;
}

/**
 * Mantiene al día el indicador de conexión con el servidor y la base de datos.
 * @param {HTMLElement} status
 */
function watchConnection(status) {
    const label = /** @type {HTMLElement} */ (status.querySelector(".nav-status-label"));

    async function refresh() {
        const online = await checkHealth();
        status.classList.toggle("is-offline", !online);
        label.textContent = online ? "En línea" : "Sin conexión";
    }

    // En segundo plano no se consulta: ahorra trabajo a la Raspberry
    setInterval(() => {
        if (!document.hidden) refresh();
    }, HEALTH_INTERVAL_MS);
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) refresh();
    });
    window.addEventListener("online", refresh);
    window.addEventListener("offline", refresh);
    refresh();
}

/**
 * Pinta el menú dentro de ``<aside id="appSidebar">``.
 * @param {string} activeHref Página actual, p. ej. "index.html".
 */
export function renderSidebar(activeHref) {
    const sidebar = document.getElementById("appSidebar");
    if (!sidebar) return;

    const groups = NAV_GROUPS.map(({ title, items }) => `
        <div class="nav-group" role="group" aria-label="${escapeHtml(title)}">
            <p class="nav-group-title" aria-hidden="true">${escapeHtml(title)}</p>
            ${items.map(item => navItem(item, activeHref)).join("")}
        </div>`).join("");

    sidebar.innerHTML = `
        <div class="brand">
            <span class="brand-logo" aria-hidden="true"><i class="fa-solid fa-store"></i></span>
            <span class="brand-name">Abarrotes</span>
        </div>
        <nav class="nav-list" aria-label="Menú principal">${groups}
            <button type="button" class="nav-item nav-logout-phone" data-logout>
                <i class="fa-solid fa-right-from-bracket" aria-hidden="true"></i><span class="nav-label">Salir</span>
            </button>
        </nav>
        <div class="nav-user">
            <span class="nav-user-name" id="navUser"></span>
            <button type="button" class="icon-btn" data-logout aria-label="Cerrar sesión" title="Cerrar sesión">
                <i class="fa-solid fa-right-from-bracket" aria-hidden="true"></i>
            </button>
        </div>
        <div class="nav-status" role="status">
            <span class="nav-status-dot" aria-hidden="true"></span>
            <span class="nav-status-label">Conectando…</span>
        </div>`;

    watchConnection(/** @type {HTMLElement} */ (sidebar.querySelector(".nav-status")));

    // Muestra quién tiene la sesión y activa las opciones de su rol
    getSession().then(user => {
        applyRole(user);
        /** @type {HTMLElement} */ (sidebar.querySelector("#navUser")).textContent = user.username;
    }).catch(err => console.error("No se pudo consultar la sesión", err));

    // Cerrar sesión desde la barra del teléfono o desde el pie del menú
    sidebar.addEventListener("click", event => {
        if (/** @type {HTMLElement} */ (event.target).closest("[data-logout]")) signOut();
    });

    // F1 regresa a Vender desde cualquier pantalla, salvo con una ventana abierta
    document.addEventListener("keydown", event => {
        if (event.key !== "F1") return;
        event.preventDefault();
        if (activeHref !== SELL_PAGE && !document.querySelector("dialog[open]")) {
            window.location.href = SELL_PAGE;
        }
    });
}
