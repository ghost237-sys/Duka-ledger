from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas
from ..database import get_db

router = APIRouter(tags=["catalog"])


# ── Categories ───────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[schemas.CategoryOut])
def list_categories(shop_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Category)
        .filter(models.Category.shop_id == shop_id)
        .order_by(models.Category.sort_order, models.Category.name)
        .all()
    )


@router.post("/categories", response_model=schemas.CategoryOut)
def create_category(shop_id: str, name: str, db: Session = Depends(get_db)):
    existing = db.query(models.Category).filter(
        models.Category.shop_id == shop_id,
        models.Category.name == name,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    cat = models.Category(shop_id=shop_id, name=name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{category_id}")
def delete_category(category_id: str, db: Session = Depends(get_db)):
    cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()
    return {"deleted": category_id}


# ── SKUs (what the checkout screen searches) ─────────────────────────────────

@router.get("/skus", response_model=List[schemas.SKUOut])
def list_skus(shop_id: str, q: str = "", db: Session = Depends(get_db)):
    """
    Full SKU list for phone to download into local SQLite on sync.
    Search is full-text across SKU name, brand name, manufacturer,
    and category name — so 'kidole', 'fresh', 'brook' all find the
    right items regardless of which field the term appears in.
    """
    query = (
        db.query(models.SKU)
        .outerjoin(models.Product, models.SKU.product_id == models.Product.id)
        .outerjoin(models.Category, models.Product.category_id == models.Category.id)
        .filter(
            models.SKU.shop_id == shop_id,
            models.SKU.is_active == True,
        )
    )
    if q:
        term = f"%{q}%"
        from sqlalchemy import or_
        query = query.filter(
            or_(
                models.SKU.name.ilike(term),
                models.Product.brand_name.ilike(term),
                models.Product.manufacturer.ilike(term),
                models.Category.name.ilike(term),
            )
        )
    return query.order_by(models.SKU.name).all()


@router.get("/skus/needs-cost-review", response_model=List[schemas.SKUOut])
def skus_needing_cost_review(shop_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.SKU)
        .filter(
            models.SKU.shop_id == shop_id,
            models.SKU.needs_cost_review == True,
        )
        .all()
    )


# ── Products (parent brands) ─────────────────────────────────────────────────

@router.get("/products", response_model=List[schemas.ProductOut])
def list_products(shop_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Product)
        .filter(
            models.Product.shop_id == shop_id,
            models.Product.is_active == True,
        )
        .order_by(models.Product.brand_name)
        .all()
    )


@router.post("/products", response_model=schemas.ProductOut)
def create_product(
    shop_id: str,
    brand_name: str,
    category_id: Optional[str] = None,
    manufacturer: Optional[str] = None,
    db: Session = Depends(get_db),
):
    import uuid
    product = models.Product(
        shop_id=shop_id,
        client_id=str(uuid.uuid4()),
        brand_name=brand_name,
        category_id=category_id,
        manufacturer=manufacturer,
        created_via=models.CreatedVia.admin,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.post("/products/{product_id}/skus", response_model=schemas.SKUOut)
def add_sku_to_product(
    product_id: str,
    name: str,
    selling_price: float,
    buying_price: Optional[float] = None,
    stock_qty: Optional[int] = None,
    db: Session = Depends(get_db),
):
    import uuid
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    sku = models.SKU(
        shop_id=product.shop_id,
        client_id=str(uuid.uuid4()),
        product_id=product_id,
        name=name,
        selling_price=selling_price,
        buying_price=buying_price,
        needs_cost_review=(buying_price is None),
        stock_qty=stock_qty,
        created_via=models.CreatedVia.admin,
    )
    db.add(sku)
    db.commit()
    db.refresh(sku)
    return sku


@router.patch("/skus/{sku_id}", response_model=schemas.SKUOut)
def update_sku(
    sku_id: str,
    name: Optional[str] = None,
    selling_price: Optional[float] = None,
    buying_price: Optional[float] = None,
    stock_qty: Optional[int] = None,
    product_id: Optional[str] = None,
    category_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Update a SKU — including linking an unlinked Quick Add to a parent product."""
    sku = db.query(models.SKU).filter(models.SKU.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    if name is not None:
        sku.name = name
    if selling_price is not None:
        sku.selling_price = selling_price
    if buying_price is not None:
        sku.buying_price = buying_price
        sku.needs_cost_review = False
    if stock_qty is not None:
        sku.stock_qty = stock_qty
    if product_id is not None:
        sku.product_id = product_id
    if category_id is not None:
        # Find or create a product for this category to link the SKU to
        existing_product = db.query(models.Product).filter(
            models.Product.shop_id == sku.shop_id,
            models.Product.category_id == category_id,
            models.Product.brand_name == sku.name,
        ).first()
        if existing_product:
            sku.product_id = existing_product.id
        else:
            import uuid
            new_product = models.Product(
                shop_id=sku.shop_id,
                client_id=str(uuid.uuid4()),
                brand_name=sku.name,
                category_id=category_id,
                created_via=models.CreatedVia.quick_add,
            )
            db.add(new_product)
            db.flush()
            sku.product_id = new_product.id
    db.commit()
    db.refresh(sku)
    return sku