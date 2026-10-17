"""Esquemas Pydantic de entrada y salida para productos y categorías."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import Money

Unit = Literal["pieza", "kg", "litro", "paquete", "caja"]


class ProductCreate(BaseModel):
    """Datos para dar de alta un producto."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    barcode: str | None = Field(default=None, max_length=50)
    sku: str | None = Field(default=None, max_length=50)
    category_id: int = Field(gt=0)
    price: Money
    cost: Money | None = None
    unit: Unit = "pieza"
    is_active: bool = True

    @field_validator("barcode", "sku", mode="before")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        """Guarda los campos opcionales vacíos como ``NULL``.

        Args:
            value: Valor recibido en la petición.

        Returns:
            ``None`` si el texto está vacío; si no, el valor original.
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ProductOut(BaseModel):
    """Producto tal como lo devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    barcode: str | None
    sku: str | None
    category_id: int
    price: Money
    cost: Money | None
    unit: str | None
    is_active: bool


class CategoryOut(BaseModel):
    """Categoría tal como la devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
