"""Modelo ORM de clientes."""

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Customer(Base):
    """Cliente de la tienda (para ventas a crédito y monedero)."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(100))
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
