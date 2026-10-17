from fastapi import APIRouter, Depends, HTTPException
from decimal import Decimal
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.products import Product
from app.schemas.inventory import InventoryMovementCreate

router = APIRouter()

@router.post("/inventory/movements")
def create_inventory_movement(data: InventoryMovementCreate, db: Session = Depends(get_db)):

    # Validar producto
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Obtener inventario actual
    inventory = db.query(Inventory).filter(Inventory.product_id == data.product_id).first()

    if not inventory:
        inventory = Inventory(product_id=data.product_id, quantity=Decimal("0"))
        db.add(inventory)

    # Calcular nuevo inventario
    if data.type == "entrada":
        inventory.quantity += data.quantity

    elif data.type == "salida":
        if inventory.quantity < data.quantity:
            raise HTTPException(status_code=400, detail="Inventario insuficiente")
        inventory.quantity -= data.quantity

    elif data.type == "ajuste":
        inventory.quantity = data.quantity

    else:
        raise HTTPException(status_code=400, detail="Tipo de movimiento inválido")

    # Registrar movimiento
    movement = InventoryMovement(
        product_id=data.product_id,
        type=data.type,
        quantity=data.quantity,
        reason=data.reason,
        user_id=data.user_id
    )

    db.add(movement)
    db.commit()
    db.refresh(movement)

    return {
        "status": "success",
        "message": "Movimiento registrado",
        "movement_id": movement.id,
        "new_quantity": float(inventory.quantity)
    }
