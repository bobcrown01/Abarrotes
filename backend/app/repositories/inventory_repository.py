"""Acceso a datos de existencias y movimientos de inventario."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement


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
