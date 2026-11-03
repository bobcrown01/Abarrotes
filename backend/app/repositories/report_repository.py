"""Consultas de los reportes de ventas."""

from decimal import Decimal

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from app.models.products import Product
from app.models.sale import Sale, SaleStatus
from app.models.sale_item import SaleItem
from app.schemas.common import DateRangeFilters


def _as_decimal(value: object) -> Decimal:
    """Pasa a Decimal una suma (SQLite suma como float; ``None`` si no hay filas)."""
    return Decimal(str(value)) if value is not None else Decimal("0")


def _paid_in_range(filters: DateRangeFilters) -> ColumnElement[bool]:
    """Condición común: ventas pagadas dentro del periodo.

    Args:
        filters: Rango de fechas.
    """
    conditions = [Sale.status == SaleStatus.PAID]
    if filters.start is not None:
        conditions.append(Sale.created_at >= filters.start)
    if filters.end is not None:
        conditions.append(Sale.created_at < filters.end)
    return and_(*conditions)


class ReportRepository:
    """Consultas de solo lectura para los reportes."""

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def sales_totals(self, filters: DateRangeFilters) -> tuple[int, Decimal]:
        """Cuenta y suma las ventas pagadas del periodo.

        Args:
            filters: Rango de fechas.

        Returns:
            Número de ventas y su total.
        """
        statement = select(func.count(Sale.id), func.sum(Sale.total)).where(_paid_in_range(filters))
        count, total = self._db.execute(statement).one()
        return count, _as_decimal(total)

    def revenue_and_cost(self, filters: DateRangeFilters) -> tuple[Decimal, Decimal, Decimal]:
        """Separa lo vendido según si el producto tiene costo capturado.

        Usa el costo actual del producto: el sistema no guarda el costo que tenía
        el día de cada venta.

        Args:
            filters: Rango de fechas.

        Returns:
            Venta de productos con costo, su costo y venta de productos sin costo.
        """
        with_cost = Product.cost.is_not(None)
        statement = (
            select(
                func.sum(SaleItem.subtotal).filter(with_cost),
                func.sum(SaleItem.qty * Product.cost).filter(with_cost),
                func.sum(SaleItem.subtotal).filter(Product.cost.is_(None)),
            )
            # Las columnas solo son sumas: hay que decir de qué tabla parte el JOIN
            .select_from(SaleItem)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .join(Product, SaleItem.product_id == Product.id)
            .where(_paid_in_range(filters))
        )
        revenue, cost, without_cost = self._db.execute(statement).one()
        return _as_decimal(revenue), _as_decimal(cost), _as_decimal(without_cost)

    def top_products(
        self, filters: DateRangeFilters, limit: int
    ) -> list[tuple[int, str, Decimal, Decimal]]:
        """Regresa los productos que más dinero dejaron en el periodo.

        Args:
            filters: Rango de fechas.
            limit: Máximo de productos.

        Returns:
            Id, nombre, cantidad vendida e importe de cada producto.
        """
        total = func.sum(SaleItem.subtotal)
        statement = (
            select(Product.id, Product.name, func.sum(SaleItem.qty), total)
            .join(SaleItem, SaleItem.product_id == Product.id)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .where(_paid_in_range(filters))
            .group_by(Product.id, Product.name)
            .order_by(total.desc(), Product.name)
            .limit(limit)
        )
        return [
            (product_id, name, _as_decimal(quantity), _as_decimal(amount))
            for product_id, name, quantity, amount in self._db.execute(statement)
        ]

    def idle_products(
        self, filters: DateRangeFilters, limit: int
    ) -> tuple[list[tuple[int, str]], int]:
        """Regresa los productos activos que no se vendieron en el periodo.

        Args:
            filters: Rango de fechas.
            limit: Máximo de productos a listar.

        Returns:
            Id y nombre de los productos listados, y cuántos son en total.
        """
        sold = (
            select(SaleItem.product_id)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .where(_paid_in_range(filters))
        )
        idle = and_(Product.is_active.is_(True), Product.id.not_in(sold))
        rows = self._db.execute(
            select(Product.id, Product.name).where(idle).order_by(Product.name).limit(limit)
        ).all()
        total = self._db.scalar(select(func.count(Product.id)).where(idle)) or 0
        return [(product_id, name) for product_id, name in rows], total
