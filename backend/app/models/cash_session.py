"""Modelo ORM de turnos de caja (apertura y corte)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CashSession(Base):
    """Turno de caja: del fondo inicial al corte.

    ``expected_cash`` y ``sales_total`` se guardan al cerrar como foto del corte:
    un corte ya hecho no debe cambiar aunque después se cancele una venta.
    """

    __tablename__ = "cash_sessions"
    __table_args__ = (
        # La base garantiza que solo haya una caja abierta, incluso con dos
        # aperturas simultáneas
        Index(
            "cash_sessions_one_open",
            text("(closed_at IS NULL)"),
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
            sqlite_where=text("closed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    opened_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    opened_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    counted_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expected_cash: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    sales_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(String(200))
