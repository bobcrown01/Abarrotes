"""Contrato de transacción que usan los servicios.

Los servicios que escriben en varias tablas (venta + inventario) confirman
todo junto con :meth:`UnitOfWork.commit`. Una ``Session`` de SQLAlchemy ya
cumple este protocolo, así que no hace falta una clase adicional.
"""

from typing import Protocol


class UnitOfWork(Protocol):
    """Transacción que se confirma o se revierte como un todo."""

    def commit(self) -> None:
        """Confirma los cambios pendientes."""
        ...

    def rollback(self) -> None:
        """Descarta los cambios pendientes."""
        ...
