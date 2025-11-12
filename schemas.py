"""
Database Schemas for School Merchandise Store

Each Pydantic model represents a MongoDB collection (collection name = lowercase class name).

Collections:
- MerchandiseProduct: products students can buy (hoodies, beanies, shirts, trackpants)
- Order: customer orders made from the storefront
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List

# ---------------------------
# Product Catalog
# ---------------------------
class MerchandiseProduct(BaseModel):
    """
    Collection: "merchandiseproduct"
    Represents a sellable item in the store. Supports multiple colors and images.
    """
    title: str = Field(..., description="Display name, e.g., 'Classic Hoodie'")
    category: str = Field(..., description="One of: hoodie, beanie, shirt, trackpants")
    description: Optional[str] = Field(None, description="Product description")
    base_price: float = Field(..., ge=0, description="Base price in dollars")
    colors: List[str] = Field(default_factory=list, description="Available colors (e.g., green, black, yellow, white)")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    in_stock: bool = Field(True, description="Whether the product is currently in stock")

# ---------------------------
# Orders
# ---------------------------
class OrderItem(BaseModel):
    product_id: str = Field(..., description="ID of the product")
    title: str = Field(..., description="Snapshot of product title at order time")
    category: str = Field(...)
    color: str = Field(..., description="Selected color")
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0, description="Unit price before embroidery")
    embroidery_text: Optional[str] = Field(None, description="Optional custom embroidery text")
    embroidery_fee: float = Field(0.0, ge=0, description="Additional fee applied for embroidery per item")
    line_total: float = Field(..., ge=0, description="Computed quantity * (unit_price + embroidery_fee)")

class Order(BaseModel):
    """
    Collection: "order"
    Stores an order consisting of multiple items with optional custom embroidery.
    """
    customer_name: str = Field(...)
    customer_email: str = Field(...)
    items: List[OrderItem] = Field(...)
    sub_total: float = Field(..., ge=0)
    embroidery_total: float = Field(..., ge=0)
    grand_total: float = Field(..., ge=0)
    notes: Optional[str] = Field(None)
