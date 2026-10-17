from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    folio = Column(String(50), unique=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    subtotal = Column(Numeric(12,2), default=0)
    discount = Column(Numeric(12,2), default=0)
    total = Column(Numeric(12,2), default=0)
    status = Column(String(20), default="pendiente")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

    items = relationship("SaleItem", back_populates="sale")
    payments = relationship("Payment", back_populates="sale")
