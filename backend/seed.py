import asyncio
from datetime import datetime, timezone
import uuid

from lib.db import client, db, ensure_indexes
from lib.security import hash_secret
from models.product import DEFAULT_PRODUCTS


async def seed() -> None:
    await ensure_indexes()
    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([product.model_dump() for product in DEFAULT_PRODUCTS])
    await db.users.update_one(
        {"email": "admin@safyra.co"},
        {"$setOnInsert": {
            "id": str(uuid.uuid4()),
            "email": "admin@safyra.co",
            "name": "SAFYRA Administrator",
            "phone": "",
            "role": "admin",
            "password_hash": hash_secret("Safyra!Admin#2026"),
            "security_question": "What is the private SAFYRA admin recovery phrase?",
            "security_answer_hash": hash_secret("zardozi 1947"),
            "wishlist_ids": [],
            "cart": [],
            "orders": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    await db.users.update_one(
        {"email": "customer@safyra.co"},
        {"$setOnInsert": {
            "id": str(uuid.uuid4()),
            "email": "customer@safyra.co",
            "name": "SAFYRA Guest",
            "phone": "+91 90000 00000",
            "role": "customer",
            "password_hash": hash_secret("Safyra!Customer#2026"),
            "wishlist_ids": [],
            "cart": [],
            "orders": [{
                "id": str(uuid.uuid4()),
                "order_number": "SF-DEMO-1042",
                "placed_at": datetime(2026, 1, 18, tzinfo=timezone.utc),
                "status": "In transit",
                "total": 3850,
                "invoice_number": "INV-DEMO-1042",
                "is_demo": True,
                "items": [{
                    "product_name": "Luxury Nazakat Collection",
                    "image_url": "https://safyra.co/cdn/shop/files/BF92BEEC-84EB-497C-9B69-2948C142F272.jpg?v=1767270653&width=600",
                    "size": "M",
                    "color": "Forest green",
                    "quantity": 1,
                    "price": 3850,
                }],
                "tracking": [
                    {"label": "Order confirmed", "completed": True, "date": "18 Jan 2026"},
                    {"label": "Artisan finishing", "completed": True, "date": "28 Jan 2026"},
                    {"label": "Dispatched", "completed": True, "date": "12 Feb 2026"},
                    {"label": "Delivered", "completed": False, "date": ""},
                ],
            }],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())