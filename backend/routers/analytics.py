from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from lib.db import db
from lib.security import require_admin
from models.analytics import DiscountPerformance, SalesAnalytics, SalesMetrics, SalesTrendPoint, TopProduct


router = APIRouter(prefix="/analytics", tags=["analytics"])


def _percent_change(current: int, previous: int) -> float:
    if previous == 0:
        return 100.0 if current else 0.0
    return round((current - previous) * 100 / previous, 1)


async def _metrics(start: datetime, end: datetime) -> tuple[SalesMetrics, list[dict]]:
    orders = await db.orders.find({"payment_status": "Paid", "converted_at": {"$gte": start, "$lt": end}, "cancelled": {"$ne": True}}).to_list(5000)
    sessions = await db.checkout_sessions.count_documents({"started_at": {"$gte": start, "$lt": end}})
    abandoned = await db.checkout_sessions.count_documents({"started_at": {"$gte": start, "$lt": end}, "status": "Abandoned"})
    revenue = sum(int(order.get("total") or order.get("subtotal") or 0) for order in orders)
    units = sum(int(item.get("quantity", 0)) for order in orders for item in order.get("items", []))
    return SalesMetrics(
        revenue=revenue, paid_orders=len(orders), average_order_value=round(revenue / len(orders)) if orders else 0,
        units_sold=units, checkout_sessions=sessions, conversion_rate=round(len(orders) * 100 / sessions, 1) if sessions else 0,
        abandoned_checkouts=abandoned,
    ), orders


@router.get("/sales", response_model=SalesAnalytics)
async def sales_analytics(days: int = Query(default=30, ge=7, le=365), _: dict = Depends(require_admin)):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    previous_start = start - timedelta(days=days)
    current, orders = await _metrics(start, end)
    previous, _ = await _metrics(previous_start, start)
    trend_map = { (start + timedelta(days=index)).date().isoformat(): {"revenue": 0, "orders": 0} for index in range(days) }
    product_map: dict[str, dict] = defaultdict(lambda: {"units": 0, "revenue": 0})
    discount_map: dict[str, dict] = defaultdict(lambda: {"uses": 0, "savings": 0})
    for order in orders:
        placed = order.get("converted_at", end)
        placed = placed if placed.tzinfo else placed.replace(tzinfo=timezone.utc)
        day = placed.date().isoformat()
        if day in trend_map:
            trend_map[day]["orders"] += 1
            trend_map[day]["revenue"] += int(order.get("total") or order.get("subtotal") or 0)
        seen_discounts: set[str] = set()
        for item in order.get("items", []):
            product_map[item["title"]]["units"] += int(item.get("quantity", 0))
            product_map[item["title"]]["revenue"] += int(item.get("line_total", 0))
            if item.get("discount_name"):
                discount_map[item["discount_name"]]["savings"] += int(item.get("discount_amount", 0))
                seen_discounts.add(item["discount_name"])
        for name in seen_discounts:
            discount_map[name]["uses"] += 1
    return SalesAnalytics(
        days=days, current=current, previous=previous,
        revenue_change=_percent_change(current.revenue, previous.revenue),
        order_change=_percent_change(current.paid_orders, previous.paid_orders),
        trend=[SalesTrendPoint(date=date, **values) for date, values in trend_map.items()],
        top_products=[TopProduct(title=title, **values) for title, values in sorted(product_map.items(), key=lambda pair: pair[1]["revenue"], reverse=True)[:8]],
        discounts=[DiscountPerformance(name=name, **values) for name, values in sorted(discount_map.items(), key=lambda pair: pair[1]["uses"], reverse=True)[:8]],
    )