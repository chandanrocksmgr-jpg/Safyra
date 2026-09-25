from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from lib.db import db
from lib.security import get_optional_user
from models.order_request import OrderRequestCreate, OrderRequestResponse


router = APIRouter(prefix="/order-requests", tags=["order requests"])


@router.post("", response_model=OrderRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_order_request(input: OrderRequestCreate, user: dict | None = Depends(get_optional_user)):
    product_ids = list(dict.fromkeys(item.product_id for item in input.items))
    products = await db.products.find({"id": {"$in": product_ids}}).to_list(len(product_ids))
    product_map = {product["id"]: product for product in products}
    if len(product_map) != len(product_ids):
        raise HTTPException(status_code=422, detail="One or more products are no longer available")

    stored_items = []
    subtotal = 0
    for item in input.items:
        product = product_map[item.product_id]
        if product.get("sizes") and item.size not in product["sizes"]:
            raise HTTPException(status_code=422, detail=f"Invalid size for {product['title']}")
        if product.get("colors") and item.color not in product["colors"]:
            raise HTTPException(status_code=422, detail=f"Invalid colour for {product['title']}")
        line_total = product["price"] * item.quantity
        subtotal += line_total
        stored_items.append({
            "product_id": product["id"],
            "title": product["title"],
            "image_url": product["image_url"],
            "price": product["price"],
            "size": item.size,
            "color": item.color,
            "quantity": item.quantity,
            "line_total": line_total,
        })

    received_at = datetime.now(timezone.utc)
    request_number = f"SAF-REQ-{received_at:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    document = input.model_dump(exclude={"items"})
    document.update({
        "id": str(uuid.uuid4()),
        "request_number": request_number,
        "received_at": received_at,
        "customer_id": user.get("id") if user else None,
        "items": stored_items,
        "subtotal": subtotal,
    })
    await db.order_requests.insert_one(document)
    return OrderRequestResponse(request_number=request_number, received_at=received_at)