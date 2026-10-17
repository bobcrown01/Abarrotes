"""Modelo ORM del historial de movimientos de inventario."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InventoryMovement(Base):
    """Registro inmutable de una entrada, salida o ajuste de existencias."""

    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # entrada / salida / ajuste
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100))
    # La hora la pone la base de datos, no el reloj del contenedor
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
