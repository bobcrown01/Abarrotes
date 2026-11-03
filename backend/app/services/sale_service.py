"""Reglas de negocio de ventas: apertura, partidas, pagos, cierre y cancelación."""

import logging
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.unit_of_work import UnitOfWork
from app.models.inventory_movement import InventoryMovement
from app.models.payment import Payment
from app.models.sale import Sale, SaleStatus
from app.models.sale_item import SaleItem
from app.repositories.cash_repository import CashRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sale_repository import CustomerRepository, SaleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.sale import PaymentCreate, SaleCreate, SaleFilters, SaleItemCreate
from app.services.cash_service import CashClosedError
from app.services.errors import ProductNotFoundError, UserNotFoundError
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)

_CENT = Decimal("0.01")

CREDIT_METHOD = "venta_credito"  # Fiado: el cliente lo paga después con abonos


class SaleNotFoundError(NotFoundError):
    """La venta no existe."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Venta no encontrada")


class SaleNotPendingError(ConflictError):
    """La operación solo se permite en ventas pendientes."""

    def __init__(self, status: str) -> None:
        """Crea el error.

        Args:
            status: Estado actual de la venta.
        """
        super().__init__(f"La venta ya está {status}")


class EmptySaleError(ConflictError):
    """No se puede cerrar una venta sin productos."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("La venta no tiene productos")


class SaleNotFullyPaidError(ConflictError):
    """Los pagos no cubren el total de la venta."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("La venta no está completamente pagada")


class PaymentExceedsBalanceError(ConflictError):
    """El pago es mayor que lo que falta por pagar."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El pago excede el saldo pendiente")


class InactiveProductError(ConflictError):
    """No se pueden vender productos desactivados."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El producto está inactivo")


class InvalidDiscountError(AppError):
    """El descuento es mayor que el importe de la partida."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El descuento no puede ser mayor que el importe")


class CustomerNotFoundError(AppError):
    """El cliente indicado no existe (400: dato inválido)."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El cliente no existe")


class CreditRequiresCustomerError(ConflictError):
    """Para fiar hay que indicar a quién."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Para fiar hay que elegir un cliente")


class CreditLimitExceededError(ConflictError):
    """La deuda del cliente rebasaría su límite de fiado."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("La venta rebasa el límite de fiado del cliente")


class CancelPaidForbiddenError(ForbiddenError):
    """Solo un rol de administración puede cancelar una venta ya pagada."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Solo un supervisor o administrador puede cancelar una venta pagada")


