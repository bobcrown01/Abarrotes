"""Pruebas de integración de usuarios y del hash de contraseñas."""

import pytest

from app.models.user import User
from app.utils.security import hash_password, verify_password


def test_create_user_stores_only_hash(db_client, db_session):
    response = db_client.post(
        "/api/users", json={"username": "maria", "password": "contraseña1", "role_id": 1}
    )

    assert response.status_code == 201
    body = response.json()
    assert "password" not in body and "password_hash" not in body

    stored = db_session.get(User, body["id"])
    assert stored.password_hash != "contraseña1"
    assert verify_password("contraseña1", stored.password_hash)


def test_duplicate_username_returns_409(db_client):
    response = db_client.post(
        "/api/users", json={"username": "caja1", "password": "otraclave1", "role_id": 1}
    )

    assert response.status_code == 409


def test_unknown_role_returns_400(db_client):
    response = db_client.post(
        "/api/users", json={"username": "pedro", "password": "otraclave1", "role_id": 99}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "El rol no existe"


@pytest.mark.parametrize(
    "changes",
    [
        {"password": "corta"},
        {"password": "ñ" * 37},  # 74 bytes: bcrypt la truncaría
        {"username": "ab"},
        {"username": "con espacio"},
    ],
)
def test_invalid_user_returns_422(db_client, changes):
    payload = {"username": "valido", "password": "contraseña1", "role_id": 1, **changes}

    assert db_client.post("/api/users", json=payload).status_code == 422


def test_list_users_hides_hashes(db_client):
    users = db_client.get("/api/users").json()

    assert [u["username"] for u in users] == ["caja1"]
    assert "password_hash" not in users[0]


def test_hash_is_salted_and_verifiable():
    first, second = hash_password("clave12345"), hash_password("clave12345")

    assert first != second
    assert verify_password("clave12345", first)
    assert not verify_password("otra", first)
