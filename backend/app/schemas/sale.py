"""Esquemas Pydantic de ventas, partidas y pagos."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import DecimalOut, Money, PositiveMoney, Quantity

PaymentMethod = Literal[
    "efectivo",
    "debito",
    "credito",
    "transferencia",
    "monedero",
    "venta_credito",
    "link_pago",
]


class SaleCreate(BaseModel):
    """Datos para abrir una venta nueva (queda en estado ``pendiente``)."""

    model_config = ConfigDict(extra="forbid")

    customer_id: int | None = Field(default=None, gt=0)
    user_id: int = Field(gt=0)


class SaleItemCreate(BaseModel):
    """Partida a agregar a una venta.

    El precio **no** se recibe: se toma del catálogo para que el cliente no
    pueda fijar su propio precio.
    """

    model_config = ConfigDict(extra="forbid")

    sale_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    qty: Quantity = Field(gt=0)
    discount: Money = Field(default=0)


class PaymentCreate(BaseModel):
    """Pago a registrar en una venta.

    El cambio lo calcula el servidor a partir de ``received``.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sale_id: int = Field(gt=0)
    method: PaymentMethod
    amount: PositiveMoney
    received: Money | None = None
    reference: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def received_covers_amount(self) -> "PaymentCreate":
        """Verifica que lo recibido alcance para el importe del pago.

        Returns:
            El mismo pago si es válido.

        Raises:
            ValueError: Si ``received`` es menor que ``amount``.
        """
        if self.received is not None and self.received < self.amount:
            raise ValueError("Lo recibido no puede ser menor que el importe del pago")
        return self


class SaleItemOut(BaseModel):
    """Partida tal como la devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    qty: DecimalOut
    price: DecimalOut
    discount: DecimalOut
    subtotal: DecimalOut


class PaymentOut(BaseModel):
    """Pago tal como lo devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    method: str
    amount: DecimalOut
    received: DecimalOut | None
    change: DecimalOut | None
    reference: str | None
    created_at: datetime


class SaleOut(BaseModel):
    """Venta completa con partidas, pagos y saldo pendiente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str | None
    status: str
    customer_id: int | None
    user_id: int | None
    subtotal: DecimalOut
    discount: DecimalOut
    total: DecimalOut
    amount_paid: DecimalOut
    created_at: datetime
    items: list[SaleItemOut]
    payments: list[PaymentOut]


class SaleSummaryOut(BaseModel):
    """Venta sin detalle, para listados."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str | None
    status: str
    customer_id: int | None
    user_id: int | None
    total: DecimalOut
    created_at: datetime
