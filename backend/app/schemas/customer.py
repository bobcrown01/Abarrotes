"""Esquemas Pydantic de clientes y abonos."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import DecimalOut, Money, PositiveMoney

# Con qué se puede abonar: no incluye fiado, porque no se paga deuda con más deuda
AbonoMethod = Literal["efectivo", "debito", "credito", "transferencia"]


class CustomerCreate(BaseModel):
    """Datos para dar de alta un cliente."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    credit_limit: Money = 0


class CustomerUpdate(BaseModel):
    """Cambios parciales a un cliente: solo se tocan los campos enviados."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    credit_limit: Money | None = None

    @model_validator(mode="after")
    def required_fields_not_null(self) -> "CustomerUpdate":
        """Rechaza ``null`` explícito en el nombre y el límite.

        Returns:
            El mismo cambio si es válido.

        Raises:
            ValueError: Si se manda ``null`` en un campo obligatorio.
        """
        for name in ("name", "credit_limit"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"El campo {name} no puede ser nulo")
        return self


class CustomerOut(BaseModel):
    """Cliente con lo que debe y lo que aún se le puede fiar."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str | None
    credit_limit: DecimalOut
    balance: DecimalOut


class CustomerPaymentCreate(BaseModel):
    """Abono de un cliente a su cuenta."""

    model_config = ConfigDict(extra="forbid")

    amount: PositiveMoney
    method: AbonoMethod = "efectivo"


class CustomerPaymentOut(BaseModel):
    """Abono registrado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    amount: DecimalOut
    method: str
    user_id: int | None
    created_at: datetime
