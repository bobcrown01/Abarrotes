"""Reglas de negocio de la caja: apertura, resumen y corte."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError
from app.core.unit_of_work import UnitOfWork
from app.models.cash_session import CashSession
from app.repositories.cash_repository import CashRepository
from app.schemas.cash import CashClose, CashOpen

logger = logging.getLogger(__name__)

CASH_METHOD = "efectivo"  # El único método que entra físicamente a la caja


class CashAlreadyOpenError(ConflictError):
    """Ya hay una caja abierta."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("La caja ya está abierta")


class CashClosedError(ConflictError):
    """La operación requiere una caja abierta."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("La caja está cerrada. Ábrela en Corte de caja para poder cobrar")


@dataclass(frozen=True)
class MethodTotal:
    """Importe cobrado con un método de pago."""

    method: str
    amount: Decimal


@dataclass(frozen=True)
class CashSummary:
    """Turno de caja con los importes que se muestran en pantalla."""

    id: int
    opened_by: int | None
    opened_at: datetime
    opening_amount: Decimal
    closed_by: int | None = None
    closed_at: datetime | None = None
    counted_amount: Decimal | None = None
    expected_cash: Decimal | None = None
    difference: Decimal | None = None
    sales_total: Decimal | None = None
    sales_count: int | None = None
    by_method: list[MethodTotal] = field(default_factory=list)
    notes: str | None = None

    def hide_expected(self) -> "CashSummary":
        """Quita lo que un cajero no debe ver antes de contar el efectivo."""
        return replace(self, expected_cash=None, sales_total=None, sales_count=None, by_method=[])


class CashService:
    """Ciclo de un turno: abrir, vender, contar y cerrar."""

    def __init__(self, cash: CashRepository, uow: UnitOfWork) -> None:
        """Crea el servicio.

        Args:
            cash: Repositorio de turnos de caja.
            uow: Transacción de la petición.
        """
        self._cash = cash
        self._uow = uow

    def current(self) -> CashSummary | None:
        """Regresa la caja abierta con lo vendido hasta ahora, o ``None`` si está cerrada."""
        session = self._cash.get_open()
        return self._live_summary(session) if session else None

    def open_cash(self, data: CashOpen, user_id: int) -> CashSummary:
        """Abre la caja con su fondo inicial.

        Args:
            data: Fondo inicial.
            user_id: Quien abre.

        Raises:
            CashAlreadyOpenError: Si ya hay una caja abierta.
        """
        if self._cash.get_open() is not None:
            raise CashAlreadyOpenError()
        try:
            session = self._cash.add(
                CashSession(opened_by=user_id, opening_amount=data.opening_amount)
            )
            self._uow.commit()
        except IntegrityError as exc:
            # Dos aperturas simultáneas: el índice único deja pasar solo a una
            self._uow.rollback()
            logger.warning("Apertura de caja rechazada por la base: %s", exc.orig)
            raise CashAlreadyOpenError() from exc

        logger.info("Caja abierta id=%s fondo=%s", session.id, session.opening_amount)
        return self._live_summary(session)

    def close_cash(self, data: CashClose, user_id: int) -> CashSummary:
        """Hace el corte: compara el efectivo contado contra el esperado.

        Args:
            data: Efectivo contado y notas.
            user_id: Quien hace el corte.

        Returns:
            El corte completo, con el esperado y la diferencia.

        Raises:
            CashClosedError: Si no hay una caja abierta.
        """
        session = self._cash.get_open(for_update=True)
        if session is None:
            raise CashClosedError()

        # El resumen se calcula antes de cerrar y se guarda como foto del corte
        summary = self._live_summary(session)
        session.closed_by = user_id
        session.closed_at = datetime.now(UTC).replace(tzinfo=None)  # UTC sin zona, como NOW()
        session.counted_amount = data.counted_amount
        session.expected_cash = summary.expected_cash
        session.sales_total = summary.sales_total
        session.notes = data.notes
        self._uow.commit()

        difference = data.counted_amount - (summary.expected_cash or Decimal("0"))
        logger.info("Corte de caja id=%s diferencia=%s", session.id, difference)
        return replace(
            summary,
            closed_by=user_id,
            closed_at=session.closed_at,
            counted_amount=data.counted_amount,
            difference=difference,
            notes=data.notes,
        )

    def history(self, limit: int, offset: int) -> Sequence[CashSummary]:
        """Regresa los cortes hechos, los más recientes primero.

        Args:
            limit: Máximo de resultados.
            offset: Resultados a saltar.
        """
        return [self._closed_summary(s) for s in self._cash.list_closed(limit, offset)]

    def _live_summary(self, session: CashSession) -> CashSummary:
        """Calcula lo vendido desde la apertura y el efectivo que debería haber.

        Args:
            session: Turno abierto.
        """
        totals = self._cash.totals_by_method(session.opened_at)
        cash_sales = totals.get(CASH_METHOD, Decimal("0"))
        # Un abono no es venta (se contó cuando se fió), pero en efectivo sí entra a la caja
        abonos = self._cash.abonos_by_method(session.opened_at)
        cash_abonos = abonos.get(CASH_METHOD, Decimal("0"))
        return CashSummary(
            id=session.id,
            opened_by=session.opened_by,
            opened_at=session.opened_at,
            opening_amount=session.opening_amount,
            # Pagos en efectivo por el importe de la venta: el cambio ya salió de la caja
            expected_cash=session.opening_amount + cash_sales + cash_abonos,
            sales_total=sum(totals.values(), Decimal("0")),
            sales_count=self._cash.count_sales(session.opened_at),
            by_method=[
                *(MethodTotal(m, a) for m, a in sorted(totals.items())),
                *(MethodTotal(f"abono_{m}", a) for m, a in sorted(abonos.items())),
            ],
        )

    @staticmethod
    def _closed_summary(session: CashSession) -> CashSummary:
        """Arma el resumen de un corte con la foto guardada al cerrar.

        Args:
            session: Turno cerrado.
        """
        expected = session.expected_cash
        counted = session.counted_amount
        return CashSummary(
            id=session.id,
            opened_by=session.opened_by,
            opened_at=session.opened_at,
            opening_amount=session.opening_amount,
            closed_by=session.closed_by,
            closed_at=session.closed_at,
            counted_amount=counted,
            expected_cash=expected,
            difference=counted - expected if counted is not None and expected is not None else None,
            sales_total=session.sales_total,
            notes=session.notes,
        )
