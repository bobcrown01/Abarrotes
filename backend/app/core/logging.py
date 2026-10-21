"""Configuración de logging del backend."""

import logging


def configure_logging(level: str) -> None:
    """Configura el formato y el nivel de los logs a la salida estándar.

    Docker recoge la salida estándar, así que no se escriben archivos
    (ahorra escrituras en la tarjeta SD de la Raspberry Pi).

    Args:
        level: Nivel mínimo, p. ej. ``"INFO"`` o ``"DEBUG"``.
    """
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
