"""Esquemas Pydantic de existencias y movimientos de inventario."""

from datetime import date, datetime
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


# ---------- Consultas ----------


class StockFilters(BaseModel):
    """Filtros de ``GET /inventory``."""

    model_config = ConfigDict(extra="forbid")

    category_id: int | None = Field(default=None, gt=0)
    in_stock: bool | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class MovementFilters(BaseModel):
    """Filtros de ``GET /inventory/movements``.

    ``start_date`` y ``end_date`` son fechas (``AAAA-MM-DD``) e incluyen el día
    completo: ``end_date=2026-10-17`` abarca hasta las 23:59:59 de ese día.
    """

    model_config = ConfigDict(extra="forbid")

    product_id: int | None = Field(default=None, gt=0)
    type: MovementType | None = None
    user_id: int | None = Field(default=None, gt=0)
    start_date: date | None = None
    end_date: date | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def date_range_is_valid(self) -> "MovementFilters":
        """Verifica que el rango de fechas no esté invertido.

        Returns:
            Los mismos filtros si son válidos.

        Raises:
            ValueError: Si ``start_date`` es posterior a ``end_date``.
        """
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date no puede ser posterior a end_date")
        return self


class StockOut(BaseModel):
    """Existencias de un producto."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: DecimalOut
    min_stock: DecimalOut
    max_stock: DecimalOut | None
    unit: str | None
    is_active: bool


class ProductMovementOut(BaseModel):
    """Movimiento en el historial de un producto."""

    model_config = ConfigDict(from_attributes=True)

    movement_id: int
    type: str
    quantity: DecimalOut
    reason: str | None
    created_at: datetime
    user_id: int | None


class MovementListOut(ProductMovementOut):
    """Movimiento en el historial general (incluye el producto)."""

    product_id: int
    product_name: str
