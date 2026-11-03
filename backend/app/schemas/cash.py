"""Esquemas Pydantic de apertura y corte de caja."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DecimalOut, Money


class CashOpen(BaseModel):
    """Datos para abrir la caja."""

    model_config = ConfigDict(extra="forbid")

    opening_amount: Money


class CashClose(BaseModel):
    """Datos del corte: lo que se contó físicamente en la caja."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    counted_amount: Money
    notes: str | None = Field(default=None, max_length=200)


class MethodTotalOut(BaseModel):
    """Importe cobrado con un método de pago."""

    method: str
    amount: DecimalOut


class CashSessionOut(BaseModel):
    """Turno de caja.

    Con la caja abierta, a un cajero no se le envían ``expected_cash``,
    ``sales_total`` ni ``by_method``: cuenta el efectivo sin saber cuánto debería
    haber, para que el conteo sea real.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    opened_by: int | None
    opened_at: datetime
    opening_amount: DecimalOut
    closed_by: int | None
    closed_at: datetime | None
    counted_amount: DecimalOut | None
    expected_cash: DecimalOut | None
    difference: DecimalOut | None
    sales_total: DecimalOut | None
    sales_count: int | None
    by_method: list[MethodTotalOut]
    notes: str | None


class CashCurrentOut(BaseModel):
    """Caja abierta, o ``null`` si está cerrada."""

    session: CashSessionOut | None
