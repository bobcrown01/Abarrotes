from decimal import Decimal
from pydantic import BaseModel
from typing import Optional

class InventoryMovementCreate(BaseModel):
    product_id: int
    type: str  # entrada / salida / ajuste
    quantity: Decimal
    reason: Optional[str] = None
    user_id: Optional[int] = None
