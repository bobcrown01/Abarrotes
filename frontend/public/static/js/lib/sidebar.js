/** Menú lateral compartido por todas las páginas (un solo lugar para editarlo). */

const NAV_ITEMS = [
    { href: "index.html", icon: "fa-cash-register", label: "Vender" },
    { href: "#", icon: "fa-house", label: "Inicio" },
    { href: "productos.html", icon: "fa-box", label: "Productos" },
    { href: "#", icon: "fa-users", label: "Clientes" },
    { href: "#", icon: "fa-gear", label: "Configuración" },
];

/**
 * Pinta el menú dentro de ``<aside id="appSidebar">``.
 * @param {string} activeHref Página actual, p. ej. "index.html".
 */
export function renderSidebar(activeHref) {
    const sidebar = document.getElementById("appSidebar");
    if (!sidebar) return;

    const links = NAV_ITEMS.map(({ href, icon, label }) => {
        const current = href === activeHref ? ' aria-current="page"' : "";
        return `<a class="nav-item" href="${href}" aria-label="${label}"${current}>`
            + `<i class="fa-solid ${icon}" aria-hidden="true"></i><span>${label}</span></a>`;
    }).join("");

    sidebar.innerHTML = `
        <div class="brand">
            <span class="brand-logo" aria-hidden="true"><i class="fa-solid fa-store"></i></span>
            <span class="brand-name">Abarrotes</span>
        </div>
        <nav aria-label="Menú principal">${links}</nav>`;
}
