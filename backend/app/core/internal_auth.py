"""Token para las consultas que el bot de Telegram hace a la propia API.

Se genera al iniciar el proceso y nunca sale de la memoria, así que no hay que
configurarlo ni se puede filtrar en un archivo ``.env``.
"""

import secrets

INTERNAL_TOKEN_HEADER = "X-Internal-Token"  # noqa: S105 (es el nombre del encabezado, no una clave)

_token = secrets.token_urlsafe(32)


def internal_headers() -> dict[str, str]:
    """Regresa los encabezados que identifican una consulta interna."""
    return {INTERNAL_TOKEN_HEADER: _token}


def is_internal_token(candidate: str) -> bool:
    """Compara en tiempo constante el token recibido contra el del proceso.

    Args:
        candidate: Valor del encabezado recibido.

    Returns:
        ``True`` si coincide.
    """
    return secrets.compare_digest(candidate, _token)
