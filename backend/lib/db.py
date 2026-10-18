"""Loop-safe shared Mongo handle.

Routers import ``db`` as before, but the proxy creates Motor inside the event
loop that performs the first database operation. This avoids binding Motor to
the module-import loop used by production ASGI loaders.
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
database_name = os.environ["DB_NAME"]


class _LoopSafeDatabase:
    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None
        self._database = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def get(self):
        loop = asyncio.get_running_loop()
        if self._database is None or self._loop is not loop:
            if self._client is not None:
                self._client.close()
            self._client = AsyncIOMotorClient(mongo_url)
            self._database = self._client[database_name]
            self._loop = loop
        return self._database

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self._database = None
        self._loop = None

    def __getattr__(self, name: str):
        return getattr(self.get(), name)

    def __getitem__(self, name: str):
        return self.get()[name]


db = _LoopSafeDatabase()


def get_db():
    return db.get()


def init_db():
    return get_db()


def close_db() -> None:
    db.close()

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "products": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("slug", ASCENDING)], name="slug", unique=True),
        IndexModel([("category", ASCENDING), ("created_at", DESCENDING)], name="category_created"),
        IndexModel([("fabric", ASCENDING)], name="fabric"),
        IndexModel([("status", ASCENDING), ("created_at", DESCENDING)], name="status_created"),
    ],
    "discounts": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("status", ASCENDING), ("starts_at", ASCENDING), ("ends_at", ASCENDING)], name="status_window"),
        IndexModel([("product_ids", ASCENDING)], name="product_ids"),
        IndexModel([("collections", ASCENDING)], name="collections"),
        IndexModel([("code", ASCENDING)], name="code_unique", unique=True, partialFilterExpression={"code": {"$type": "string"}}),
    ],
    "checkout_sessions": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("session_key", ASCENDING)], name="session_key", unique=True),
        IndexModel([("checkout_number", ASCENDING)], name="checkout_number", unique=True),
        IndexModel([("status", ASCENDING), ("last_activity_at", DESCENDING)], name="status_activity"),
        IndexModel([("reminder_status", ASCENDING), ("last_activity_at", ASCENDING)], name="reminder_activity"),
        IndexModel([("completed_order_request_id", ASCENDING)], name="completed_order", sparse=True),
    ],
    "product_media.files": [IndexModel([("metadata.legacy_path", ASCENDING)], name="legacy_path", sparse=True)],
    "cron_runs": [IndexModel([("run_id", ASCENDING)], name="run_id", unique=True)],
    "catalog_groups": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("group_type", ASCENDING), ("slug", ASCENDING)], name="type_slug", unique=True),
        IndexModel([("status", ASCENDING), ("sort_order", ASCENDING)], name="status_sort"),
    ],
    "site_content": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "store_settings": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "invoices": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("order_id", ASCENDING), ("document_type", ASCENDING)], name="order_document", unique=True),
        IndexModel([("number", ASCENDING)], name="number", unique=True),
        IndexModel([("customer_id", ASCENDING), ("issued_at", DESCENDING)], name="customer_issued", sparse=True),
    ],
    "email_verification_tokens": [
        IndexModel([("token_hash", ASCENDING)], name="token_hash", unique=True),
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created"),
        IndexModel([("expires_at", ASCENDING)], name="expires_at_ttl", expireAfterSeconds=0),
    ],
    "order_status_notifications": [IndexModel([("request_id", ASCENDING), ("status", ASCENDING)], name="request_status", unique=True)],
    "invoice_notifications": [IndexModel([("invoice_id", ASCENDING)], name="invoice_id", unique=True)],
    "oauth_exchanges": [
        IndexModel([("session_id_hash", ASCENDING)], name="session_id_hash", unique=True),
        IndexModel([("created_at", ASCENDING)], name="created_at_ttl", expireAfterSeconds=86400),
    ],
    "google_link_notifications": [IndexModel([("user_id", ASCENDING)], name="user_id", unique=True)],
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
        IndexModel([("converted_order_id", ASCENDING), ("received_at", DESCENDING)], name="converted_received"),
        IndexModel([("request_received_email_status", ASCENDING), ("received_at", ASCENDING)], name="request_email_queue"),
        IndexModel([("paid_email_status", ASCENDING), ("payment_verified_at", ASCENDING)], name="paid_email_queue"),
        IndexModel([("payment_transaction_id", ASCENDING)], name="payment_transaction_id", unique=True, sparse=True),
        IndexModel([("payment_provider", ASCENDING), ("payment_status", ASCENDING), ("payment_created_at", ASCENDING)], name="provider_payment_created"),
        IndexModel([("checkout_session_id", ASCENDING), ("payment_status", ASCENDING)], name="checkout_payment_status", sparse=True),
    ],
    "waitlist_requests": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("status", ASCENDING), ("created_at", DESCENDING)], name="status_created"),
        IndexModel([("product_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)], name="product_status_created"),
        IndexModel([("mobile_normalised", ASCENDING), ("product_id", ASCENDING), ("size_key", ASCENDING), ("color_key", ASCENDING), ("status", ASCENDING)], name="mobile_product_variant_status"),
        IndexModel([("email_normalised", ASCENDING), ("product_id", ASCENDING), ("size_key", ASCENDING), ("color_key", ASCENDING), ("status", ASCENDING)], name="email_product_variant_status", sparse=True),
        IndexModel([("active_mobile_key", ASCENDING)], name="active_mobile_key", unique=True, sparse=True),
        IndexModel([("active_email_key", ASCENDING)], name="active_email_key", unique=True, sparse=True),
    ],
    "orders": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("order_number", ASCENDING)], name="order_number", unique=True),
        IndexModel([("source_request_id", ASCENDING)], name="source_request_id", unique=True),
        IndexModel([("customer_id", ASCENDING), ("converted_at", DESCENDING)], name="customer_converted"),
    ],
}


async def ensure_indexes() -> None:
    database = get_db()
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await database[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
