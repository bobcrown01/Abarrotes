"""Pruebas de integración de los endpoints de productos (HTTP ↔ servicio)."""

import pytest


def test_list_categories_sorted_by_name(client):
    response = client.get("/api/categories")

    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Abarrotes", "Bebidas"]


def test_create_product_returns_201_with_product(client, valid_payload):
    response = client.post("/api/products", json=valid_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    # El dinero sale como número JSON, no como texto
    assert body["price"] == 18.5
    assert body["cost"] == 12.0


def test_create_product_duplicate_barcode_returns_409(client, valid_payload):
    client.post("/api/products", json=valid_payload)

    response = client.post("/api/products", json=valid_payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya existe un producto con ese código de barras"


def test_create_product_unknown_category_returns_400(client, valid_payload):
    response = client.post("/api/products", json={**valid_payload, "category_id": 99})

    assert response.status_code == 400
    assert response.json()["detail"] == "La categoría no existe"


@pytest.mark.parametrize(
    "changes",
    [
        {"price": -1},
        {"price": 1.234},  # más de dos decimales
        {"cost": -5},
        {"name": ""},
        {"name": "x" * 151},
        {"unit": "tonelada"},
        {"category_id": 0},
        {"is_admin": True},  # campos desconocidos se rechazan
    ],
)
def test_create_product_invalid_data_returns_422(client, valid_payload, changes):
    response = client.post("/api/products", json={**valid_payload, **changes})

    assert response.status_code == 422


def test_list_products_newest_first(client, valid_payload):
    client.post("/api/products", json=valid_payload)
    client.post("/api/products", json={**valid_payload, "name": "Pepsi", "barcode": None})

    names = [p["name"] for p in client.get("/api/products").json()]

    assert names == ["Pepsi", "Coca Cola 600ml"]


def test_search_products_by_partial_text(client, valid_payload):
    client.post("/api/products", json=valid_payload)

    response = client.get("/api/products/search", params={"q": "coca"})

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.parametrize("params", [{"q": ""}, {"q": "a", "limit": 1000}, {"q": "a", "offset": -1}])
def test_search_products_rejects_bad_params(client, params):
    assert client.get("/api/products/search", params=params).status_code == 422
