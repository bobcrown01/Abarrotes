from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    method = Column(String(30), nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    received = Column(Numeric(12,2))
    change = Column(Numeric(12,2))
    reference = Column(String(100))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    sale = relationship("Sale", back_populates="payments")
