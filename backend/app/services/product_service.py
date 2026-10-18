"""Reglas de negocio del catálogo de productos."""

import logging
from collections.abc import Callable, Sequence
from typing import Protocol

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError, ConflictError
from app.models.products import Category, Product
from app.schemas.product import ProductCreate, ProductFilters, ProductUpdate
from app.services.errors import ProductNotFoundError

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

    def filter(self, filters: ProductFilters) -> Sequence[Product]:
        """Busca productos combinando filtros."""
        ...

    def get(self, product_id: int) -> Product | None:
        """Busca un producto por id."""
        ...

    def barcode_exists(self, barcode: str, exclude_id: int | None = None) -> bool:
        """Indica si algún otro producto ya usa ese código de barras."""
        ...

    def add(self, product: Product) -> Product:
        """Guarda un producto nuevo y lo regresa con su id."""
        ...

    def save(self, product: Product) -> Product:
        """Confirma los cambios de un producto existente."""
        ...


class ProductService:
    """Casos de uso del catálogo: consultar, dar de alta, editar y desactivar."""

    def __init__(self, products: ProductStore, categories: CategoryStore) -> None:
        """Crea el servicio.

        Args:
            products: Repositorio de productos.
            categories: Repositorio de categorías.
        """
        self._products = products
        self._categories = categories

    # ---------- Consultas ----------

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

    def filter_products(self, filters: ProductFilters) -> Sequence[Product]:
        """Busca productos por texto, categoría, estado, precio y existencias.

        Args:
            filters: Filtros validados.
        """
        return self._products.filter(filters)

    def get_product(self, product_id: int) -> Product:
        """Regresa un producto.

        Args:
            product_id: Id del producto.

        Raises:
            ProductNotFoundError: Si no existe.
        """
        product = self._products.get(product_id)
        if product is None:
            raise ProductNotFoundError()
        return product

    # ---------- Escrituras ----------

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
        self._check_category(data.category_id)
        self._check_barcode(data.barcode)

        product = self._persist(lambda: self._products.add(Product(**data.model_dump())))
        logger.info("Producto creado id=%s barcode=%s", product.id, product.barcode)
        return product

    def update_product(self, product_id: int, data: ProductUpdate) -> Product:
        """Aplica cambios parciales a un producto.

        Args:
            product_id: Id del producto.
            data: Solo los campos enviados en la petición se modifican.

        Raises:
            ProductNotFoundError: Si el producto no existe.
            CategoryNotFoundError: Si la nueva categoría no existe.
            DuplicateBarcodeError: Si el nuevo código ya lo usa otro producto.
        """
        product = self.get_product(product_id)
        changes = data.model_dump(exclude_unset=True)

        if "category_id" in changes:
            self._check_category(changes["category_id"])
        if "barcode" in changes:
            self._check_barcode(changes["barcode"], exclude_id=product_id)

        for field, value in changes.items():
            setattr(product, field, value)

        saved = self._persist(lambda: self._products.save(product))
        logger.info("Producto actualizado id=%s campos=%s", product_id, sorted(changes))
        return saved

    def deactivate_product(self, product_id: int) -> Product:
        """Desactiva un producto (no se borra: las ventas pasadas lo referencian).

        Args:
            product_id: Id del producto.

        Raises:
            ProductNotFoundError: Si el producto no existe.
        """
        product = self.get_product(product_id)
        product.is_active = False
        saved = self._products.save(product)
        logger.info("Producto desactivado id=%s", product_id)
        return saved

    # ---------- Apoyo ----------

    def _check_category(self, category_id: int) -> None:
        """Lanza :class:`CategoryNotFoundError` si la categoría no existe."""
        if not self._categories.exists(category_id):
            raise CategoryNotFoundError()

    def _check_barcode(self, barcode: str | None, exclude_id: int | None = None) -> None:
        """Lanza :class:`DuplicateBarcodeError` si otro producto ya usa el código."""
        if barcode and self._products.barcode_exists(barcode, exclude_id):
            raise DuplicateBarcodeError()

    @staticmethod
    def _persist(write: Callable[[], Product]) -> Product:
        """Ejecuta una escritura traduciendo el rechazo de la base a un error de dominio.

        Dos peticiones simultáneas pueden pasar la validación previa; el índice
        único de la base es la defensa final contra códigos duplicados.
        """
        try:
            return write()
        except IntegrityError as exc:
            logger.warning("Escritura de producto rechazada por la base: %s", exc.orig)
            raise DuplicateBarcodeError() from exc
