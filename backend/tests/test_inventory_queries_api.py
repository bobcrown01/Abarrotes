"""Pruebas de integración de las consultas de inventario."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def with_movements(db_client):
    for payload in [
        {"product_id": 1, "type": "entrada", "quantity": 10, "user_id": 1},
        {"product_id": 1, "type": "salida", "quantity": 3, "reason": "Merma"},
        {"product_id": 2, "type": "entrada", "quantity": 4},
        {"product_id": 2, "type": "salida", "quantity": 4},
    ]:
        assert db_client.post("/api/inventory/movements", json=payload).status_code == 201
    return db_client


def test_movements_route_is_not_taken_as_product_id(with_movements):
    # Antes de reordenar las rutas respondía 422 ("movements" no es un número)
    response = with_movements.get("/api/inventory/movements")

    assert response.status_code == 200
    assert len(response.json()) == 4


def test_list_stock_with_product_data(with_movements):
    stock = with_movements.get("/api/inventory").json()

    assert stock == [
        {
            "product_id": 1,
            "product_name": "Coca Cola 600ml",
            "quantity": 7.0,
            "min_stock": 0.0,
            "max_stock": None,
            "unit": "pieza",
            "is_active": True,
        },
        {
            "product_id": 2,
            "product_name": "Sabritas",
            "quantity": 0.0,
            "min_stock": 0.0,
            "max_stock": None,
            "unit": "pieza",
            "is_active": True,
        },
    ]


@pytest.mark.parametrize("in_stock, expected", [("true", [1]), ("false", [2])])
def test_list_stock_by_availability(with_movements, in_stock, expected):
    stock = with_movements.get("/api/inventory", params={"in_stock": in_stock}).json()

    assert [s["product_id"] for s in stock] == expected


def test_get_stock_by_product(with_movements):
    assert with_movements.get("/api/inventory/1").json()["quantity"] == 7.0
    response = with_movements.get("/api/inventory/3")
    assert response.status_code == 404
    assert response.json()["detail"] == "Inventario no encontrado para este producto"


@pytest.mark.parametrize(
    "params, expected_count",
    [
        ({"product_id": 1}, 2),
        ({"type": "salida"}, 2),
        ({"user_id": 1}, 1),
        ({"limit": 1}, 1),
    ],
)
def test_filter_movements(with_movements, params, expected_count):
    movements = with_movements.get("/api/inventory/movements", params=params).json()

    assert len(movements) == expected_count


def test_movement_date_range_includes_whole_end_day(with_movements):
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    same_day = with_movements.get(
        "/api/inventory/movements", params={"start_date": today, "end_date": today}
    ).json()
    future = with_movements.get("/api/inventory/movements", params={"start_date": tomorrow}).json()

    assert len(same_day) == 4
    assert future == []


def test_movements_are_newest_first_with_product_name(with_movements):
    latest = with_movements.get("/api/inventory/movements").json()[0]

    assert latest["product_name"] == "Sabritas"
    assert latest["type"] == "salida"
    assert set(latest) == {
        "movement_id",
        "product_id",
        "product_name",
        "type",
        "quantity",
        "reason",
        "created_at",
        "user_id",
    }


@pytest.mark.parametrize(
    "params",
    [
        {"type": "robo"},
        {"start_date": "2026-10-18", "end_date": "2026-10-01"},
        {"start_date": "ayer"},
        {"limit": 10000},
    ],
)
def test_filter_movements_rejects_bad_params(db_client, params):
    assert db_client.get("/api/inventory/movements", params=params).status_code == 422


def test_product_movements(with_movements):
    movements = with_movements.get("/api/inventory/1/movements").json()

    assert [m["type"] for m in movements] == ["salida", "entrada"]
    assert movements[0]["reason"] == "Merma"
    assert with_movements.get("/api/inventory/999/movements").status_code == 404
