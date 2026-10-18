"""Acceso a datos de existencias y movimientos de inventario."""

from collections.abc import Sequence
from datetime import datetime, time, timedelta

from sqlalchemy import Row, Select, select
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.products import Product
from app.schemas.inventory import MovementFilters, StockFilters


class InventoryRepository:
    """Consultas y escrituras sobre ``inventory`` e ``inventory_movements``.

    No confirma transacciones: eso le toca al servicio que la usa.
    """

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def get_for_update(self, product_id: int) -> Inventory | None:
        """Regresa las existencias de un producto bloqueando la fila.

        El bloqueo (``SELECT ... FOR UPDATE``) evita que dos movimientos
        simultáneos lean la misma cantidad y uno pise al otro.

        Args:
            product_id: Id del producto.
        """
        statement = select(Inventory).where(Inventory.product_id == product_id).with_for_update()
        return self._db.scalar(statement)

    def add(self, inventory: Inventory) -> None:
        """Agrega una fila de existencias nueva a la transacción.

        Args:
            inventory: Existencias del producto.
        """
        self._db.add(inventory)

    def add_movement(self, movement: InventoryMovement) -> InventoryMovement:
        """Agrega un movimiento y lo regresa con su id y fecha.

        Args:
            movement: Movimiento a registrar.
        """
        self._db.add(movement)
        self._db.flush()
        # Carga created_at, que lo genera la base de datos
        self._db.refresh(movement)
        return movement

    # ---------- Consultas (sin bloqueo) ----------

    def _stock_query(self) -> Select[tuple[Inventory, Product]]:
        """Existencias junto con su producto (un solo JOIN, sin consultas N+1)."""
        return select(Inventory, Product).join(Product, Product.id == Inventory.product_id)

    def list_stock(self, filters: StockFilters) -> Sequence[Row[tuple[Inventory, Product]]]:
        """Regresa existencias con su producto, ordenadas por nombre.

        Args:
            filters: Categoría, con/sin existencias y paginación.
        """
        statement = self._stock_query()
        if filters.category_id is not None:
            statement = statement.where(Product.category_id == filters.category_id)
        if filters.in_stock is True:
            statement = statement.where(Inventory.quantity > 0)
        elif filters.in_stock is False:
            statement = statement.where(Inventory.quantity <= 0)

        statement = statement.order_by(Product.name).limit(filters.limit).offset(filters.offset)
        return self._db.execute(statement).all()

    def get_stock(self, product_id: int) -> Row[tuple[Inventory, Product]] | None:
        """Regresa las existencias de un producto con sus datos.

        Args:
            product_id: Id del producto.
        """
        statement = self._stock_query().where(Inventory.product_id == product_id)
        return self._db.execute(statement).first()

    def list_movements(
        self, filters: MovementFilters
    ) -> Sequence[Row[tuple[InventoryMovement, Product]]]:
        """Regresa movimientos con su producto, los más recientes primero.

        Args:
            filters: Producto, tipo, usuario, rango de fechas y paginación.
        """
        statement = select(InventoryMovement, Product).join(
            Product, Product.id == InventoryMovement.product_id
        )
        if filters.product_id is not None:
            statement = statement.where(InventoryMovement.product_id == filters.product_id)
        if filters.type is not None:
            statement = statement.where(InventoryMovement.type == filters.type)
        if filters.user_id is not None:
            statement = statement.where(InventoryMovement.user_id == filters.user_id)
        if filters.start_date is not None:
            start = datetime.combine(filters.start_date, time.min)
            statement = statement.where(InventoryMovement.created_at >= start)
        if filters.end_date is not None:
            # Hasta el inicio del día siguiente para incluir todo end_date
            end = datetime.combine(filters.end_date + timedelta(days=1), time.min)
            statement = statement.where(InventoryMovement.created_at < end)

        statement = (
            statement.order_by(InventoryMovement.id.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        return self._db.execute(statement).all()
