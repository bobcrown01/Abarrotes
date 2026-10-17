"""Esquemas Pydantic de movimientos de inventario."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import DecimalOut, Quantity

MovementType = Literal["entrada", "salida", "ajuste"]


class InventoryMovementCreate(BaseModel):
    """Movimiento manual de inventario.

    ``entrada`` y ``salida`` suman o restan ``quantity``; ``ajuste`` fija las
    existencias en ``quantity`` (resultado de un conteo físico).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product_id: int = Field(gt=0)
    type: MovementType
    quantity: Quantity
    reason: str | None = Field(default=None, max_length=100)
    user_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def quantity_positive_unless_adjustment(self) -> "InventoryMovementCreate":
        """Solo un ajuste puede ser cero (conteo físico sin existencias).

        Returns:
            El mismo movimiento si es válido.

        Raises:
            ValueError: Si una entrada o salida trae cantidad cero.
        """
        if self.type != "ajuste" and self.quantity == 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        return self


class InventoryMovementOut(BaseModel):
    """Movimiento registrado junto con las existencias resultantes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    type: str
    quantity: DecimalOut
    reason: str | None
    user_id: int | None
    created_at: datetime
    new_quantity: DecimalOut
