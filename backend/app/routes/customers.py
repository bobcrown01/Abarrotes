"""Endpoints HTTP de clientes y abonos."""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.models.customer import Customer
from app.models.customer_payment import CustomerPayment
from app.routes.dependencies import (
    LOGIN_REQUIRED,
    MANAGER_REQUIRED,
    CurrentUserDep,
    CustomerServiceDep,
)
from app.schemas.customer import (
    CustomerCreate,
    CustomerOut,
    CustomerPaymentCreate,
    CustomerPaymentOut,
    CustomerUpdate,
)

# El cajero consulta y recibe abonos; definir a quién y cuánto se fía es de administración
router = APIRouter(prefix="/customers", tags=["clientes"], dependencies=[LOGIN_REQUIRED])


@router.get("", response_model=list[CustomerOut])
def list_customers(service: CustomerServiceDep) -> Sequence[Customer]:
    """Lista los clientes ordenados por nombre."""
    return service.list_customers()


@router.post(
    "",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[MANAGER_REQUIRED],
)
def create_customer(data: CustomerCreate, service: CustomerServiceDep) -> Customer:
    """Da de alta un cliente."""
    return service.create_customer(data)


@router.put("/{customer_id}", response_model=CustomerOut, dependencies=[MANAGER_REQUIRED])
def update_customer(
    customer_id: int, data: CustomerUpdate, service: CustomerServiceDep
) -> Customer:
    """Cambia nombre, teléfono o límite de fiado. Responde 404 si no existe."""
    return service.update_customer(customer_id, data)


@router.post(
    "/{customer_id}/payments",
    response_model=CustomerPaymentOut,
    status_code=status.HTTP_201_CREATED,
)
def record_payment(
    customer_id: int,
    data: CustomerPaymentCreate,
    service: CustomerServiceDep,
    user: CurrentUserDep,
) -> CustomerPayment:
    """Registra un abono. Responde 409 si excede la deuda o si la caja está cerrada."""
    return service.record_payment(customer_id, data, user.id)


@router.get("/{customer_id}/payments", response_model=list[CustomerPaymentOut])
def list_payments(
    customer_id: int,
    service: CustomerServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Sequence[CustomerPayment]:
    """Lista los abonos de un cliente, los más recientes primero."""
    return service.list_payments(customer_id, limit)
