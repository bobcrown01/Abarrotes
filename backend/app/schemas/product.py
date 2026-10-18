"""Esquemas Pydantic de entrada y salida para productos y categorías."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import Money

Unit = Literal["pieza", "kg", "litro", "paquete", "caja"]

# Reglas de cada campo, compartidas por alta y edición
ProductName = Annotated[str, Field(min_length=1, max_length=150)]
Barcode = Annotated[str, Field(max_length=50)]
Sku = Annotated[str, Field(max_length=50)]
CategoryId = Annotated[int, Field(gt=0)]

# Columnas que no admiten NULL: en una edición se pueden omitir, no mandar vacías
_NOT_NULLABLE = ("name", "category_id", "price", "unit", "is_active")


def _blank_to_none(value: object) -> object:
    """Convierte texto vacío en ``None`` para guardarlo como ``NULL``."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ProductCreate(BaseModel):
    """Datos para dar de alta un producto."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: ProductName
    barcode: Barcode | None = None
    sku: Sku | None = None
    category_id: CategoryId
    price: Money
    cost: Money | None = None
    unit: Unit = "pieza"
    is_active: bool = True

    @field_validator("barcode", "sku", mode="before")
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        """Guarda los campos opcionales vacíos como ``NULL``."""
        return _blank_to_none(value)


class ProductUpdate(BaseModel):
    """Cambios parciales a un producto: solo se tocan los campos enviados."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: ProductName | None = None
    barcode: Barcode | None = None
    sku: Sku | None = None
    category_id: CategoryId | None = None
    price: Money | None = None
    cost: Money | None = None
    unit: Unit | None = None
    is_active: bool | None = None

    @field_validator("barcode", "sku", mode="before")
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        """Permite borrar el código o el SKU mandando texto vacío."""
        return _blank_to_none(value)

    @model_validator(mode="after")
    def required_fields_not_null(self) -> "ProductUpdate":
        """Rechaza ``null`` explícito en campos obligatorios.

        Returns:
            El mismo cambio si es válido.

        Raises:
            ValueError: Si se manda ``null`` en un campo obligatorio.
        """
        nulls = [
            name
            for name in _NOT_NULLABLE
            if name in self.model_fields_set and getattr(self, name) is None
        ]
        if nulls:
            raise ValueError(f"Estos campos no pueden ser nulos: {', '.join(nulls)}")
        return self


class ProductFilters(BaseModel):
    """Filtros de ``GET /products/filter`` (todos opcionales, se combinan con AND)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    search: str | None = Field(default=None, max_length=100)
    category_id: CategoryId | None = None
    active: bool | None = None
    min_price: Money | None = None
    max_price: Money | None = None
    in_stock: bool | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def price_range_is_valid(self) -> "ProductFilters":
        """Verifica que el rango de precios no esté invertido.

        Returns:
            Los mismos filtros si son válidos.

        Raises:
            ValueError: Si ``min_price`` es mayor que ``max_price``.
        """
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price no puede ser mayor que max_price")
        return self


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
