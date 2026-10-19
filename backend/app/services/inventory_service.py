"""Reglas de negocio de existencias de inventario."""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError
from app.core.unit_of_work import UnitOfWork
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.products import Product
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.inventory import InventoryMovementCreate, MovementFilters, StockFilters
from app.services.errors import ProductNotFoundError, UserNotFoundError

logger = logging.getLogger(__name__)


class InsufficientStockError(ConflictError):
    """La salida dejaría las existencias en negativo."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Inventario insuficiente")


class StockNotFoundError(NotFoundError):
    """El producto no tiene registro de existencias."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Inventario no encontrado para este producto")


@dataclass(frozen=True)
class StockView:
    """Existencias de un producto con los datos que muestra la API."""

    product_id: int
    product_name: str
    quantity: Decimal
    min_stock: Decimal
    max_stock: Decimal | None
    unit: str | None
    is_active: bool

    @classmethod
    def build(cls, inventory: Inventory, product: Product) -> "StockView":
        """Combina la fila de inventario con su producto."""
        return cls(
            product_id=inventory.product_id,
            product_name=product.name,
            quantity=inventory.quantity,
            min_stock=inventory.min_stock,
            max_stock=inventory.max_stock,
            unit=product.unit,
            is_active=product.is_active,
        )


@dataclass(frozen=True)
class MovementView:
    """Movimiento del historial con el nombre de su producto."""

    movement_id: int
    product_id: int
    product_name: str
    type: str
    quantity: Decimal
    reason: str | None
    created_at: datetime
    user_id: int | None

    @classmethod
    def build(cls, movement: InventoryMovement, product: Product) -> "MovementView":
        """Combina el movimiento con su producto."""
        return cls(
            movement_id=movement.id,
            product_id=movement.product_id,
            product_name=product.name,
            type=movement.type,
            quantity=movement.quantity,
            reason=movement.reason,
            created_at=movement.created_at,
            user_id=movement.user_id,
        )


@dataclass(frozen=True)
class RecordedMovement:
    """Movimiento guardado junto con las existencias que quedaron."""

    id: int
    product_id: int
    type: str
    quantity: Decimal
    reason: str | None
    user_id: int | None
    created_at: datetime
    new_quantity: Decimal


class InventoryService:
    """Casos de uso de inventario. También lo usa la venta al cerrarse o cancelarse."""

    def __init__(
        self,
        inventory: InventoryRepository,
        products: ProductRepository,
        users: UserRepository,
        uow: UnitOfWork,
    ) -> None:
        """Crea el servicio.

        Args:
            inventory: Repositorio de existencias y movimientos.
            products: Repositorio de productos.
            users: Repositorio de usuarios.
            uow: Transacción de la petición.
        """
        self._inventory = inventory
        self._products = products
        self._users = users
        self._uow = uow

    # ---------- Consultas ----------

    def list_stock(self, filters: StockFilters) -> list[StockView]:
        """Regresa existencias filtradas por categoría y disponibilidad.

        Args:
            filters: Filtros validados.
        """
        return [StockView.build(inv, prod) for inv, prod in self._inventory.list_stock(filters)]

    def get_stock(self, product_id: int) -> StockView:
        """Regresa las existencias de un producto.

        Args:
            product_id: Id del producto.

        Raises:
            StockNotFoundError: Si el producto no lleva inventario.
        """
        row = self._inventory.get_stock(product_id)
        if row is None:
            raise StockNotFoundError()
        return StockView.build(*row)

    def list_movements(self, filters: MovementFilters) -> list[MovementView]:
        """Regresa el historial de movimientos filtrado.

        Args:
            filters: Filtros validados.
        """
        return [MovementView.build(m, p) for m, p in self._inventory.list_movements(filters)]

    def list_product_movements(
        self, product_id: int, limit: int, offset: int
    ) -> list[MovementView]:
        """Regresa el historial de un producto.

        Args:
            product_id: Id del producto.
            limit: Máximo de resultados.
            offset: Resultados a saltar.

        Raises:
            ProductNotFoundError: Si el producto no existe.
        """
        if self._products.get(product_id) is None:
            raise ProductNotFoundError()
        filters = MovementFilters(product_id=product_id, limit=limit, offset=offset)
        return self.list_movements(filters)

    # ---------- Escrituras ----------

    def record_movement(self, data: InventoryMovementCreate) -> RecordedMovement:
        """Registra un movimiento manual (entrada, salida o ajuste) y lo confirma.

        Args:
            data: Movimiento validado por Pydantic.

        Returns:
            El movimiento guardado y las existencias resultantes.

        Raises:
            ProductNotFoundError: Si el producto no existe.
            UserNotFoundError: Si el usuario no existe.
            InsufficientStockError: Si una salida deja existencias negativas.
        """
        if self._products.get(data.product_id) is None:
            raise ProductNotFoundError()
        if data.user_id is not None and not self._users.exists(data.user_id):
            raise UserNotFoundError()

        movement = InventoryMovement(**data.model_dump())
        new_quantity = self.apply_movement(movement)
        self._uow.commit()

        logger.info(
            "Movimiento de inventario id=%s producto=%s %s %s → %s",
            movement.id,
            movement.product_id,
            movement.type,
            movement.quantity,
            new_quantity,
        )
        return RecordedMovement(
            id=movement.id,
            product_id=movement.product_id,
            type=movement.type,
            quantity=movement.quantity,
            reason=movement.reason,
            user_id=movement.user_id,
            created_at=movement.created_at,
            # Siempre hay valor: create_if_missing es True por omisión
            new_quantity=new_quantity or Decimal("0"),
        )

    def apply_movement(
        self,
        movement: InventoryMovement,
        *,
        create_if_missing: bool = True,
        allow_negative: bool = False,
    ) -> Decimal | None:
        """Aplica un movimiento a las existencias **sin** confirmar la transacción.

        Args:
            movement: Movimiento a aplicar (se agrega al historial).
            create_if_missing: Si el producto no tiene fila de inventario, la
                crea en cero. Con ``False`` el movimiento se ignora (productos
                que no llevan control de existencias, como servicios).
            allow_negative: Permite que una salida deje existencias negativas.
                Las ventas lo usan para no bloquear el cobro en caja cuando el
                conteo está desfasado.

        Returns:
            Existencias resultantes, o ``None`` si el producto no lleva inventario.

        Raises:
            InsufficientStockError: Si una salida deja existencias negativas y
                ``allow_negative`` es ``False``.
        """
        inventory = self._inventory.get_for_update(movement.product_id)
        if inventory is None:
            if not create_if_missing:
                return None
            inventory = Inventory(product_id=movement.product_id, quantity=Decimal("0"))
            self._inventory.add(inventory)

        match movement.type:
            case "entrada":
                new_quantity = inventory.quantity + movement.quantity
            case "salida":
                new_quantity = inventory.quantity - movement.quantity
                if new_quantity < 0 and not allow_negative:
                    raise InsufficientStockError()
            case "ajuste":
                new_quantity = movement.quantity
            case _:
                raise ValueError(f"Tipo de movimiento desconocido: {movement.type}")

        inventory.quantity = new_quantity
        self._inventory.add_movement(movement)
        return new_quantity
