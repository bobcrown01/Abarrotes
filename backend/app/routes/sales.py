from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.products import Product
from app.models.payment import Payment
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.schemas.sale import SaleCreate, SaleItemCreate, PaymentCreate
from app.models.inventory import Inventory
from datetime import datetime

router = APIRouter()

@router.post("/sales")
def create_sale(data: SaleCreate, db: Session = Depends(get_db)):

    new_sale = Sale(
        folio=f"V-{int(datetime.utcnow().timestamp())}",
        customer_id=data.customer_id,
        user_id=data.user_id,
        status="pendiente"
    )

    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)

    return {
        "status": "success",
        "sale_id": new_sale.id,
        "folio": new_sale.folio
    }

@router.post("/sales/items")
def add_sale_item(data: SaleItemCreate, db: Session = Depends(get_db)):

    sale = db.query(Sale).filter(Sale.id == data.sale_id).first()
    if not sale:
        raise HTTPException(404, "Venta no encontrada")

    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, "Producto no encontrado")

    subtotal = (data.qty * data.price) - data.discount

    item = SaleItem(
        sale_id=data.sale_id,
        product_id=data.product_id,
        qty=data.qty,
        price=data.price,
        discount=data.discount,
        subtotal=subtotal
    )

    db.add(item)

    # Actualizar totales de la venta
    sale.subtotal += subtotal
    sale.total = sale.subtotal - sale.discount

    db.commit()
    db.refresh(item)

    return {
        "status": "success",
        "item_id": item.id,
        "sale_total": float(sale.total)
    }

@router.post("/sales/payments")
def add_payment(data: PaymentCreate, db: Session = Depends(get_db)):

    sale = db.query(Sale).filter(Sale.id == data.sale_id).first()
    if not sale:
        raise HTTPException(404, "Venta no encontrada")

    payment = Payment(
        sale_id=data.sale_id,
        method=data.method,
        amount=data.amount,
        received=data.received,
        change=data.change,
        reference=data.reference
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "status": "success",
        "payment_id": payment.id
    }

@router.post("/sales/{sale_id}/close")
def close_sale(sale_id: int, db: Session = Depends(get_db)):

    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(404, "Venta no encontrada")

    total_pagado = sum([float(p.amount) for p in sale.payments])

    if total_pagado < sale.total:
        raise HTTPException(400, "La venta no está completamente pagada")

    sale.status = "pagada"

    # Restar inventario por cada item
    for item in sale.items:
        inv = db.query(Inventory).filter(Inventory.product_id == item.product_id).first()
        if inv:
            inv.quantity -= item.qty

    db.commit()

    return {"status": "success", "message": "Venta cerrada"}

@router.get("/sales/{sale_id}")
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(404, "Venta no encontrada")
    return sale

@router.get("/sales")
def list_sales(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    return db.query(Sale).order_by(Sale.id.desc()).limit(limit).offset(offset).all()

@router.post("/sales/{sale_id}/cancel")
def cancel_sale(sale_id: int, db: Session = Depends(get_db)):

    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(404, "Venta no encontrada")

    sale.status = "cancelada"

    # Revertir inventario
    for item in sale.items:
        inv = db.query(Inventory).filter(Inventory.product_id == item.product_id).first()
        if inv:
            inv.quantity += item.qty

    db.commit()

    return {"status": "success", "message": "Venta cancelada"}
