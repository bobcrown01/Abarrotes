"""Excepciones de dominio y su traducción a respuestas HTTP.

Los servicios lanzan estas excepciones sin saber nada de HTTP; el manejador
registrado en :func:`register_exception_handlers` las convierte en JSON con
el mismo formato ``{"detail": ...}`` que usa FastAPI.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Error base de la aplicación.

    Attributes:
        status_code: Código HTTP con el que se responde.
        detail: Mensaje legible para el usuario final.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str) -> None:
        """Crea el error.

        Args:
            detail: Mensaje legible para el usuario final.
        """
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    """El recurso solicitado no existe."""

    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    """La operación choca con datos existentes (p. ej. un valor duplicado)."""

    status_code = status.HTTP_409_CONFLICT


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convierte un :class:`AppError` en una respuesta JSON y lo registra."""
    logger.info(
        "%s en %s %s: %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores de errores de dominio en la aplicación.

    Args:
        app: Aplicación FastAPI.
    """
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
