import asyncio

from lib.db import client, db, ensure_indexes
from models.product import DEFAULT_PRODUCTS


async def seed() -> None:
    await ensure_indexes()
    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([product.model_dump() for product in DEFAULT_PRODUCTS])
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())