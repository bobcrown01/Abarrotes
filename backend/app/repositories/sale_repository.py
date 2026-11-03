"""Acceso a datos de ventas y clientes."""

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.customer_payment import CustomerPayment
from app.models.sale import Sale, SaleStatus
from app.schemas.sale import SaleFilters


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

    @staticmethod
    def _apply_filters(statement: Select, filters: SaleFilters) -> Select:
        """Agrega a una consulta las condiciones de los filtros recibidos.

        Args:
            statement: Consulta sobre ``sales``.
            filters: Estado, folio y rango de fechas.
        """
        if filters.status is not None:
            statement = statement.where(Sale.status == filters.status)
        if filters.folio:
            # Coincidencia parcial sin distinguir mayúsculas; autoescape evita que
            # un % o _ tecleado actúe como comodín
            statement = statement.where(Sale.folio.icontains(filters.folio, autoescape=True))
        if filters.start is not None:
            statement = statement.where(Sale.created_at >= filters.start)
        if filters.end is not None:
            statement = statement.where(Sale.created_at < filters.end)
        return statement

    def list_filtered(self, filters: SaleFilters) -> Sequence[Sale]:
        """Regresa las ventas que coinciden, las más recientes primero.

        Args:
            filters: Estado, folio, rango de fechas y paginación.
        """
        statement = self._apply_filters(select(Sale), filters)
        statement = statement.order_by(Sale.id.desc()).limit(filters.limit).offset(filters.offset)
        return self._db.scalars(statement).all()

    def summarize(self, filters: SaleFilters) -> tuple[int, Decimal]:
        """Cuenta y suma las ventas pagadas que coinciden con los filtros.

        Solo cuenta pagadas: una pendiente o cancelada no es dinero de la tienda.

        Args:
            filters: Estado, folio y rango de fechas (la paginación no aplica).

        Returns:
            Número de ventas y su total.
        """
        statement = select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
        statement = self._apply_filters(statement, filters).where(Sale.status == SaleStatus.PAID)
        count, total = self._db.execute(statement).one()
        # str(): SQLite suma como float; así todo queda en Decimal exacto
        return count, Decimal(str(total))

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

    def get(self, customer_id: int, *, for_update: bool = False) -> Customer | None:
        """Busca un cliente por id.

        Args:
            customer_id: Id del cliente.
            for_update: Bloquea la fila para cambiar su saldo sin carreras.
        """
        statement = select(Customer).where(Customer.id == customer_id)
        if for_update:
            statement = statement.with_for_update()
        return self._db.scalar(statement)

    def list_all(self) -> Sequence[Customer]:
        """Regresa los clientes ordenados por nombre."""
        return self._db.scalars(select(Customer).order_by(Customer.name)).all()

    def add(self, customer: Customer) -> Customer:
        """Inserta un cliente y lo regresa con su id.

        Args:
            customer: Cliente nuevo.
        """
        self._db.add(customer)
        self._db.flush()
        return customer

    def add_payment(self, payment: CustomerPayment) -> CustomerPayment:
        """Inserta un abono y lo regresa con su id y fecha.

        Args:
            payment: Abono nuevo.
        """
        self._db.add(payment)
        self._db.flush()
        self._db.refresh(payment)
        return payment

    def list_payments(self, customer_id: int, limit: int) -> Sequence[CustomerPayment]:
        """Regresa los abonos de un cliente, los más recientes primero.

        Args:
            customer_id: Id del cliente.
            limit: Máximo de resultados.
        """
        statement = (
            select(CustomerPayment)
            .where(CustomerPayment.customer_id == customer_id)
            .order_by(CustomerPayment.id.desc())
            .limit(limit)
        )
        return self._db.scalars(statement).all()
