"""Reglas de negocio de clientes y abonos a su cuenta de fiado."""

import logging
from collections.abc import Sequence
from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError
from app.core.unit_of_work import UnitOfWork
from app.models.customer import Customer
from app.models.customer_payment import CustomerPayment
from app.repositories.cash_repository import CashRepository
from app.repositories.sale_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerPaymentCreate, CustomerUpdate
from app.services.cash_service import CashClosedError

logger = logging.getLogger(__name__)


class CustomerNotFoundInCatalogError(NotFoundError):
    """El cliente no existe."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Cliente no encontrado")


class PaymentExceedsDebtError(ConflictError):
    """El abono es mayor que lo que debe el cliente."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El abono es mayor que lo que debe el cliente")


class CustomerService:
    """Alta y consulta de clientes, y abonos a su cuenta."""

    def __init__(
        self, customers: CustomerRepository, cash: CashRepository, uow: UnitOfWork
    ) -> None:
        """Crea el servicio.

        Args:
            customers: Repositorio de clientes.
            cash: Repositorio de caja, para exigir una caja abierta al recibir un abono.
            uow: Transacción de la petición.
        """
        self._customers = customers
        self._cash = cash
        self._uow = uow

    def list_customers(self) -> Sequence[Customer]:
        """Regresa los clientes ordenados por nombre."""
        return self._customers.list_all()

    def create_customer(self, data: CustomerCreate) -> Customer:
        """Da de alta un cliente sin deuda.

        Args:
            data: Nombre, teléfono y límite de fiado.
        """
        customer = self._customers.add(
            Customer(
                name=data.name,
                phone=data.phone or None,
                credit_limit=data.credit_limit,
                balance=Decimal("0"),
            )
        )
        self._uow.commit()
        logger.info("Cliente creado id=%s", customer.id)
        return customer

    def update_customer(self, customer_id: int, data: CustomerUpdate) -> Customer:
        """Actualiza solo los campos enviados. El saldo no se edita a mano.

        Args:
            customer_id: Id del cliente.
            data: Cambios validados.

        Raises:
            CustomerNotFoundInCatalogError: Si no existe.
        """
        customer = self._customers.get(customer_id)
        if customer is None:
            raise CustomerNotFoundInCatalogError()
        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(customer, name, value)
        self._uow.commit()
        return customer

    def record_payment(
        self, customer_id: int, data: CustomerPaymentCreate, user_id: int
    ) -> CustomerPayment:
        """Registra un abono y baja la deuda del cliente.

        Args:
            customer_id: Id del cliente.
            data: Importe y método.
            user_id: Quien recibe el abono.

        Raises:
            CashClosedError: Si la caja está cerrada: el dinero no entraría en ningún corte.
            CustomerNotFoundInCatalogError: Si el cliente no existe.
            PaymentExceedsDebtError: Si abona más de lo que debe.
        """
        if self._cash.get_open() is None:
            raise CashClosedError()

        customer = self._customers.get(customer_id, for_update=True)
        if customer is None:
            raise CustomerNotFoundInCatalogError()
        if data.amount > customer.balance:
            raise PaymentExceedsDebtError()

        customer.balance -= data.amount
        payment = self._customers.add_payment(
            CustomerPayment(
                customer_id=customer_id, amount=data.amount, method=data.method, user_id=user_id
            )
        )
        self._uow.commit()
        logger.info("Abono cliente=%s importe=%s", customer_id, data.amount)
        return payment

    def list_payments(self, customer_id: int, limit: int) -> Sequence[CustomerPayment]:
        """Regresa los abonos de un cliente, los más recientes primero.

        Args:
            customer_id: Id del cliente.
            limit: Máximo de resultados.

        Raises:
            CustomerNotFoundInCatalogError: Si el cliente no existe.
        """
        if self._customers.get(customer_id) is None:
            raise CustomerNotFoundInCatalogError()
        return self._customers.list_payments(customer_id, limit)
