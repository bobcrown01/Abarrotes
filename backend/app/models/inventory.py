"""Modelo ORM de existencias por producto."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Inventory(Base):
    """Existencias actuales de un producto (una fila por producto)."""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, unique=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    max_stock: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
