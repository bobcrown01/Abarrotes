"""Acceso a datos de productos y categorías.

Esta es la única capa que conoce SQLAlchemy; los servicios trabajan con estos
repositorios y así se pueden probar con implementaciones falsas.
"""

from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.products import Category, Product


def _escape_like(text: str) -> str:
    """Escapa los comodines de ``LIKE`` para buscar el texto literal.

    Args:
        text: Texto escrito por el usuario.

    Returns:
        Texto con la barra invertida, ``%`` y ``_`` escapados.
    """
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
        pattern = f"%{_escape_like(query)}%"
        statement = (
            select(Product)
            .where(
                or_(
                    Product.name.ilike(pattern, escape="\\"),
                    Product.barcode.ilike(pattern, escape="\\"),
                    Product.sku.ilike(pattern, escape="\\"),
                )
            )
            .order_by(Product.name)
            .limit(limit)
            .offset(offset)
        )
        return self._db.scalars(statement).all()

    def barcode_exists(self, barcode: str) -> bool:
        """Indica si algún producto ya usa ese código de barras.

        Args:
            barcode: Código de barras a revisar.
        """
        statement = select(Product.id).where(Product.barcode == barcode).limit(1)
        return self._db.scalar(statement) is not None

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
        try:
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise
        self._db.refresh(product)
        return product
