from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    type = Column(String(20), nullable=False)  # entrada / salida / ajuste
    quantity = Column(Numeric(14,3), nullable=False)
    reason = Column(String(100))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

    product = relationship("Product")
