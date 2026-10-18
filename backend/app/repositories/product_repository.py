"""Acceso a datos de productos y categorías.

Esta es la única capa que conoce SQLAlchemy; los servicios trabajan con estos
repositorios y así se pueden probar con implementaciones falsas.
"""

from collections.abc import Sequence

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.products import Category, Product
from app.schemas.product import ProductFilters


def _escape_like(text: str) -> str:
    """Escapa los comodines de ``LIKE`` para buscar el texto literal.

    Args:
        text: Texto escrito por el usuario.

    Returns:
        Texto con la barra invertida, ``%`` y ``_`` escapados.
    """
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _matches_text(query: str) -> ColumnElement[bool]:
    """Condición de coincidencia parcial en nombre, código de barras o SKU.

    Args:
        query: Texto escrito por el usuario.
    """
    pattern = f"%{_escape_like(query)}%"
    return or_(
        Product.name.ilike(pattern, escape="\\"),
        Product.barcode.ilike(pattern, escape="\\"),
        Product.sku.ilike(pattern, escape="\\"),
    )


class CategoryRepository:
    """Consultas sobre la tabla ``categories``."""

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def list_all(self) -> Sequence[Category]:
        """Regresa todas las categorías ordenadas por nombre."""
        return self._db.scalars(select(Category).order_by(Category.name)).all()

    def exists(self, category_id: int) -> bool:
        """Indica si existe una categoría con ese id.

        Args:
            category_id: Id de la categoría.
        """
        return self._db.get(Category, category_id) is not None


class ProductRepository:
    """Consultas y escrituras sobre la tabla ``products``."""

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def list_all(self) -> Sequence[Product]:
        """Regresa todos los productos, los más recientes primero."""
        return self._db.scalars(select(Product).order_by(Product.id.desc())).all()

    def search(self, query: str, limit: int, offset: int) -> Sequence[Product]:
        """Busca por coincidencia parcial en nombre, código de barras o SKU.

        Args:
            query: Texto a buscar.
            limit: Máximo de resultados.
            offset: Resultados a saltar (paginación).
        """
        statement = (
            select(Product)
            .where(_matches_text(query))
            .order_by(Product.name)
            .limit(limit)
            .offset(offset)
        )
        return self._db.scalars(statement).all()

    def filter(self, filters: ProductFilters) -> Sequence[Product]:
        """Busca productos combinando los filtros indicados (AND).

        Args:
            filters: Filtros validados; los que valen ``None`` no se aplican.
        """
        statement = select(Product)

        if filters.search:
            statement = statement.where(_matches_text(filters.search))
        if filters.category_id is not None:
            statement = statement.where(Product.category_id == filters.category_id)
        if filters.active is not None:
            statement = statement.where(Product.is_active == filters.active)
        if filters.min_price is not None:
            statement = statement.where(Product.price >= filters.min_price)
        if filters.max_price is not None:
            statement = statement.where(Product.price <= filters.max_price)
        if filters.in_stock is not None:
            # Solo productos con fila de inventario: los que no llevan control
            # de existencias no cuentan como "con" ni "sin" stock
            statement = statement.join(Inventory, Inventory.product_id == Product.id)
            in_stock = Inventory.quantity > 0
            statement = statement.where(in_stock if filters.in_stock else ~in_stock)

        statement = statement.order_by(Product.name).limit(filters.limit).offset(filters.offset)
        return self._db.scalars(statement).all()

    def get(self, product_id: int) -> Product | None:
        """Busca un producto por id.

        Args:
            product_id: Id del producto.
        """
        return self._db.get(Product, product_id)

    def barcode_exists(self, barcode: str, exclude_id: int | None = None) -> bool:
        """Indica si algún producto ya usa ese código de barras.

        Args:
            barcode: Código de barras a revisar.
            exclude_id: Producto que no cuenta (el que se está editando).
        """
        statement = select(Product.id).where(Product.barcode == barcode)
        if exclude_id is not None:
            statement = statement.where(Product.id != exclude_id)
        return self._db.scalar(statement.limit(1)) is not None

    def add(self, product: Product) -> Product:
        """Guarda un producto nuevo y confirma la transacción.

        Args:
            product: Producto sin id.

        Returns:
            El mismo producto con su id asignado.

        Raises:
            sqlalchemy.exc.IntegrityError: Si la base rechaza el registro
                (p. ej. código de barras duplicado por una alta simultánea).
        """
        self._db.add(product)
        return self.save(product)

    def save(self, product: Product) -> Product:
        """Confirma los cambios de un producto y lo recarga de la base.

        Args:
            product: Producto nuevo o modificado.

        Returns:
            El mismo producto con los valores guardados.

        Raises:
            sqlalchemy.exc.IntegrityError: Si la base rechaza los cambios.
        """
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise
        self._db.refresh(product)
        return product
