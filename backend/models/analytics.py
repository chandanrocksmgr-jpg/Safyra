from pydantic import BaseModel, Field


class SalesMetrics(BaseModel):
    revenue: int = 0
    paid_orders: int = 0
    average_order_value: int = 0
    units_sold: int = 0
    checkout_sessions: int = 0
    conversion_rate: float = 0
    abandoned_checkouts: int = 0


class SalesTrendPoint(BaseModel):
    date: str
    revenue: int = 0
    orders: int = 0


class TopProduct(BaseModel):
    title: str
    units: int
    revenue: int


class DiscountPerformance(BaseModel):
    name: str
    uses: int
    savings: int


class SalesAnalytics(BaseModel):
    days: int
    current: SalesMetrics
    previous: SalesMetrics
    revenue_change: float = 0
    order_change: float = 0
    trend: list[SalesTrendPoint] = Field(default_factory=list)
    top_products: list[TopProduct] = Field(default_factory=list)
    discounts: list[DiscountPerformance] = Field(default_factory=list)