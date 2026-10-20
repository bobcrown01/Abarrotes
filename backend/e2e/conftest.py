"""Fixtures para pruebas end-to-end contra el stack levantado con Docker Compose.

Viven fuera de ``tests/`` para que ``pytest`` normal no las recolecte: requieren
navegador y la app corriendo (``docker compose up``).
"""

import os
from collections.abc import Iterator

import pytest
from playwright.sync_api import Page

# Desde el contenedor de Playwright, el frontend publicado en el host
# (127.0.0.1:8081) se alcanza por host.docker.internal.
DEFAULT_BASE_URL = "http://host.docker.internal:8081"


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("E2E_BASE_URL", DEFAULT_BASE_URL)


@pytest.fixture
def page_errors(page: Page) -> Iterator[list[str]]:
    """Acumula errores JS y respuestas 4xx/5xx de la API durante la prueba."""
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(f"JS: {exc}"))
    page.on(
        "response",
        lambda r: errors.append(f"HTTP {r.status} {r.url}")
        if "/api/" in r.url and r.status >= 400
        else None,
    )
    yield errors
