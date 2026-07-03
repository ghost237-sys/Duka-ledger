from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from decimal import Decimal

from .. import models, schemas
from ..database import get_db
from .auth import get_shopkeeper_by_token

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=schemas.AnalyticsSummary)
def get_summary(
    shop_id: str = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    shopkeeper = get_shopkeeper_by_token(token, db)

    # Shopkeepers locked to their own shop
    if shopkeeper.role == "shopkeeper":
        shop_id = shopkeeper.shop_id

    today = datetime.utcnow().date()

    sale_q = db.query(models.Sale)
    if shop_id:
        sale_q = sale_q.filter(models.Sale.shop_id == shop_id)

    # Today
    today_sales = sale_q.filter(func.date(models.Sale.sold_at) == today).all()
    today_revenue = sum(s.total_amount for s in today_sales)

    # Last 7 days
    last_7 = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_sales = sale_q.filter(func.date(models.Sale.sold_at) == day).all()
        last_7.append(schemas.DailySummary(
            date=str(day),
            total_revenue=Decimal(str(sum(s.total_amount for s in day_sales))),
            total_sales=len(day_sales),
        ))

    # Top SKUs (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    sku_q = (
        db.query(
            models.SaleItem.sku_id,
            models.SKU.name,
            func.sum(models.SaleItem.quantity).label("total_quantity"),
            func.sum(models.SaleItem.line_total).label("total_revenue"),
        )
        .join(models.SKU, models.SaleItem.sku_id == models.SKU.id)
        .join(models.Sale, models.SaleItem.sale_id == models.Sale.id)
        .filter(func.date(models.Sale.sold_at) >= thirty_days_ago)
    )
    if shop_id:
        sku_q = sku_q.filter(models.Sale.shop_id == shop_id)

    top_skus = (
        sku_q
        .group_by(models.SaleItem.sku_id, models.SKU.name)
        .order_by(func.sum(models.SaleItem.quantity).desc())
        .limit(5)
        .all()
    )

    return schemas.AnalyticsSummary(
        today_revenue=Decimal(str(today_revenue)),
        today_sales=len(today_sales),
        last_7_days=last_7,
        top_skus=[
            schemas.TopSKU(
                sku_id=row.sku_id,
                name=row.name,
                total_quantity=row.total_quantity,
                total_revenue=Decimal(str(row.total_revenue)),
            )
            for row in top_skus
        ],
    )