"""Modelos ORM del catálogo: categorías y productos."""

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Category(Base):
    """Categoría a la que pertenece un producto (Bebidas, Lácteos, ...)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class Product(Base):
    """Producto vendible del catálogo."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(50))
    sku: Mapped[str | None] = mapped_column(String(50))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    unit: Mapped[str | None] = mapped_column(String(20), default="pieza")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
