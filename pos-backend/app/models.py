import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Numeric, Integer, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────
# Enums
# ─────────────────────────────────────────

class ShopkeeperRole(str, enum.Enum):
    owner = "owner"
    shopkeeper = "shopkeeper"


class CreatedVia(str, enum.Enum):
    quick_add = "quick_add"
    admin = "admin"


# ─────────────────────────────────────────
# Shop
# ─────────────────────────────────────────

class Shop(Base):
    __tablename__ = "shops"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    shopkeepers = relationship("Shopkeeper", back_populates="shop")
    categories = relationship("Category", back_populates="shop")
    products = relationship("Product", back_populates="shop")
    sales = relationship("Sale", back_populates="shop")


# ─────────────────────────────────────────
# Shopkeeper
# ─────────────────────────────────────────

class Shopkeeper(Base):
    __tablename__ = "shopkeepers"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)
    pin_hash = Column(String, nullable=False)
    role = Column(SAEnum(ShopkeeperRole), default=ShopkeeperRole.shopkeeper)
    shop_id = Column(String, ForeignKey("shops.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    shop = relationship("Shop", back_populates="shopkeepers")
    sales = relationship("Sale", back_populates="shopkeeper")


# ─────────────────────────────────────────
# Category
# ─────────────────────────────────────────

class Category(Base):
    """
    Fixed list per shop. Owner creates/edits/deletes categories.
    Shopkeepers only pick from the list — never free-type.
    This prevents spelling drift (e.g. "Flour" vs "flour" vs "Unga").
    """
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=gen_uuid)
    shop_id = Column(String, ForeignKey("shops.id"), nullable=False)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    shop = relationship("Shop", back_populates="categories")
    products = relationship("Product", back_populates="category")

    __table_args__ = (
        UniqueConstraint("shop_id", "name", name="uq_category_shop_name"),
    )


# ─────────────────────────────────────────
# Product (parent / brand identity)
# ─────────────────────────────────────────

class Product(Base):
    """
    The brand identity. Things that never change regardless of size or variant.
    e.g. "Jogoo Unga" — brand: Jogoo, category: Unga & Nafaka, manufacturer: Unga Group.
    A product has one or more SKUs (the actual sellable units).
    """
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=gen_uuid)
    client_id = Column(String, nullable=False)
    shop_id = Column(String, ForeignKey("shops.id"), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"), nullable=True)

    brand_name = Column(String, nullable=False)
    manufacturer = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    created_via = Column(SAEnum(CreatedVia), default=CreatedVia.admin)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop = relationship("Shop", back_populates="products")
    category = relationship("Category", back_populates="products")
    skus = relationship("SKU", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("shop_id", "client_id", name="uq_product_shop_clientid"),
    )


# ─────────────────────────────────────────
# SKU (child / specific sellable unit)
# ─────────────────────────────────────────

class SKU(Base):
    """
    The specific thing on the shelf with a price tag.
    e.g. "Jogoo Unga 2kg" — variant: 2kg, selling: 180, buying: 140, stock: 24.

    product_id is NULLABLE — Quick Add creates a bare SKU with no parent product.
    These show as "Unlinked" in inventory until the owner links them to a product.

    client_id is phone-generated so offline Quick Add works before any sync.
    """
    __tablename__ = "skus"

    id = Column(String, primary_key=True, default=gen_uuid)
    client_id = Column(String, nullable=False)
    shop_id = Column(String, ForeignKey("shops.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)

    # The display name used at checkout — either "Jogoo Unga 2kg" (linked)
    # or whatever the shopkeeper typed at Quick Add (unlinked)
    name = Column(String, nullable=False)

    selling_price = Column(Numeric(10, 2), nullable=False)
    buying_price = Column(Numeric(10, 2), nullable=True)
    needs_cost_review = Column(Boolean, default=True)

    # NULL = not tracked. 0 = tracked, currently out of stock.
    stock_qty = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True)
    created_via = Column(SAEnum(CreatedVia), default=CreatedVia.quick_add)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="skus")
    shop = relationship("Shop")

    __table_args__ = (
        UniqueConstraint("shop_id", "client_id", name="uq_sku_shop_clientid"),
    )


# ─────────────────────────────────────────
# Sale
# ─────────────────────────────────────────

class Sale(Base):
    __tablename__ = "sales"

    id = Column(String, primary_key=True, default=gen_uuid)
    client_id = Column(String, nullable=False)
    shop_id = Column(String, ForeignKey("shops.id"), nullable=False)
    shopkeeper_id = Column(String, ForeignKey("shopkeepers.id"), nullable=True)

    total_amount = Column(Numeric(10, 2), nullable=False)
    sold_at = Column(DateTime, nullable=False)
    synced_at = Column(DateTime, default=datetime.utcnow)

    shop = relationship("Shop", back_populates="sales")
    shopkeeper = relationship("Shopkeeper", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("shop_id", "client_id", name="uq_sale_shop_clientid"),
    )


# ─────────────────────────────────────────
# SaleItem
# ─────────────────────────────────────────

class SaleItem(Base):
    """
    Now references SKU not Product — because what was actually sold
    was a specific variant (2kg bag) not just a brand (Jogoo Unga).
    Price snapshot is still kept so historical sales never change value
    when the SKU's selling price is updated later.
    """
    __tablename__ = "sale_items"

    id = Column(String, primary_key=True, default=gen_uuid)
    sale_id = Column(String, ForeignKey("sales.id"), nullable=False)
    sku_id = Column(String, ForeignKey("skus.id"), nullable=False)

    quantity = Column(Integer, nullable=False)
    unit_price_at_sale = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)

    sale = relationship("Sale", back_populates="items")
    sku = relationship("SKU")