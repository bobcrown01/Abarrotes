/**
 * Pantalla de inicio de sesión. Si aún no existe ningún administrador, la misma
 * pantalla sirve para crear el primero.
 */

import { ApiError, getAuthStatus, getMe, login, setupAdmin } from "../lib/api.js";

/** Pantallas a las que se puede regresar: evita redirigir a otro sitio con ?next=. */
const ALLOWED_PAGES = new Set([
    "index.html",
    "ventas.html",
    "caja.html",
    "productos.html",
    "inventario.html",
    "clientes.html",
    "reportes.html",
]);
const MIN_ADMIN_PASSWORD = 8;

const form = /** @type {HTMLFormElement} */ (document.getElementById("loginForm"));
const title = /** @type {HTMLElement} */ (document.getElementById("loginTitle"));
const subtitle = /** @type {HTMLElement} */ (document.getElementById("loginSubtitle"));
const errorBox = /** @type {HTMLElement} */ (document.getElementById("loginError"));
const userInput = /** @type {HTMLInputElement} */ (document.getElementById("loginUser"));
const passwordInput = /** @type {HTMLInputElement} */ (document.getElementById("loginPassword"));
const passwordLabel = /** @type {HTMLElement} */ (document.getElementById("loginPasswordLabel"));
const submitButton = /** @type {HTMLButtonElement} */ (document.getElementById("btnLogin"));

let settingUp = false;

/** Regresa a la pantalla que se quería abrir, o a Vender. */
function goToApp() {
    const next = new URLSearchParams(window.location.search).get("next") ?? "";
    window.location.replace(ALLOWED_PAGES.has(next) ? next : "index.html");
}

/** @param {string} message */
function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
}

/** Cambia la pantalla al modo de crear el primer administrador. */
function showSetup() {
    settingUp = true;
    title.textContent = "Crea el administrador";
    subtitle.textContent = "Es la primera vez que se usa el sistema. Esta cuenta podrá crear a los cajeros.";
    passwordLabel.textContent = `Contraseña (mínimo ${MIN_ADMIN_PASSWORD} caracteres)`;
    passwordInput.autocomplete = "new-password";
    submitButton.textContent = "Crear y entrar";
}

/** @param {SubmitEvent} event */
async function submit(event) {
    event.preventDefault();
    errorBox.hidden = true;

    const username = userInput.value.trim();
    const password = passwordInput.value;
    if (!username || !password) {
        showError("Escribe tu usuario y tu contraseña.");
        return;
    }
    if (settingUp && password.length < MIN_ADMIN_PASSWORD) {
        showError(`La contraseña debe tener al menos ${MIN_ADMIN_PASSWORD} caracteres.`);
        return;
    }

    submitButton.disabled = true;
    try {
        await (settingUp ? setupAdmin(username, password) : login(username, password));
        goToApp();
    } catch (err) {
        if (!(err instanceof ApiError)) console.error(err);
        showError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión");
        // Se borra la clave para reintentar sin dejarla escrita en la caja
        passwordInput.value = "";
        passwordInput.focus();
    } finally {
        submitButton.disabled = false;
    }
}

/** Decide qué mostrar: si ya hay sesión entra directo; si no, login o configuración inicial. */
async function start() {
    form.addEventListener("submit", submit);
    userInput.focus();
    try {
        await getMe();
        goToApp();
        return;
    } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 401) console.error(err);
    }
    try {
        const { needs_setup: needsSetup } = await getAuthStatus();
        if (needsSetup) showSetup();
    } catch (err) {
        showError(err instanceof ApiError ? err.message : "Sin conexión con el servidor");
    }
}

start();
