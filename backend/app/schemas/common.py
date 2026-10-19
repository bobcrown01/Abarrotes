"""Tipos de Pydantic reutilizados por varios esquemas."""

from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

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
