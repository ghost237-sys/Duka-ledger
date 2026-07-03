from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────
# Category
# ─────────────────────────────────────────

class CategoryOut(BaseModel):
    id: str
    name: str
    sort_order: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# SKU
# ─────────────────────────────────────────

class SKUOut(BaseModel):
    id: str
    client_id: str
    product_id: Optional[str]
    name: str
    selling_price: Decimal
    buying_price: Optional[Decimal]
    needs_cost_review: bool
    stock_qty: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Product
# ─────────────────────────────────────────

class ProductOut(BaseModel):
    id: str
    client_id: str
    brand_name: str
    manufacturer: Optional[str]
    category_id: Optional[str]
    skus: List[SKUOut] = []

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Sync batch — what the phone sends up
# ─────────────────────────────────────────

class NewSKUIn(BaseModel):
    """
    A SKU created via Quick Add on the phone (online or offline).
    No product_id required — it's unlinked until the owner assigns it.
    """
    client_id: str
    name: str
    selling_price: Decimal
    buying_price: Optional[Decimal] = None


class SaleItemIn(BaseModel):
    sku_id: Optional[str] = None          # server id — for already-synced SKUs
    sku_client_id: Optional[str] = None   # client id — for SKUs in this same batch
    quantity: int
    unit_price_at_sale: Decimal


class SaleIn(BaseModel):
    client_id: str
    shopkeeper_id: Optional[str] = None
    sold_at: datetime
    total_amount: Decimal
    items: List[SaleItemIn]


class SyncBatchIn(BaseModel):
    shop_id: str
    new_skus: List[NewSKUIn] = Field(default_factory=list)
    sales: List[SaleIn] = Field(default_factory=list)


class SyncBatchOut(BaseModel):
    synced_sku_ids: dict
    synced_sale_ids: dict
    skipped_duplicate_sales: List[str]


# ─────────────────────────────────────────
# Auth
# ─────────────────────────────────────────

class LoginIn(BaseModel):
    phone: str
    pin: str


class ShopkeeperOut(BaseModel):
    id: str
    name: str
    phone: str
    role: str
    shop_id: Optional[str]

    class Config:
        from_attributes = True


class LoginOut(BaseModel):
    token: str
    shopkeeper: ShopkeeperOut


# ─────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────

class DailySummary(BaseModel):
    date: str
    total_revenue: Decimal
    total_sales: int


class TopSKU(BaseModel):
    sku_id: str
    name: str
    total_quantity: int
    total_revenue: Decimal


class AnalyticsSummary(BaseModel):
    today_revenue: Decimal
    today_sales: int
    last_7_days: List[DailySummary]
    top_skus: List[TopSKU]