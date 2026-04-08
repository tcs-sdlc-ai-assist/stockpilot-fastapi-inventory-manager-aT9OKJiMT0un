from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    sku = Column(String(50), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    unit_price = Column(Float, nullable=False, default=0.0)
    reorder_level = Column(Integer, nullable=False, default=10)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="items", lazy="selectin")
    owner = relationship("User", back_populates="inventory_items", lazy="selectin")

    @property
    def total_value(self) -> float:
        return (self.quantity or 0) * (self.unit_price or 0.0)

    @property
    def is_low_stock(self) -> bool:
        quantity = self.quantity or 0
        reorder = self.reorder_level or 0
        return quantity <= reorder and quantity > 0

    @property
    def is_out_of_stock(self) -> bool:
        return (self.quantity or 0) <= 0

    def __repr__(self) -> str:
        return f"<InventoryItem(id={self.id}, name='{self.name}', quantity={self.quantity})>"