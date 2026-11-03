"""Pruebas de clientes, ventas fiadas y abonos."""

import pytest

from app.models.user import User
from app.services.auth_service import login_throttle
from app.utils.security import hash_password


@pytest.fixture
def customer(db_client):
    """Cliente con $100 de límite de fiado."""
    payload = {"name": "Doña Lupe", "phone": "5512345678", "credit_limit": 100}
    response = db_client.post("/api/customers", json=payload)
    assert response.status_code == 201
    return response.json()


def fiar(client, customer_id, qty=1):
    """Vende Coca Cola ($18.50 c/u) a fiado y regresa la respuesta del pago y el id."""
    sale = client.post("/api/sales", json={"customer_id": customer_id}).json()
    current = client.post(
        "/api/sales/items", json={"sale_id": sale["id"], "product_id": 1, "qty": qty}
    ).json()
    payment = client.post(
        "/api/sales/payments",
        json={"sale_id": sale["id"], "method": "venta_credito", "amount": current["total"]},
    )
    return payment, sale["id"]


def balance(client):
    return client.get("/api/customers").json()[0]["balance"]


def test_alta_empieza_sin_deuda(customer):
    assert customer["balance"] == 0
    assert customer["credit_limit"] == 100


def test_editar_no_toca_el_saldo(db_client, customer):
    response = db_client.put(f"/api/customers/{customer['id']}", json={"credit_limit": 500})

    assert response.json()["credit_limit"] == 500
    assert response.json()["name"] == "Doña Lupe"
    assert response.json()["balance"] == 0
    # El saldo no se puede mandar: solo cambia con ventas y abonos
    forged = db_client.put(f"/api/customers/{customer['id']}", json={"balance": 0})
    assert forged.status_code == 422


def test_fiado_suma_deuda_hasta_cerrar_la_venta(db_client, customer):
    payment, sale_id = fiar(db_client, customer["id"], qty=2)

    assert payment.status_code == 201
    assert balance(db_client) == 0  # Todavía no cierra

    assert db_client.post(f"/api/sales/{sale_id}/close").status_code == 200
    assert balance(db_client) == 37


def test_fiado_sin_cliente_se_rechaza(db_client):
    sale = db_client.post("/api/sales", json={}).json()
    current = db_client.post(
        "/api/sales/items", json={"sale_id": sale["id"], "product_id": 1, "qty": 1}
    ).json()

    response = db_client.post(
        "/api/sales/payments",
        json={"sale_id": sale["id"], "method": "venta_credito", "amount": current["total"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Para fiar hay que elegir un cliente"


def test_fiado_no_rebasa_el_limite(db_client, customer):
    payment, _ = fiar(db_client, customer["id"], qty=6)  # $111.00 con límite de $100

    assert payment.status_code == 409
    assert payment.json()["detail"] == "La venta rebasa el límite de fiado del cliente"


def test_cliente_sin_limite_no_puede_fiar(db_client):
    other = db_client.post("/api/customers", json={"name": "Sin crédito"}).json()

    payment, _ = fiar(db_client, other["id"])

    assert payment.status_code == 409


def test_cancelar_venta_fiada_quita_la_deuda(db_client, customer):
    _, sale_id = fiar(db_client, customer["id"])
    db_client.post(f"/api/sales/{sale_id}/close")

    db_client.post(f"/api/sales/{sale_id}/cancel")

    assert balance(db_client) == 0


def test_cancelar_fiado_pendiente_no_altera_la_deuda(db_client, customer):
    _, sale_id = fiar(db_client, customer["id"])

    db_client.post(f"/api/sales/{sale_id}/cancel")

    assert balance(db_client) == 0


def test_abono_baja_la_deuda_y_queda_registrado(db_client, customer):
    _, sale_id = fiar(db_client, customer["id"])
    db_client.post(f"/api/sales/{sale_id}/close")

    response = db_client.post(f"/api/customers/{customer['id']}/payments", json={"amount": 10})

    assert response.status_code == 201
    assert response.json()["user_id"] == 1
    assert balance(db_client) == 8.5
    history = db_client.get(f"/api/customers/{customer['id']}/payments").json()
    assert [p["amount"] for p in history] == [10]


def test_abono_no_excede_la_deuda(db_client, customer):
    response = db_client.post(f"/api/customers/{customer['id']}/payments", json={"amount": 1})

    assert response.status_code == 409
    assert response.json()["detail"] == "El abono es mayor que lo que debe el cliente"


def test_abono_requiere_caja_abierta(db_client, customer):
    _, sale_id = fiar(db_client, customer["id"])
    db_client.post(f"/api/sales/{sale_id}/close")
    db_client.post("/api/cash/close", json={"counted_amount": 100})

    response = db_client.post(f"/api/customers/{customer['id']}/payments", json={"amount": 1})

    assert response.status_code == 409


def test_corte_fiado_no_entra_a_la_caja_y_abono_en_efectivo_si(db_client, customer):
    _, sale_id = fiar(db_client, customer["id"])  # $18.50 fiados
    db_client.post(f"/api/sales/{sale_id}/close")
    url = f"/api/customers/{customer['id']}/payments"
    db_client.post(url, json={"amount": 5})
    db_client.post(url, json={"amount": 3, "method": "debito"})

    session = db_client.get("/api/cash/current").json()["session"]

    assert session["expected_cash"] == 105  # Fondo + abono en efectivo; ni fiado ni débito
    assert session["sales_total"] == 18.5  # Los abonos no son ventas nuevas
    assert session["by_method"] == [
        {"method": "venta_credito", "amount": 18.5},
        {"method": "abono_debito", "amount": 3},
        {"method": "abono_efectivo", "amount": 5},
    ]


@pytest.mark.parametrize(
    "payload", [{"name": ""}, {"name": "x" * 151}, {"name": "Ana", "credit_limit": -1}]
)
def test_alta_invalida_responde_422(db_client, payload):
    assert db_client.post("/api/customers", json=payload).status_code == 422


def test_abono_no_acepta_fiado_como_metodo(db_client, customer):
    response = db_client.post(
        f"/api/customers/{customer['id']}/payments",
        json={"amount": 1, "method": "venta_credito"},
    )

    assert response.status_code == 422


def test_cliente_inexistente_responde_404(db_client):
    assert db_client.put("/api/customers/999", json={"name": "X"}).status_code == 404
    assert db_client.post("/api/customers/999/payments", json={"amount": 1}).status_code == 404
    assert db_client.get("/api/customers/999/payments").status_code == 404


def test_cajero_recibe_abonos_pero_no_define_el_fiado(anon_client, db_session):
    db_session.add(User(id=3, username="caja2", password_hash=hash_password("1234"), role_id=1))
    db_session.commit()
    login_throttle.reset("caja2")
    anon_client.post("/api/auth/login", json={"username": "caja2", "password": "1234"})

    assert anon_client.get("/api/customers").status_code == 200
    assert anon_client.post("/api/customers", json={"name": "Ana"}).status_code == 403
    assert anon_client.put("/api/customers/1", json={"credit_limit": 9}).status_code == 403
