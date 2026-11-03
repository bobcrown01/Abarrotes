"""Pruebas de la apertura, las ventas y el corte de caja."""

from decimal import Decimal

import pytest

from app.models.cash_session import CashSession
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import login_throttle
from app.utils.security import hash_password


def sell(client, method="efectivo", qty=1):
    """Hace una venta completa de Coca Cola ($18.50 c/u) y regresa la venta."""
    sale = client.post("/api/sales", json={}).json()
    current = client.post(
        "/api/sales/items", json={"sale_id": sale["id"], "product_id": 1, "qty": qty}
    ).json()
    client.post(
        "/api/sales/payments",
        json={
            "sale_id": sale["id"],
            "method": method,
            "amount": current["total"],
            "received": current["total"] if method == "efectivo" else None,
        },
    )
    return client.post(f"/api/sales/{sale['id']}/close").json()


def test_resumen_cuenta_ventas_por_metodo(db_client):
    sell(db_client, "efectivo", 2)  # $37.00
    sell(db_client, "debito")  # $18.50

    session = db_client.get("/api/cash/current").json()["session"]

    assert session["opening_amount"] == 100
    assert session["expected_cash"] == 137  # Fondo + efectivo; la tarjeta no entra a la caja
    assert session["sales_total"] == 55.5
    assert session["sales_count"] == 2
    assert session["by_method"] == [
        {"method": "debito", "amount": 18.5},
        {"method": "efectivo", "amount": 37.0},
    ]


def test_venta_cancelada_no_cuenta_en_el_corte(db_client):
    sale = sell(db_client)
    db_client.post(f"/api/sales/{sale['id']}/cancel")

    session = db_client.get("/api/cash/current").json()["session"]

    assert session["expected_cash"] == 100
    assert session["sales_count"] == 0


def test_corte_calcula_diferencia_y_cierra_la_caja(db_client):
    sell(db_client)  # Esperado: 100 + 18.50

    response = db_client.post(
        "/api/cash/close", json={"counted_amount": 110, "notes": "  Faltante  "}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["expected_cash"] == 118.5
    assert body["counted_amount"] == 110
    assert body["difference"] == -8.5
    assert body["notes"] == "Faltante"
    assert db_client.get("/api/cash/current").json() == {"session": None}


def test_historial_conserva_la_foto_aunque_luego_se_cancele_una_venta(db_client):
    sale = sell(db_client)
    db_client.post("/api/cash/close", json={"counted_amount": 118.5})
    assert db_client.post("/api/cash/open", json={"opening_amount": 50}).status_code == 201
    db_client.post(f"/api/sales/{sale['id']}/cancel")

    history = db_client.get("/api/cash/sessions").json()

    assert len(history) == 1
    assert history[0]["expected_cash"] == 118.5
    assert history[0]["difference"] == 0
    assert history[0]["closed_by"] == 1


def test_no_se_abre_dos_veces(db_client):
    response = db_client.post("/api/cash/open", json={"opening_amount": 10})

    assert response.status_code == 409
    assert response.json()["detail"] == "La caja ya está abierta"


def test_la_base_impide_dos_cajas_abiertas(db_session):
    db_session.add(CashSession(opened_by=1, opening_amount=Decimal("1")))

    with pytest.raises(Exception, match="UNIQUE"):
        db_session.commit()
    db_session.rollback()


def test_corte_sin_caja_abierta_responde_409(db_client):
    db_client.post("/api/cash/close", json={"counted_amount": 100})

    assert db_client.post("/api/cash/close", json={"counted_amount": 100}).status_code == 409


def test_no_se_vende_con_la_caja_cerrada(db_client):
    # Una venta ya empezada tampoco se puede cobrar si cierran la caja a medias
    sale = db_client.post("/api/sales", json={}).json()
    current = db_client.post(
        "/api/sales/items", json={"sale_id": sale["id"], "product_id": 1, "qty": 1}
    ).json()
    db_client.post("/api/cash/close", json={"counted_amount": 100})

    payment = {"sale_id": sale["id"], "method": "debito", "amount": current["total"]}
    assert db_client.post("/api/sales/payments", json=payment).status_code == 409
    assert db_client.post("/api/sales", json={}).status_code == 409


@pytest.mark.parametrize(
    "path, payload",
    [
        ("/api/cash/open", {"opening_amount": -1}),
        ("/api/cash/close", {"counted_amount": -1}),
        ("/api/cash/close", {"counted_amount": 1, "notes": "x" * 201}),
    ],
)
def test_datos_invalidos_responden_422(db_client, path, payload):
    assert db_client.post(path, json=payload).status_code == 422


def test_cajero_cuenta_a_ciegas_pero_ve_el_resultado(anon_client, db_session):
    db_session.add_all(
        [User(id=3, username="caja2", password_hash=hash_password("1234"), role_id=1)]
    )
    db_session.commit()
    login_throttle.reset("caja2")
    anon_client.post("/api/auth/login", json={"username": "caja2", "password": "1234"})

    session = anon_client.get("/api/cash/current").json()["session"]
    assert session["opening_amount"] == 100
    assert session["expected_cash"] is None
    assert session["by_method"] == []

    # El historial es solo de administración
    assert anon_client.get("/api/cash/sessions").status_code == 403

    closed = anon_client.post("/api/cash/close", json={"counted_amount": 100}).json()
    assert closed["expected_cash"] == 100
    assert closed["difference"] == 0


def test_supervisor_si_ve_el_esperado(anon_client, db_session):
    db_session.add_all(
        [
            Role(id=2, name="supervisor"),
            User(id=4, username="super", password_hash=hash_password("clave-larga-1"), role_id=2),
        ]
    )
    db_session.commit()
    login_throttle.reset("super")
    anon_client.post("/api/auth/login", json={"username": "super", "password": "clave-larga-1"})

    assert anon_client.get("/api/cash/current").json()["session"]["expected_cash"] == 100


def test_sin_sesion_no_hay_acceso_a_la_caja(anon_client):
    assert anon_client.get("/api/cash/current").status_code == 401
    assert anon_client.post("/api/cash/open", json={"opening_amount": 1}).status_code == 401
