"""Pruebas de integración del ciclo de vida de una venta."""

import pytest
from sqlalchemy import select

from app.models.inventory import Inventory


def open_sale(client):
    response = client.post("/api/sales", json={"user_id": 1})
    assert response.status_code == 201
    return response.json()


def add_item(client, sale_id, product_id=1, qty=2, **extra):
    payload = {"sale_id": sale_id, "product_id": product_id, "qty": qty, **extra}
    return client.post("/api/sales/items", json=payload)


def pay(client, sale_id, amount, **extra):
    payload = {"sale_id": sale_id, "method": "efectivo", "amount": amount, **extra}
    return client.post("/api/sales/payments", json=payload)


def stock(session, product_id=1):
    session.expire_all()
    return session.scalar(select(Inventory.quantity).where(Inventory.product_id == product_id))


@pytest.fixture
def stocked(db_client):
    db_client.post(
        "/api/inventory/movements",
        json={"product_id": 1, "type": "entrada", "quantity": 10},
    )
    return db_client


def test_open_sale_assigns_sequential_folio(db_client):
    first = open_sale(db_client)
    second = open_sale(db_client)

    assert first["folio"] == "V-000001"
    assert second["folio"] == "V-000002"
    assert first["status"] == "pendiente"


def test_open_sale_with_unknown_user_or_customer_returns_400(db_client):
    assert db_client.post("/api/sales", json={"user_id": 999}).status_code == 400
    response = db_client.post("/api/sales", json={"user_id": 1, "customer_id": 999})
    assert response.status_code == 400
    assert response.json()["detail"] == "El cliente no existe"


def test_item_uses_catalog_price_and_updates_totals(db_client):
    sale = open_sale(db_client)

    body = add_item(db_client, sale["id"], qty=2, discount=1).json()

    assert body["items"][0]["price"] == 18.5
    assert body["items"][0]["subtotal"] == 36.0  # 2 × 18.50 − 1
    assert body["total"] == 36.0


def test_client_cannot_send_its_own_price(db_client):
    sale = open_sale(db_client)

    response = add_item(db_client, sale["id"], price=0.01)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "changes, status, detail",
    [
        ({"product_id": 999}, 404, "Producto no encontrado"),
        ({"product_id": 3}, 409, "El producto está inactivo"),
        ({"discount": 100}, 400, "El descuento no puede ser mayor que el importe"),
    ],
)
def test_invalid_items_are_rejected(db_client, changes, status, detail):
    sale = open_sale(db_client)

    response = add_item(db_client, sale["id"], **changes)

    assert response.status_code == status
    assert response.json()["detail"] == detail


def test_payment_computes_change_on_server(db_client):
    sale = open_sale(db_client)
    add_item(db_client, sale["id"], qty=2)  # 37.00

    body = pay(db_client, sale["id"], 37, received=50).json()

    assert body["amount_paid"] == 37.0
    assert body["payments"][0]["change"] == 13.0


def test_payment_cannot_exceed_balance_or_received(db_client):
    sale = open_sale(db_client)
    add_item(db_client, sale["id"], qty=1)  # 18.50

    assert pay(db_client, sale["id"], 20).status_code == 409
    assert pay(db_client, sale["id"], 18.5, received=10).status_code == 422
    assert pay(db_client, sale["id"], 18.5, change=999).status_code == 422


def test_close_requires_items_and_full_payment(db_client):
    sale = open_sale(db_client)
    assert db_client.post(f"/api/sales/{sale['id']}/close").json()["detail"] == (
        "La venta no tiene productos"
    )

    add_item(db_client, sale["id"], qty=2)  # 37.00
    pay(db_client, sale["id"], 30)

    response = db_client.post(f"/api/sales/{sale['id']}/close")
    assert response.status_code == 409
    assert response.json()["detail"] == "La venta no está completamente pagada"


def test_close_marks_paid_and_deducts_stock(stocked, db_session):
    sale = open_sale(stocked)
    add_item(stocked, sale["id"], qty=3)
    pay(stocked, sale["id"], 55.5)

    response = stocked.post(f"/api/sales/{sale['id']}/close")

    assert response.status_code == 200
    assert response.json()["status"] == "pagada"
    assert stock(db_session) == 7


def test_closed_sale_rejects_changes(stocked):
    sale = open_sale(stocked)
    add_item(stocked, sale["id"], qty=1)
    pay(stocked, sale["id"], 18.5)
    stocked.post(f"/api/sales/{sale['id']}/close")

    response = add_item(stocked, sale["id"])

    assert response.status_code == 409
    assert response.json()["detail"] == "La venta ya está pagada"


def test_cancel_pending_sale_does_not_touch_stock(stocked, db_session):
    sale = open_sale(stocked)
    add_item(stocked, sale["id"], qty=4)

    response = stocked.post(f"/api/sales/{sale['id']}/cancel")

    assert response.json()["status"] == "cancelada"
    assert stock(db_session) == 10  # antes sumaba 4 aunque nunca se habían descontado


def test_cancel_paid_sale_restores_stock_once(stocked, db_session):
    sale = open_sale(stocked)
    add_item(stocked, sale["id"], qty=4)
    pay(stocked, sale["id"], 74)
    stocked.post(f"/api/sales/{sale['id']}/close")
    assert stock(db_session) == 6

    stocked.post(f"/api/sales/{sale['id']}/cancel")
    second = stocked.post(f"/api/sales/{sale['id']}/cancel")

    assert stock(db_session) == 10
    assert second.status_code == 409


def test_products_without_inventory_can_be_sold(db_client):
    sale = open_sale(db_client)
    add_item(db_client, sale["id"], product_id=2, qty=1)
    pay(db_client, sale["id"], 21)

    assert db_client.post(f"/api/sales/{sale['id']}/close").status_code == 200


def test_get_and_list_sales(db_client):
    sale = open_sale(db_client)

    assert db_client.get(f"/api/sales/{sale['id']}").json()["folio"] == "V-000001"
    assert db_client.get("/api/sales/999").status_code == 404
    assert [s["id"] for s in db_client.get("/api/sales").json()] == [sale["id"]]
    assert db_client.get("/api/sales", params={"limit": 1000}).status_code == 422
