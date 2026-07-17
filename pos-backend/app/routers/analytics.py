from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from .. import models, schemas
from ..database import get_db
from .auth import get_shopkeeper_by_token

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sales", response_model=List[schemas.SaleOut])
def get_sales_history(
    shop_id: str = None,
    limit: int = 50,
    offset: int = 0,
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

    query = (
        db.query(models.Sale)
        .join(models.Shopkeeper, models.Sale.shopkeeper_id == models.Shopkeeper.id)
    )
    
    if shop_id:
        query = query.filter(models.Sale.shop_id == shop_id)

    sales = (
        query
        .order_by(models.Sale.sold_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    # Build response with shopkeeper names and SKU names
    result = []
    for sale in sales:
        shopkeeper_name = sale.shopkeeper.name if sale.shopkeeper else None
        
        items = []
        for item in sale.items:
            sku_name = item.sku.name if item.sku else None
            items.append({
                "id": item.id,
                "sku_id": item.sku_id,
                "quantity": item.quantity,
                "unit_price_at_sale": item.unit_price_at_sale,
                "line_total": item.line_total,
                "sku_name": sku_name,
            })
        
        result.append({
            "id": sale.id,
            "total_amount": sale.total_amount,
            "sold_at": sale.sold_at,
            "shopkeeper_id": sale.shopkeeper_id,
            "shopkeeper_name": shopkeeper_name,
            "items": items,
        })

    return result


@router.get("/dead-capital", response_model=schemas.DeadCapitalReport)
def get_dead_capital(
    days_threshold: int = 14,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    shopkeeper = get_shopkeeper_by_token(token, db)

    shop_id = None
    if shopkeeper.role == "shopkeeper":
        shop_id = shopkeeper.shop_id

    cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

    # Find SKUs with stock but no sales in the threshold period
    sku_sales = (
        db.query(
            models.SaleItem.sku_id,
            func.sum(models.SaleItem.quantity).label("total_sold"),
        )
        .join(models.Sale, models.SaleItem.sale_id == models.Sale.id)
        .filter(models.Sale.sold_at >= cutoff_date)
        .group_by(models.SaleItem.sku_id)
        .subquery()
    )

    # Get all SKUs with stock
    skus_with_stock = (
        db.query(models.SKU)
        .filter(models.SKU.stock_qty.isnot(None))
        .filter(models.SKU.stock_qty > 0)
    )
    
    if shop_id:
        skus_with_stock = skus_with_stock.filter(models.SKU.shop_id == shop_id)

    dead_capital_items = []
    total_trapped = Decimal("0")

    for sku in skus_with_stock.all():
        # Check if this SKU had sales in the period
        had_sales = (
            db.query(sku_sales)
            .filter(sku_sales.c.sku_id == sku.id)
            .first()
        )

        if not had_sales or had_sales.total_sold == 0:
            trapped = (sku.buying_price or 0) * (sku.stock_qty or 0)
            total_trapped += trapped
            
            # Calculate days since last sale
            last_sale = (
                db.query(func.max(models.Sale.sold_at))
                .join(models.SaleItem, models.Sale.id == models.SaleItem.sale_id)
                .filter(models.SaleItem.sku_id == sku.id)
                .scalar()
            )
            
            days_without = 0
            if last_sale:
                days_without = (datetime.utcnow() - last_sale).days
            else:
                days_without = 999  # Never sold

            dead_capital_items.append({
                "sku_id": sku.id,
                "sku_name": sku.name,
                "buying_price": sku.buying_price,
                "stock_qty": sku.stock_qty,
                "days_without_sales": days_without,
                "trapped_capital": trapped,
            })

    return schemas.DeadCapitalReport(
        total_trapped_capital=total_trapped,
        items=dead_capital_items,
    )


@router.get("/profit-matrix", response_model=schemas.ProfitMatrixReport)
def get_profit_matrix(
    days: int = 30,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    shopkeeper = get_shopkeeper_by_token(token, db)

    shop_id = None
    if shopkeeper.role == "shopkeeper":
        shop_id = shopkeeper.shop_id

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get sales data per SKU
    sku_data = (
        db.query(
            models.SaleItem.sku_id,
            models.SKU.name,
            func.sum(models.SaleItem.quantity).label("total_quantity"),
            func.sum(models.SaleItem.line_total).label("total_revenue"),
        )
        .join(models.SKU, models.SaleItem.sku_id == models.SKU.id)
        .join(models.Sale, models.SaleItem.sale_id == models.Sale.id)
        .filter(models.Sale.sold_at >= cutoff_date)
    )
    
    if shop_id:
        sku_data = sku_data.filter(models.Sale.shop_id == shop_id)

    sku_data = sku_data.group_by(models.SaleItem.sku_id, models.SKU.name).all()

    items = []
    total_profit = Decimal("0")
    total_revenue = Decimal("0")
    total_cost = Decimal("0")

    for row in sku_data:
        # Calculate cost (using buying price if available)
        sku = db.query(models.SKU).filter(models.SKU.id == row.sku_id).first()
        cost_per_unit = sku.buying_price if sku and sku.buying_price else Decimal("0")
        total_cost_value = cost_per_unit * row.total_quantity
        profit = row.total_revenue - total_cost_value
        margin = (profit / row.total_revenue * 100) if row.total_revenue > 0 else Decimal("0")

        # Categorize
        if margin > 20 and row.total_quantity > 10:
            category = "profit_generator"
        elif row.total_quantity > 50 and margin < 10:
            category = "high_volume_low_margin"
        else:
            category = "low_volume"

        items.append({
            "sku_id": row.sku_id,
            "sku_name": row.name,
            "total_sales_volume": row.total_quantity,
            "total_revenue": row.total_revenue,
            "total_cost": total_cost_value,
            "net_profit": profit,
            "profit_margin_percent": margin,
            "category": category,
        })

        total_profit += profit
        total_revenue += row.total_revenue
        total_cost += total_cost_value

    return schemas.ProfitMatrixReport(
        total_profit=total_profit,
        total_revenue=total_revenue,
        total_cost=total_cost,
        items=items,
    )


@router.get("/restock-prediction", response_model=schemas.RestockPredictionReport)
def get_restock_prediction(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    shopkeeper = get_shopkeeper_by_token(token, db)

    shop_id = None
    if shopkeeper.role == "shopkeeper":
        shop_id = shopkeeper.shop_id

    # Calculate daily sales rate for each SKU (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    sku_sales = (
        db.query(
            models.SaleItem.sku_id,
            func.sum(models.SaleItem.quantity).label("total_sold_30d"),
        )
        .join(models.Sale, models.SaleItem.sale_id == models.Sale.id)
        .filter(models.Sale.sold_at >= thirty_days_ago)
        .group_by(models.SaleItem.sku_id)
        .subquery()
    )

    # Get SKUs with stock
    skus = db.query(models.SKU).filter(
        models.SKU.stock_qty.isnot(None),
        models.SKU.stock_qty > 0
    )
    
    if shop_id:
        skus = skus.filter(models.SKU.shop_id == shop_id)

    urgent_items = []
    soon_items = []
    normal_items = []

    for sku in skus.all():
        sales_data = db.query(sku_sales).filter(sku_sales.c.sku_id == sku.id).first()
        daily_rate = sales_data.total_sold_30d / 30 if sales_data else 0

        if daily_rate > 0:
            days_until_out = sku.stock_qty / daily_rate
        else:
            days_until_out = None

        # Determine priority
        if days_until_out is not None and days_until_out <= 3:
            priority = "urgent"
            suggested_order = int(daily_rate * 14)  # 2 weeks supply
            urgent_items.append({
                "sku_id": sku.id,
                "sku_name": sku.name,
                "current_stock": sku.stock_qty,
                "daily_sales_rate": daily_rate,
                "days_until_stockout": days_until_out,
                "priority": priority,
                "suggested_order_qty": suggested_order,
            })
        elif days_until_out is not None and days_until_out <= 7:
            priority = "soon"
            suggested_order = int(daily_rate * 7)  # 1 week supply
            soon_items.append({
                "sku_id": sku.id,
                "sku_name": sku.name,
                "current_stock": sku.stock_qty,
                "daily_sales_rate": daily_rate,
                "days_until_stockout": days_until_out,
                "priority": priority,
                "suggested_order_qty": suggested_order,
            })
        elif days_until_out is not None:
            priority = "normal"
            normal_items.append({
                "sku_id": sku.id,
                "sku_name": sku.name,
                "current_stock": sku.stock_qty,
                "daily_sales_rate": daily_rate,
                "days_until_stockout": days_until_out,
                "priority": priority,
                "suggested_order_qty": None,
            })

    return schemas.RestockPredictionReport(
        urgent_items=urgent_items,
        soon_items=soon_items,
        normal_items=normal_items,
    )


@router.get("/keeper-audit", response_model=schemas.KeeperAuditReport)
def get_keeper_audit(
    days: int = 7,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    shopkeeper = get_shopkeeper_by_token(token, db)

    shop_id = None
    if shopkeeper.role == "shopkeeper":
        shop_id = shopkeeper.shop_id

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get sales by shopkeeper
    sales_by_keeper = (
        db.query(
            models.Shopkeeper.id,
            models.Shopkeeper.name,
            func.min(models.Sale.sold_at).label("shift_start"),
            func.max(models.Sale.sold_at).label("shift_end"),
            func.sum(models.Sale.total_amount).label("total_sales"),
            func.sum(models.SaleItem.quantity).label("total_items"),
        )
        .join(models.Sale, models.Shopkeeper.id == models.Sale.shopkeeper_id)
        .join(models.SaleItem, models.Sale.id == models.SaleItem.sale_id)
        .filter(models.Sale.sold_at >= cutoff_date)
    )
    
    if shop_id:
        sales_by_keeper = sales_by_keeper.filter(models.Sale.shop_id == shop_id)

    sales_by_keeper = sales_by_keeper.group_by(
        models.Shopkeeper.id, models.Shopkeeper.name
    ).all()

    shifts = []
    total_anomalies = 0

    for row in sales_by_keeper:
        anomalies = []
        
        # Check for irregular patterns (simplified anomaly detection)
        # In a real system, this would compare against expected patterns
        if row.total_items < 5 and row.total_sales > 10000:
            anomalies.append("High value with few items - possible price manipulation")
        
        if row.total_items > 100 and row.total_sales < 5000:
            anomalies.append("High volume with low revenue - possible discount abuse")

        # Check for gaps in sales timing
        keeper_sales = (
            db.query(models.Sale.sold_at)
            .filter(models.Sale.shopkeeper_id == row.id)
            .filter(models.Sale.sold_at >= cutoff_date)
            .order_by(models.Sale.sold_at)
            .all()
        )

        for i in range(len(keeper_sales) - 1):
            gap = (keeper_sales[i + 1].sold_at - keeper_sales[i].sold_at).total_seconds() / 3600
            if gap > 4:  # 4+ hour gap during a shift
                anomalies.append(f"Unusual {int(gap)}h gap in sales activity")

        total_anomalies += len(anomalies)

        shifts.append({
            "shopkeeper_id": row.id,
            "shopkeeper_name": row.name,
            "shift_start": row.shift_start,
            "shift_end": row.shift_end,
            "total_sales": row.total_sales or Decimal("0"),
            "total_items_sold": row.total_items or 0,
            "anomalies": anomalies,
        })

    return schemas.KeeperAuditReport(
        shifts=shifts,
        total_anomalies=total_anomalies,
    )


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