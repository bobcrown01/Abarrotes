"""Acceso a datos de ventas y clientes."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.sale import Sale


class SaleRepository:
    """Consultas y escrituras sobre ``sales`` (las partidas y pagos van en cascada).

    No confirma transacciones: eso le toca al servicio.
    """

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def get(self, sale_id: int, *, for_update: bool = False) -> Sale | None:
        """Busca una venta por id.

        Args:
            sale_id: Id de la venta.
            for_update: Bloquea la fila para modificarla sin carreras
                (dos cajas agregando partidas a la misma venta).
        """
        statement = select(Sale).where(Sale.id == sale_id)
        if for_update:
            statement = statement.with_for_update()
        return self._db.scalar(statement)

    def list_recent(self, limit: int, offset: int) -> Sequence[Sale]:
        """Regresa ventas, las más recientes primero.

        Args:
            limit: Máximo de resultados.
            offset: Resultados a saltar.
        """
        statement = select(Sale).order_by(Sale.id.desc()).limit(limit).offset(offset)
        return self._db.scalars(statement).all()

    def add(self, sale: Sale) -> Sale:
        """Inserta una venta y la regresa con id y fecha asignados.

        Args:
            sale: Venta nueva.
        """
        self._db.add(sale)
        self._db.flush()
        self._db.refresh(sale)
        return sale


class CustomerRepository:
    """Consultas sobre ``customers``."""

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def exists(self, customer_id: int) -> bool:
        """Indica si existe un cliente con ese id.

        Args:
            customer_id: Id del cliente.
        """
        return self._db.get(Customer, customer_id) is not None
