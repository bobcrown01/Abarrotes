"""Tipos de Pydantic reutilizados por varios esquemas."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

# Los Decimal se envían al frontend como número JSON, no como texto
_as_json_number = PlainSerializer(float, return_type=float, when_used="json")

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2), _as_json_number]
"""Importe de entrada en pesos: no negativo y con máximo dos decimales."""

PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2), _as_json_number]
"""Importe de entrada mayor que cero."""

Quantity = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=3), _as_json_number]
"""Cantidad de entrada (piezas o kg) con hasta tres decimales."""

DecimalOut = Annotated[Decimal, _as_json_number]
"""Decimal de salida sin restricciones (p. ej. existencias que pueden quedar negativas)."""


class DateRangeFilters(BaseModel):
    """Rango de fechas para consultas, compartido por ventas y reportes.

    ``start`` y ``end`` son instantes, no días: el navegador conoce la zona
    horaria de la tienda y manda los límites de "hoy" ya convertidos.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    start: datetime | None = None
    end: datetime | None = None

    @field_validator("start", "end")
    @classmethod
    def to_naive_utc(cls, value: datetime | None) -> datetime | None:
        """Pasa la fecha a UTC sin zona, que es como la guarda la base.

        Args:
            value: Fecha recibida, con o sin zona.

        Returns:
            La misma fecha en UTC sin zona.
        """
        if value is None or value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    @model_validator(mode="after")
    def date_range_is_valid(self) -> Self:
        """Verifica que el rango de fechas no esté invertido.

        Returns:
            Los mismos filtros si son válidos.

        Raises:
            ValueError: Si ``start`` es posterior a ``end``.
        """
        if self.start and self.end and self.start > self.end:
            raise ValueError("La fecha inicial no puede ser posterior a la final")
        return self
