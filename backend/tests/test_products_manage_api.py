"""Pruebas de integración de consulta, filtros, edición y desactivación de productos.

Usa la base SQLite de ``db_client`` (productos 1, 2 y 3 de conftest).
"""

import pytest


def stock_in(client, product_id, quantity):
    client.post(
        "/api/inventory/movements",
        json={"product_id": product_id, "type": "entrada", "quantity": quantity},
    )


def names(response):
    return [p["name"] for p in response.json()]


# ---------- GET /products/{id} ----------


def test_get_product_by_id(db_client):
    assert db_client.get("/api/products/1").json()["name"] == "Coca Cola 600ml"
    assert db_client.get("/api/products/999").status_code == 404


# ---------- GET /products/filter ----------


@pytest.mark.parametrize(
    "params, expected",
    [
        ({}, ["Coca Cola 600ml", "Descontinuado", "Sabritas"]),
        ({"search": "sab"}, ["Sabritas"]),
        ({"active": "false"}, ["Descontinuado"]),
        ({"min_price": 10, "max_price": 20}, ["Coca Cola 600ml"]),
        ({"category_id": 1, "active": "true"}, ["Coca Cola 600ml", "Sabritas"]),
    ],
)
def test_filter_products(db_client, params, expected):
    response = db_client.get("/api/products/filter", params=params)

    assert response.status_code == 200
    assert names(response) == expected


def test_filter_by_stock_only_counts_products_with_inventory(db_client):
    stock_in(db_client, 1, 5)
    stock_in(db_client, 2, 1)
    db_client.post(
        "/api/inventory/movements", json={"product_id": 2, "type": "ajuste", "quantity": 0}
    )

    assert names(db_client.get("/api/products/filter", params={"in_stock": "true"})) == [
        "Coca Cola 600ml"
    ]
    assert names(db_client.get("/api/products/filter", params={"in_stock": "false"})) == [
        "Sabritas"
    ]


def test_filter_route_is_not_taken_as_product_id(db_client):
    # Antes de reordenar las rutas, "filter" se leía como {product_id}
    assert db_client.get("/api/products/filter").status_code == 200


@pytest.mark.parametrize(
    "params",
    [{"min_price": 20, "max_price": 10}, {"limit": 1000}, {"min_price": -1}, {"color": "rojo"}],
)
def test_filter_rejects_bad_params(db_client, params):
    assert db_client.get("/api/products/filter", params=params).status_code == 422


# ---------- PUT /products/{id} ----------


def test_update_changes_only_sent_fields(db_client):
    response = db_client.put("/api/products/1", json={"price": 19.0})

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 19.0
    assert body["name"] == "Coca Cola 600ml"


def test_update_can_clear_barcode_with_blank(db_client):
    db_client.put("/api/products/1", json={"barcode": "750111"})

    assert db_client.put("/api/products/1", json={"barcode": ""}).json()["barcode"] is None


def test_update_keeps_own_barcode_but_rejects_another_products(db_client):
    db_client.put("/api/products/1", json={"barcode": "750111"})

    assert db_client.put("/api/products/1", json={"barcode": "750111"}).status_code == 200
    response = db_client.put("/api/products/2", json={"barcode": "750111"})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload, status",
    [
        ({"category_id": 99}, 400),
        ({"price": -5}, 422),
        ({"price": None}, 422),
        ({"name": None}, 422),
        ({"unit": "tonelada"}, 422),
        ({"id": 50}, 422),
    ],
)
def test_update_rejects_invalid_changes(db_client, payload, status):
    assert db_client.put("/api/products/1", json=payload).status_code == status


def test_update_unknown_product_returns_404(db_client):
    assert db_client.put("/api/products/999", json={"price": 1}).status_code == 404


# ---------- DELETE /products/{id} ----------


def test_delete_deactivates_instead_of_removing(db_client):
    response = db_client.delete("/api/products/1")

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert db_client.get("/api/products/1").json()["is_active"] is False
    assert db_client.delete("/api/products/999").status_code == 404
