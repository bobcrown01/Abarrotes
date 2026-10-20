"""Smoke tests: cada pantalla carga, consulta la API y no lanza errores."""

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
