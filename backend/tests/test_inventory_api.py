"""Pruebas de integración de movimientos de inventario."""

import pytest


def move(client, type_, quantity, product_id=1, **extra):
    payload = {"product_id": product_id, "type": type_, "quantity": quantity, **extra}
    return client.post("/api/inventory/movements", json=payload)


def test_entry_creates_stock_and_returns_201(db_client):
    response = move(db_client, "entrada", 20, reason="Compra proveedor", user_id=1)

    assert response.status_code == 201
    body = response.json()
    assert body["new_quantity"] == 20
    assert body["type"] == "entrada"
    assert body["created_at"]


def test_exit_subtracts_and_adjustment_sets(db_client):
    move(db_client, "entrada", 20)

    assert move(db_client, "salida", 2).json()["new_quantity"] == 18
    assert move(db_client, "ajuste", 50).json()["new_quantity"] == 50
    assert move(db_client, "ajuste", 0).json()["new_quantity"] == 0


def test_exit_beyond_stock_returns_409_and_keeps_stock(db_client):
    move(db_client, "entrada", 5)

    response = move(db_client, "salida", 6)

    assert response.status_code == 409
    assert response.json()["detail"] == "Inventario insuficiente"
    assert move(db_client, "entrada", 1).json()["new_quantity"] == 6


def test_unknown_product_returns_404(db_client):
    assert move(db_client, "entrada", 1, product_id=999).status_code == 404


def test_unknown_user_returns_400(db_client):
    response = move(db_client, "entrada", 1, user_id=999)

    assert response.status_code == 400
    assert response.json()["detail"] == "El usuario no existe"


@pytest.mark.parametrize(
    "type_, quantity",
    [("robo", 1), ("entrada", 0), ("salida", 0), ("entrada", -3), ("entrada", 1.2345)],
)
def test_invalid_movement_returns_422(db_client, type_, quantity):
    assert move(db_client, type_, quantity).status_code == 422
