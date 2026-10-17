"""Errores de dominio compartidos entre varios servicios."""

from app.core.exceptions import AppError, NotFoundError


class ProductNotFoundError(NotFoundError):
    """El producto indicado no existe."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Producto no encontrado")


class UserNotFoundError(AppError):
    """El usuario indicado en la petición no existe (400: dato inválido)."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El usuario no existe")
