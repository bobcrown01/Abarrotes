"""Modelo ORM de ventas."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.sale_item import SaleItem


class SaleStatus:
    """Estados posibles de una venta."""

    PENDING = "pendiente"
    PAID = "pagada"
    CANCELLED = "cancelada"


class Sale(Base):
    """Venta (ticket) con sus partidas y pagos."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str | None] = mapped_column(String(50), unique=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), default=SaleStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", order_by="SaleItem.id", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="sale", order_by="Payment.id", cascade="all, delete-orphan"
    )

    @property
    def amount_paid(self) -> Decimal:
        """Suma de los pagos registrados."""
        return sum((p.amount for p in self.payments), Decimal("0"))
