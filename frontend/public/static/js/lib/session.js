/** Sesión del usuario: quién está en la caja y qué puede hacer. */

import { ApiError, getMe, logout, redirectToLogin } from "./api.js";

/** @typedef {import("./api.js").CurrentUser} CurrentUser */

const HTTP_UNAUTHORIZED = 401;

/** @type {Promise<CurrentUser>|null} Se consulta una sola vez por pantalla. */
let current = null;

/**
 * Regresa el usuario de la sesión; sin sesión, manda al login.
 * @returns {Promise<CurrentUser>}
 */
export function getSession() {
    current ??= getMe().catch(err => {
        if (err instanceof ApiError && err.status === HTTP_UNAUTHORIZED) redirectToLogin();
        throw err;
    });
    return current;
}

/**
 * Muestra lo que solo puede usar un rol de administración (clase ``manager-only``).
 * Es solo comodidad visual: quien hace cumplir el permiso es el backend.
 * @param {CurrentUser} user
 */
export function applyRole(user) {
    document.documentElement.toggleAttribute("data-can-manage", user.can_manage);
}

/** Cierra la sesión y regresa al login, aunque el servidor no responda. */
export async function signOut() {
    await logout().catch(err => console.error("No se pudo cerrar la sesión en el servidor", err));
    window.location.href = "login.html";
}
