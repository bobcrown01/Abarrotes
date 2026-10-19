"""Hash y verificación de contraseñas con bcrypt.

Se usa ``bcrypt`` directamente: ``passlib`` ya no se mantiene y depende del
módulo ``crypt``, que Python 3.13 eliminó. Los hashes existentes (``$2b$``)
siguen siendo compatibles.
"""

import bcrypt


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña.

    Args:
        password: Contraseña en texto plano (máximo 72 bytes).

    Returns:
        Hash listo para guardar en ``users.password_hash``.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña contra su hash en tiempo constante.

    Args:
        password: Contraseña en texto plano.
        password_hash: Hash guardado.

    Returns:
        ``True`` si coinciden.
    """
    return bcrypt.checkpw(password.encode(), password_hash.encode())