class SaleService:
    """Ciclo de vida de una venta.

    ``pendiente`` → (partidas y pagos) → ``pagada`` (descuenta inventario)
    ``pendiente`` → ``cancelada``
    ``pagada`` → ``cancelada`` (regresa el inventario)
    """

    def __init__(
        self,
        sales: SaleRepository,
        products: ProductRepository,
        users: UserRepository,
        customers: CustomerRepository,
        cash: CashRepository,
        inventory: InventoryService,
        uow: UnitOfWork,
    ) -> None:
        """Crea el servicio.

        Args:
            sales: Repositorio de ventas.
            products: Repositorio de productos.
            users: Repositorio de usuarios.
            customers: Repositorio de clientes.
            cash: Repositorio de caja, para exigir una caja abierta al cobrar.
            inventory: Servicio de inventario para descontar o regresar existencias.
            uow: Transacción de la petición.
        """
        self._sales = sales
        self._products = products
        self._users = users
        self._customers = customers
        self._cash = cash
        self._inventory = inventory
        self._uow = uow

    # ---------- Consultas ----------

    def get_sale(self, sale_id: int) -> Sale:
        """Regresa una venta con sus partidas y pagos.

        Args:
            sale_id: Id de la venta.

        Raises:
            SaleNotFoundError: Si no existe.
        """
        sale = self._sales.get(sale_id)
        if sale is None:
            raise SaleNotFoundError()
        return sale

    def list_sales(self, filters: SaleFilters) -> Sequence[Sale]:
        """Regresa las ventas que coinciden con los filtros, las más recientes primero.

        Args:
            filters: Estado, folio, rango de fechas y paginación.
        """
        return self._sales.list_filtered(filters)

    def summarize_sales(self, filters: SaleFilters) -> tuple[int, Decimal]:
        """Cuenta y suma las ventas pagadas que coinciden con los filtros.

        Args:
            filters: Estado, folio y rango de fechas.

        Returns:
            Número de ventas y su total.
        """
        return self._sales.summarize(filters)

    # ---------- Operaciones ----------

    def create_sale(self, data: SaleCreate) -> Sale:
        """Abre una venta pendiente.

        Args:
            data: Usuario que vende y cliente opcional.

        Raises:
            UserNotFoundError: Si el usuario no existe.
            CustomerNotFoundError: Si el cliente no existe.
            CashClosedError: Si la caja está cerrada.
        """
        # Se avisa desde el inicio de la venta, antes de que el cajero la arme
        self._require_open_cash()
        if not self._users.exists(data.user_id):
            raise UserNotFoundError()
        if data.customer_id is not None and not self._customers.exists(data.customer_id):
            raise CustomerNotFoundError()

        sale = self._sales.add(
            Sale(
                customer_id=data.customer_id,
                user_id=data.user_id,
                status=SaleStatus.PENDING,
                subtotal=Decimal("0"),
                discount=Decimal("0"),
                total=Decimal("0"),
            )
        )
        # El folio sale del id: único y sin colisiones aunque se abran dos
        # ventas en el mismo segundo
        sale.folio = f"V-{sale.id:06d}"
        self._uow.commit()

        logger.info("Venta abierta %s usuario=%s", sale.folio, sale.user_id)
        return sale

    def add_item(self, data: SaleItemCreate) -> Sale:
        """Agrega una partida con el precio vigente del catálogo.

        Args:
            data: Venta, producto, cantidad y descuento.

        Returns:
            La venta con totales actualizados.

        Raises:
            SaleNotFoundError: Si la venta no existe.
            SaleNotPendingError: Si la venta ya se cerró o canceló.
            ProductNotFoundError: Si el producto no existe.
            InactiveProductError: Si el producto está desactivado.
            InvalidDiscountError: Si el descuento supera el importe.
        """
        sale = self._get_pending_for_update(data.sale_id)

        product = self._products.get(data.product_id)
        if product is None:
            raise ProductNotFoundError()
        if not product.is_active:
            raise InactiveProductError()

        gross = (data.qty * product.price).quantize(_CENT, rounding=ROUND_HALF_UP)
        if data.discount > gross:
            raise InvalidDiscountError()
        subtotal = gross - data.discount

        sale.items.append(
            SaleItem(
                product_id=product.id,
                qty=data.qty,
                price=product.price,
                discount=data.discount,
                subtotal=subtotal,
            )
        )
        sale.subtotal += subtotal
        sale.total = sale.subtotal - sale.discount
        self._uow.commit()
        return sale

    def add_payment(self, data: PaymentCreate) -> Sale:
        """Registra un pago y calcula el cambio en el servidor.

        Args:
            data: Venta, método, importe y lo recibido (efectivo).

        Returns:
            La venta con el pago aplicado.

        Raises:
            SaleNotFoundError: Si la venta no existe.
            SaleNotPendingError: Si la venta ya se cerró o canceló.
            PaymentExceedsBalanceError: Si el importe supera el saldo pendiente.
            CashClosedError: Si cerraron la caja mientras se armaba la venta.
            CreditRequiresCustomerError: Si es fiado y la venta no tiene cliente.
            CreditLimitExceededError: Si el fiado rebasa el límite del cliente.
        """
        # Sin caja abierta, este dinero no entraría en ningún corte
        self._require_open_cash()
        sale = self._get_pending_for_update(data.sale_id)

        if data.amount > sale.total - sale.amount_paid:
            raise PaymentExceedsBalanceError()
        if data.method == CREDIT_METHOD:
            self._check_credit(sale, data.amount)

        change = data.received - data.amount if data.received is not None else None
        sale.payments.append(
            Payment(
                method=data.method,
                amount=data.amount,
                received=data.received,
                change=change,
                reference=data.reference,
            )
        )
        self._uow.commit()
        return sale

    def close_sale(self, sale_id: int) -> Sale:
        """Marca la venta como pagada y descuenta el inventario.

        Args:
            sale_id: Id de la venta.

        Raises:
            SaleNotFoundError: Si la venta no existe.
            SaleNotPendingError: Si la venta ya se cerró o canceló.
            EmptySaleError: Si no tiene partidas.
            SaleNotFullyPaidError: Si los pagos no cubren el total.
        """
        sale = self._get_pending_for_update(sale_id)
        if not sale.items:
            raise EmptySaleError()
        if sale.amount_paid < sale.total:
            raise SaleNotFullyPaidError()

        sale.status = SaleStatus.PAID
        self._move_stock(sale, "salida", f"Venta {sale.folio}")
        # La deuda nace al cerrar la venta, igual que la salida de inventario
        self._apply_credit(sale, sign=1)
        self._uow.commit()

        logger.info("Venta cerrada %s total=%s", sale.folio, sale.total)
        return sale

    def cancel_sale(self, sale_id: int, *, allow_paid: bool = True) -> Sale:
        """Cancela una venta; si ya estaba pagada, regresa el inventario.

        Args:
            sale_id: Id de la venta.
            allow_paid: Si quien cancela tiene permiso para anular una venta pagada.

        Raises:
            SaleNotFoundError: Si la venta no existe.
            SaleNotPendingError: Si ya estaba cancelada.
            CancelPaidForbiddenError: Si está pagada y no tiene permiso.
        """
        sale = self._sales.get(sale_id, for_update=True)
        if sale is None:
            raise SaleNotFoundError()
        if sale.status == SaleStatus.CANCELLED:
            raise SaleNotPendingError(sale.status)
        if sale.status == SaleStatus.PAID and not allow_paid:
            raise CancelPaidForbiddenError()

        # Una venta pendiente nunca descontó inventario: no hay nada que regresar
        if sale.status == SaleStatus.PAID:
            self._move_stock(sale, "entrada", f"Cancelación {sale.folio}")
            # Si fue fiada, el cliente deja de deber esa venta
            self._apply_credit(sale, sign=-1)

        sale.status = SaleStatus.CANCELLED
        self._uow.commit()

        logger.info("Venta cancelada %s", sale.folio)
        return sale

    # ---------- Apoyo ----------

    def _require_open_cash(self) -> None:
        """Exige una caja abierta para que todo cobro entre en un corte."""
        if self._cash.get_open() is None:
            raise CashClosedError()

    def _check_credit(self, sale: Sale, amount: Decimal) -> None:
        """Verifica que la venta tenga cliente y que el fiado quepa en su límite.

        Args:
            sale: Venta que se está cobrando.
            amount: Importe que se quiere fiar.

        Raises:
            CreditRequiresCustomerError: Si la venta no tiene cliente.
            CreditLimitExceededError: Si la deuda rebasaría el límite.
        """
        customer = None
        if sale.customer_id is not None:
            customer = self._customers.get(sale.customer_id, for_update=True)
        if customer is None:
            raise CreditRequiresCustomerError()
        if customer.balance + amount > customer.credit_limit:
            raise CreditLimitExceededError()

    def _apply_credit(self, sale: Sale, *, sign: int) -> None:
        """Suma o resta a la deuda del cliente lo fiado en esta venta.

        Args:
            sale: Venta que se cierra o se cancela.
            sign: 1 para sumar la deuda, -1 para quitarla.
        """
        credit = sum((p.amount for p in sale.payments if p.method == CREDIT_METHOD), Decimal("0"))
        if not credit or sale.customer_id is None:
            return
        customer = self._customers.get(sale.customer_id, for_update=True)
        if customer is not None:
            customer.balance += sign * credit

    def _get_pending_for_update(self, sale_id: int) -> Sale:
        """Regresa una venta pendiente con la fila bloqueada."""
        sale = self._sales.get(sale_id, for_update=True)
        if sale is None:
            raise SaleNotFoundError()
        if sale.status != SaleStatus.PENDING:
            raise SaleNotPendingError(sale.status)
        return sale

    def _move_stock(self, sale: Sale, movement_type: str, reason: str) -> None:
        """Descuenta o regresa existencias por cada partida de la venta."""
        # Orden fijo por producto: dos ventas simultáneas bloquean las filas de
        # inventario en el mismo orden y no se produce un deadlock
        for item in sorted(sale.items, key=lambda i: i.product_id):
            self._inventory.apply_movement(
                InventoryMovement(
                    product_id=item.product_id,
                    type=movement_type,
                    quantity=item.qty,
                    reason=reason,
                    user_id=sale.user_id,
                ),
                create_if_missing=False,
                allow_negative=True,
            )
