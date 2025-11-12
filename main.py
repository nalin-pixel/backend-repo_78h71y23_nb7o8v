import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import MerchandiseProduct, Order, OrderItem

app = FastAPI(title="School Merchandise Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Utilities ----------

def to_str_id(doc):
    if doc is None:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# ---------- Health & Test ----------

@app.get("/")
def read_root():
    return {"message": "School Merchandise Store Backend"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# ---------- Product Catalog ----------

@app.get("/api/products")
def list_products():
    docs = get_documents("merchandiseproduct")
    return [to_str_id(d) for d in docs]

class CreateProduct(BaseModel):
    title: str
    category: str # hoodie, beanie, shirt, trackpants
    description: Optional[str] = None
    base_price: float
    colors: List[str] = []
    images: List[str] = []
    in_stock: bool = True

@app.post("/api/products", status_code=201)
def create_product(payload: CreateProduct):
    # Basic category & color validation
    allowed_cats = {"hoodie", "beanie", "shirt", "trackpants"}
    allowed_colors = {"green", "black", "yellow", "white"}
    if payload.category not in allowed_cats:
        raise HTTPException(status_code=400, detail="Invalid category")
    if any(c not in allowed_colors for c in payload.colors):
        raise HTTPException(status_code=400, detail="One or more invalid colors")

    model = MerchandiseProduct(**payload.model_dump())
    new_id = create_document("merchandiseproduct", model)
    return {"id": new_id}

# ---------- Orders with Optional Embroidery ----------

EMBROIDERY_FEE_PER_ITEM = 8.0  # default extra cost per item if embroidery text provided

class CreateOrderItem(BaseModel):
    product_id: str
    color: str
    quantity: int
    embroidery_text: Optional[str] = None

class CreateOrder(BaseModel):
    customer_name: str
    customer_email: str
    items: List[CreateOrderItem]
    notes: Optional[str] = None

@app.post("/api/orders", status_code=201)
def create_order(payload: CreateOrder):
    # Validate colors and compute totals
    allowed_colors = {"green", "black", "yellow", "white"}
    for it in payload.items:
        if it.color not in allowed_colors:
            raise HTTPException(status_code=400, detail=f"Invalid color: {it.color}")
        if it.quantity < 1:
            raise HTTPException(status_code=400, detail="Quantity must be >= 1")

    # Fetch products for all items
    ids = [ObjectId(i.product_id) for i in payload.items if ObjectId.is_valid(i.product_id)]
    if len(ids) != len(payload.items):
        raise HTTPException(status_code=400, detail="Invalid product id")

    products_map = {}
    for doc in db["merchandiseproduct"].find({"_id": {"$in": ids}}):
        products_map[str(doc["_id"]) ] = doc

    if len(products_map) != len(payload.items):
        raise HTTPException(status_code=400, detail="One or more products not found")

    order_items: List[OrderItem] = []
    sub_total = 0.0
    embroidery_total = 0.0

    for it in payload.items:
        p = products_map[it.product_id]
        unit = float(p.get("base_price", 0))
        embroidery_fee = EMBROIDERY_FEE_PER_ITEM if (it.embroidery_text and it.embroidery_text.strip()) else 0.0
        line_total = (unit + embroidery_fee) * it.quantity
        sub_total += unit * it.quantity
        embroidery_total += embroidery_fee * it.quantity
        order_items.append(
            OrderItem(
                product_id=it.product_id,
                title=p.get("title", ""),
                category=p.get("category", ""),
                color=it.color,
                quantity=it.quantity,
                unit_price=unit,
                embroidery_text=it.embroidery_text,
                embroidery_fee=embroidery_fee,
                line_total=line_total,
            )
        )

    grand_total = sub_total + embroidery_total

    order = Order(
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        items=order_items,
        sub_total=sub_total,
        embroidery_total=embroidery_total,
        grand_total=grand_total,
        notes=payload.notes,
    )

    order_id = create_document("order", order)
    return {"id": order_id, "grand_total": grand_total}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
