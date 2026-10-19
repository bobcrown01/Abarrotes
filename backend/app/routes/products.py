"""Endpoints HTTP del catálogo de productos y categorías.

Los handlers solo traducen HTTP ↔ servicio; la lógica vive en
:mod:`app.services.product_service`.

Importante: las rutas fijas (``/products/search``, ``/products/filter``) van
antes que ``/products/{product_id}``; FastAPI prueba las rutas en orden.
"""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.models.products import Category, Product
from app.routes.dependencies import ProductServiceDep
from app.schemas.product import (
    CategoryOut,
    ProductCreate,
    ProductFilters,
    ProductOut,
    ProductUpdate,
)

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


@router.get("/products/filter", response_model=list[ProductOut])
def filter_products(
    service: ProductServiceDep, filters: Annotated[ProductFilters, Query()]
) -> Sequence[Product]:
    """Filtra por texto, categoría, estado, rango de precio y existencias."""
    return service.filter_products(filters)


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, service: ProductServiceDep) -> Product:
    """Regresa un producto. Responde 404 si no existe."""
    return service.get_product(product_id)


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, service: ProductServiceDep) -> Product:
    """Actualiza solo los campos enviados.

    Responde 404 si el producto no existe, 400 si la categoría no existe y
    409 si el código de barras ya lo usa otro producto.
    """
    return service.update_product(product_id, data)


@router.post("/products/{product_id}/deactivate", response_model=ProductOut)
def deactivate_product(product_id: int, service: ProductServiceDep) -> Product:
    """Desactiva el producto (deja de venderse pero conserva su historial)."""
    return service.deactivate_product(product_id)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, service: ProductServiceDep) -> None:
    """Elimina un producto que nunca se ha usado.

    Responde 404 si no existe y 409 si tiene ventas o movimientos de
    inventario (en ese caso hay que desactivarlo).
    """
    service.delete_product(product_id)
