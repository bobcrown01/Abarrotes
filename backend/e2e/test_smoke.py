"""Smoke tests: cada pantalla carga, consulta la API y no lanza errores."""

import os
import re

from playwright.sync_api import Page, expect


def test_pantalla_venta_carga_catalogo(page: Page, page_errors: list[str]) -> None:
    page.goto("/")

    expect(page).to_have_title("Vender · Abarrotes POS")
    expect(page.locator("#productGrid")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_role("searchbox", name="Buscar o escanear producto")).to_be_visible()
    assert page_errors == []


def test_pantalla_productos_carga_tabla(page: Page, page_errors: list[str]) -> None:
    page.goto("/productos.html")

    expect(page.get_by_role("heading", level=1, name="Productos")).to_be_visible()
    expect(page.locator("#productTable")).to_have_attribute("aria-busy", "false")
    assert page_errors == []


def test_pantalla_ventas_carga_historial(page: Page, page_errors: list[str]) -> None:
    page.goto("/ventas.html")

    expect(page.get_by_role("heading", level=1, name="Ventas")).to_be_visible()
    expect(page.locator("#salesTable")).to_have_attribute("aria-busy", "false")
    assert page_errors == []


def test_pantalla_inventario_carga_existencias(page: Page, page_errors: list[str]) -> None:
    page.goto("/inventario.html")

    expect(page.get_by_role("heading", level=1, name="Inventario")).to_be_visible()
    expect(page.locator("#stockTable")).to_have_attribute("aria-busy", "false")
    page.get_by_role("button", name="Movimientos").click()
    expect(page.locator("#movementsTable")).to_have_attribute("aria-busy", "false")
    assert page_errors == []


def test_menu_navega_y_marca_la_pantalla_actual(page: Page, page_errors: list[str]) -> None:
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("/")

    menu = page.get_by_role("navigation", name="Menú principal")
    menu.get_by_role("link", name="Inventario").click()

    expect(page).to_have_url(re.compile(r"/inventario\.html$"))
    expect(menu.get_by_role("link", name="Inventario")).to_have_attribute("aria-current", "page")
    expect(page.locator(".nav-status")).to_have_text("En línea")
    assert page_errors == []


def test_menu_deshabilita_lo_que_no_tiene_pantalla(page: Page) -> None:
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("/")

    configuracion = page.get_by_role("link", name="Configuración, próximamente")
    expect(configuracion).to_have_attribute("aria-disabled", "true")
    assert configuracion.get_attribute("href") is None


def test_sin_sesion_manda_al_login_y_regresa(page: Page) -> None:
    page.context.clear_cookies()

    page.goto("/ventas.html")
    expect(page).to_have_url(re.compile(r"/login\.html\?next=ventas\.html$"))

    page.get_by_label("Usuario").fill(os.environ.get("E2E_USER", "e2e_admin"))
    page.get_by_label("Contraseña o PIN").fill(os.environ.get("E2E_PASSWORD", "e2e-clave-larga"))
    page.get_by_role("button", name="Entrar").click()

    expect(page).to_have_url(re.compile(r"/ventas\.html$"))


def test_cerrar_sesion_regresa_al_login(page: Page) -> None:
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("/ventas.html")

    page.get_by_role("button", name="Cerrar sesión").click()

    expect(page).to_have_url(re.compile(r"/login\.html$"))
    page.goto("/ventas.html")
    expect(page).to_have_url(re.compile(r"/login\.html"))


def test_f1_regresa_a_vender(page: Page) -> None:
    page.goto("/ventas.html")
    expect(page.locator("#salesTable")).to_have_attribute("aria-busy", "false")

    page.keyboard.press("F1")

    expect(page).to_have_title("Vender · Abarrotes POS")
