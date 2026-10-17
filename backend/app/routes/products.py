"""Endpoints HTTP del catálogo de productos y categorías.

Los handlers solo traducen HTTP ↔ servicio; la lógica vive en
:mod:`app.services.product_service`.
"""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.models.products import Category, Product
from app.routes.dependencies import ProductServiceDep
from app.schemas.product import CategoryOut, ProductCreate, ProductOut

router = APIRouter(tags=["productos"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(service: ProductServiceDep) -> Sequence[Category]:
    """Lista las categorías ordenadas por nombre."""
    return service.list_categories()


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, service: ProductServiceDep) -> Product:
    """Da de alta un producto.

    Responde 400 si la categoría no existe y 409 si el código de barras ya
    está registrado.
    """
    return service.create_product(data)


@router.get("/products", response_model=list[ProductOut])
def list_products(service: ProductServiceDep) -> Sequence[Product]:
    """Lista todos los productos, los más recientes primero."""
    return service.list_products()


@router.get("/products/search", response_model=list[ProductOut])
def search_products(
    service: ProductServiceDep,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Product]:
    """Busca productos por nombre, código de barras o SKU (coincidencia parcial)."""
    return service.search_products(q, limit, offset)
