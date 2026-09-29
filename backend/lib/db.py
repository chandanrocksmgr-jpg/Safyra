"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "products": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("slug", ASCENDING)], name="slug", unique=True),
        IndexModel([("category", ASCENDING), ("created_at", DESCENDING)], name="category_created"),
        IndexModel([("fabric", ASCENDING)], name="fabric"),
    ],
    "users": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("email", ASCENDING)], name="email", unique=True),
        IndexModel([("role", ASCENDING)], name="role"),
    ],
    "sessions": [
        IndexModel([("token_hash", ASCENDING)], name="token_hash", unique=True),
        IndexModel([("user_id", ASCENDING)], name="user_id"),
        IndexModel([("expires_at", ASCENDING)], name="expires_at_ttl", expireAfterSeconds=0),
    ],
    "recovery_attempts": [
        IndexModel([("email", ASCENDING), ("created_at", DESCENDING)], name="email_created"),
        IndexModel([("created_at", ASCENDING)], name="created_at_ttl", expireAfterSeconds=86400),
    ],
    "order_requests": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("request_number", ASCENDING)], name="request_number", unique=True),
        IndexModel([("customer_id", ASCENDING), ("received_at", DESCENDING)], name="customer_received"),
        IndexModel([("received_at", DESCENDING)], name="received_at"),
        IndexModel([("payment_status", ASCENDING), ("fulfilment_status", ASCENDING), ("received_at", DESCENDING)], name="status_received"),
    ],
    "orders": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("order_number", ASCENDING)], name="order_number", unique=True),
        IndexModel([("source_request_id", ASCENDING)], name="source_request_id", unique=True),
        IndexModel([("customer_id", ASCENDING), ("converted_at", DESCENDING)], name="customer_converted"),
    ],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
