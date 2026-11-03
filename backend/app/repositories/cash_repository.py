"""Acceso a datos de los turnos de caja."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.cash_session import CashSession
from app.models.customer_payment import CustomerPayment
from app.models.payment import Payment
from app.models.sale import Sale, SaleStatus


class CashRepository:
    """Consultas y escrituras sobre ``cash_sessions``.

    No confirma transacciones: eso le toca al servicio.
    """

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def get_open(self, *, for_update: bool = False) -> CashSession | None:
        """Regresa la caja abierta, si hay una.

        Args:
            for_update: Bloquea la fila para cerrarla sin carreras.
        """
        statement = select(CashSession).where(CashSession.closed_at.is_(None))
        if for_update:
            statement = statement.with_for_update()
        return self._db.scalar(statement)

    def add(self, session: CashSession) -> CashSession:
        """Inserta un turno y lo regresa con id y fecha asignados.

        Args:
            session: Turno nuevo.
        """
        self._db.add(session)
        self._db.flush()
        self._db.refresh(session)
        return session

    def list_closed(self, limit: int, offset: int) -> Sequence[CashSession]:
        """Regresa los cortes hechos, los más recientes primero.

        Args:
            limit: Máximo de resultados.
            offset: Resultados a saltar.
        """
        statement = (
            select(CashSession)
            .where(CashSession.closed_at.is_not(None))
            .order_by(CashSession.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return self._db.scalars(statement).all()

    def totals_by_method(self, since: datetime) -> dict[str, Decimal]:
        """Suma lo cobrado por método de pago desde un momento dado.

        Solo cuenta ventas pagadas: una cancelada ya no está en la caja.

        Args:
            since: Apertura de la caja.

        Returns:
            Importe cobrado por cada método usado.
        """
        statement = (
            select(Payment.method, func.sum(Payment.amount))
            .join(Sale, Payment.sale_id == Sale.id)
            .where(Sale.status == SaleStatus.PAID, Payment.created_at >= since)
            .group_by(Payment.method)
        )
        # str(): SQLite suma como float; así todo queda en Decimal exacto
        return {method: Decimal(str(total)) for method, total in self._db.execute(statement)}

    def abonos_by_method(self, since: datetime) -> dict[str, Decimal]:
        """Suma los abonos de clientes por método desde un momento dado.

        Args:
            since: Apertura de la caja.

        Returns:
            Importe abonado por cada método usado.
        """
        statement = (
            select(CustomerPayment.method, func.sum(CustomerPayment.amount))
            .where(CustomerPayment.created_at >= since)
            .group_by(CustomerPayment.method)
        )
        return {method: Decimal(str(total)) for method, total in self._db.execute(statement)}

    def count_sales(self, since: datetime) -> int:
        """Cuenta las ventas pagadas desde un momento dado.

        Args:
            since: Apertura de la caja.
        """
        statement = (
            select(func.count(distinct(Payment.sale_id)))
            .join(Sale, Payment.sale_id == Sale.id)
            .where(Sale.status == SaleStatus.PAID, Payment.created_at >= since)
        )
        return self._db.scalar(statement) or 0
