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
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())