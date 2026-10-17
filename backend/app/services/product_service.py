"""Reglas de negocio del catálogo de productos."""

import logging
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError, ConflictError
from app.models.products import Category, Product
from app.schemas.product import ProductCreate

logger = logging.getLogger(__name__)


class CategoryNotFoundError(AppError):
    """La categoría indicada no existe."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("La categoría no existe")


class DuplicateBarcodeError(ConflictError):
    """Ya hay un producto con el mismo código de barras."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Ya existe un producto con ese código de barras")


class CategoryStore(Protocol):
    """Lo que el servicio necesita del repositorio de categorías."""

    def list_all(self) -> Sequence[Category]:
        """Regresa todas las categorías ordenadas por nombre."""
        ...

    def exists(self, category_id: int) -> bool:
        """Indica si existe una categoría con ese id."""
        ...


class ProductStore(Protocol):
    """Lo que el servicio necesita del repositorio de productos."""

    def list_all(self) -> Sequence[Product]:
        """Regresa todos los productos, los más recientes primero."""
        ...

    def search(self, query: str, limit: int, offset: int) -> Sequence[Product]:
        """Busca por coincidencia parcial en nombre, código de barras o SKU."""
        ...

    def barcode_exists(self, barcode: str) -> bool:
        """Indica si algún producto ya usa ese código de barras."""
        ...

    def add(self, product: Product) -> Product:
        """Guarda un producto nuevo y lo regresa con su id."""
        ...


class ProductService:
    """Casos de uso del catálogo: listar, buscar y dar de alta productos."""

    def __init__(self, products: ProductStore, categories: CategoryStore) -> None:
        """Crea el servicio.

        Args:
            products: Repositorio de productos.
            categories: Repositorio de categorías.
        """
        self._products = products
        self._categories = categories

    def list_categories(self) -> Sequence[Category]:
        """Regresa todas las categorías."""
        return self._categories.list_all()

    def list_products(self) -> Sequence[Product]:
        """Regresa todos los productos."""
        return self._products.list_all()

    def search_products(self, query: str, limit: int, offset: int) -> Sequence[Product]:
        """Busca productos por nombre, código de barras o SKU.

        Args:
            query: Texto a buscar.
            limit: Máximo de resultados.
            offset: Resultados a saltar.
        """
        return self._products.search(query, limit, offset)

    def create_product(self, data: ProductCreate) -> Product:
        """Da de alta un producto validando las reglas del catálogo.

        Args:
            data: Datos ya validados por Pydantic.

        Returns:
            El producto guardado, con su id.

        Raises:
            CategoryNotFoundError: Si la categoría no existe.
            DuplicateBarcodeError: Si el código de barras ya está en uso.
        """
        if not self._categories.exists(data.category_id):
            raise CategoryNotFoundError()

        if data.barcode and self._products.barcode_exists(data.barcode):
            raise DuplicateBarcodeError()

        try:
            product = self._products.add(Product(**data.model_dump()))
        except IntegrityError as exc:
            # Dos altas simultáneas pueden pasar la validación de arriba; el
            # índice único de la base es la defensa final.
            logger.warning("Alta de producto rechazada por la base: %s", exc.orig)
            raise DuplicateBarcodeError() from exc

        logger.info("Producto creado id=%s barcode=%s", product.id, product.barcode)
        return product
