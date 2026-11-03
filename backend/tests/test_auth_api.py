"""Pruebas del login, las sesiones y los permisos por rol."""

import pytest

from app.core.internal_auth import internal_headers
from app.models.role import Role
from app.models.sale import Sale, SaleStatus
from app.models.user import User
from app.models.user_session import UserSession
from app.services.auth_service import MAX_FAILED_ATTEMPTS, login_throttle
from app.utils.security import hash_password


@pytest.fixture
def roles(db_session):
    """Agrega un administrador y un cajero con PIN (el rol 1 ya es cajero)."""
    db_session.add_all(
        [
            Role(id=2, name="admin"),
            User(id=2, username="dueno", password_hash=hash_password("clave-larga-1"), role_id=2),
            User(id=3, username="caja2", password_hash=hash_password("1234"), role_id=1),
        ]
    )
    db_session.commit()
    for name in ("dueno", "caja2", "nadie"):
        login_throttle.reset(name)


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


# ---------- Rutas protegidas ----------


@pytest.mark.parametrize(
    "path",
    ["/api/products", "/api/categories", "/api/inventory", "/api/sales", "/api/users"],
)
def test_sin_sesion_responde_401(anon_client, path):
    assert anon_client.get(path).status_code == 401


def test_salud_no_requiere_sesion(anon_client):
    assert anon_client.get("/api/health").status_code == 200


# ---------- Login ----------


def test_login_correcto_abre_sesion_con_cookie_protegida(anon_client, roles):
    response = login(anon_client, "dueno", "clave-larga-1")

    assert response.status_code == 200
    assert response.json() == {"id": 2, "username": "dueno", "role": "admin", "can_manage": True}
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert anon_client.get("/api/auth/me").json()["username"] == "dueno"


def test_el_token_no_se_guarda_en_claro(anon_client, db_session, roles):
    token = login(anon_client, "dueno", "clave-larga-1").cookies["pos_session"]

    stored = db_session.query(UserSession).one()
    assert stored.token_hash != token


def test_cajero_entra_con_pin(anon_client, roles):
    response = login(anon_client, "caja2", "1234")

    assert response.status_code == 200
    assert response.json()["can_manage"] is False


@pytest.mark.parametrize(
    ("username", "password"), [("dueno", "incorrecta"), ("nadie", "incorrecta")]
)
def test_credenciales_malas_dan_el_mismo_mensaje(anon_client, roles, username, password):
    response = login(anon_client, username, password)

    assert response.status_code == 401
    assert response.json()["detail"] == "Usuario o contraseña incorrectos"


def test_usuario_inactivo_no_entra(anon_client, db_session, roles):
    db_session.get(User, 3).is_active = False
    db_session.commit()

    assert login(anon_client, "caja2", "1234").status_code == 401


def test_bloquea_tras_varios_intentos_fallidos(anon_client, roles):
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert login(anon_client, "caja2", "0000").status_code == 401

    # Ya bloqueado, ni la clave correcta entra
    assert login(anon_client, "caja2", "1234").status_code == 429


def test_logout_invalida_la_sesion_en_el_servidor(anon_client, roles):
    token = login(anon_client, "dueno", "clave-larga-1").cookies["pos_session"]

    assert anon_client.post("/api/auth/logout").status_code == 204

    anon_client.cookies.set("pos_session", token)
    assert anon_client.get("/api/auth/me").status_code == 401


def test_desactivar_usuario_corta_su_sesion(anon_client, db_session, roles):
    login(anon_client, "caja2", "1234")
    db_session.get(User, 3).is_active = False
    db_session.commit()

    assert anon_client.get("/api/auth/me").status_code == 401


# ---------- Primer administrador ----------


def test_setup_solo_funciona_sin_administrador(anon_client, db_session):
    db_session.add(Role(id=2, name="admin"))
    db_session.commit()
    payload = {"username": "dueno", "password": "clave-larga-1"}

    assert anon_client.get("/api/auth/status").json() == {"needs_setup": True}
    assert anon_client.post("/api/auth/setup", json=payload).status_code == 201
    assert anon_client.get("/api/auth/me").json()["role"] == "admin"

    assert anon_client.get("/api/auth/status").json() == {"needs_setup": False}
    other = {"username": "intruso", "password": "clave-larga-2"}
    assert anon_client.post("/api/auth/setup", json=other).status_code == 409


def test_setup_no_acepta_pin(anon_client, db_session):
    db_session.add(Role(id=2, name="admin"))
    db_session.commit()
    payload = {"username": "dueno", "password": "1234"}

    assert anon_client.post("/api/auth/setup", json=payload).status_code == 422


# ---------- Permisos por rol ----------


def test_cajero_no_puede_cambiar_catalogo_ni_inventario(anon_client, roles):
    login(anon_client, "caja2", "1234")

    assert anon_client.get("/api/products").status_code == 200
    assert anon_client.delete("/api/products/1").status_code == 403
    assert anon_client.put("/api/products/1", json={"price": 1}).status_code == 403
    movement = {"product_id": 1, "type": "ajuste", "quantity": 0}
    assert anon_client.post("/api/inventory/movements", json=movement).status_code == 403
    new_user = {"username": "otro", "password": "clave-larga-1", "role_id": 2}
    assert anon_client.post("/api/users", json=new_user).status_code == 403


def test_la_venta_queda_a_nombre_de_quien_tiene_la_sesion(anon_client, roles):
    login(anon_client, "caja2", "1234")

    # Aunque pida vender a nombre de otro usuario
    sale = anon_client.post("/api/sales", json={"user_id": 2}).json()

    assert sale["user_id"] == 3


def test_cajero_cancela_pendiente_pero_no_pagada(anon_client, db_session, roles):
    login(anon_client, "caja2", "1234")
    pending = anon_client.post("/api/sales", json={}).json()
    paid = Sale(user_id=3, status=SaleStatus.PAID, subtotal=1, discount=0, total=1)
    db_session.add(paid)
    db_session.commit()

    assert anon_client.post(f"/api/sales/{pending['id']}/cancel").status_code == 200
    assert anon_client.post(f"/api/sales/{paid.id}/cancel").status_code == 403


def test_administrador_cancela_venta_pagada(anon_client, db_session, roles):
    login(anon_client, "dueno", "clave-larga-1")
    paid = Sale(user_id=3, status=SaleStatus.PAID, subtotal=1, discount=0, total=1)
    db_session.add(paid)
    db_session.commit()

    assert anon_client.post(f"/api/sales/{paid.id}/cancel").status_code == 200


def test_pin_solo_para_cajeros(anon_client, roles):
    login(anon_client, "dueno", "clave-larga-1")

    pin_admin = {"username": "otro", "password": "1234", "role_id": 2}
    assert anon_client.post("/api/users", json=pin_admin).status_code == 400
    pin_cajero = {"username": "otro", "password": "1234", "role_id": 1}
    assert anon_client.post("/api/users", json=pin_cajero).status_code == 201


# ---------- Bot de Telegram ----------


def test_token_interno_solo_sirve_para_leer(anon_client):
    headers = internal_headers()

    assert anon_client.get("/api/products", headers=headers).status_code == 200
    assert anon_client.delete("/api/products/1", headers=headers).status_code == 401


def test_token_interno_falso_no_entra(anon_client):
    response = anon_client.get("/api/products", headers={"X-Internal-Token": "falso"})

    assert response.status_code == 401
