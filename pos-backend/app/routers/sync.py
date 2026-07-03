from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/batch", response_model=schemas.SyncBatchOut)
def sync_batch(payload: schemas.SyncBatchIn, db: Session = Depends(get_db)):
    shop = db.query(models.Shop).filter(models.Shop.id == payload.shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Unknown shop_id")

    # ── Step 1: upsert new SKUs ──────────────────────────────────────────────
    sku_id_map = {}  # client_id -> server id

    for s in payload.new_skus:
        existing = (
            db.query(models.SKU)
            .filter(
                models.SKU.shop_id == payload.shop_id,
                models.SKU.client_id == s.client_id,
            )
            .first()
        )
        if existing:
            sku_id_map[s.client_id] = existing.id
            continue

        sku = models.SKU(
            shop_id=payload.shop_id,
            client_id=s.client_id,
            product_id=None,  # unlinked until owner assigns from inventory
            name=s.name,
            selling_price=s.selling_price,
            buying_price=s.buying_price,
            needs_cost_review=(s.buying_price is None),
            created_via=models.CreatedVia.quick_add,
        )
        db.add(sku)
        db.flush()
        sku_id_map[s.client_id] = sku.id

    # ── Step 2: upsert sales ─────────────────────────────────────────────────
    synced_sale_ids = {}
    skipped_duplicates = []

    for s in payload.sales:
        existing_sale = (
            db.query(models.Sale)
            .filter(
                models.Sale.shop_id == payload.shop_id,
                models.Sale.client_id == s.client_id,
            )
            .first()
        )
        if existing_sale:
            skipped_duplicates.append(s.client_id)
            synced_sale_ids[s.client_id] = existing_sale.id
            continue

        sale = models.Sale(
            shop_id=payload.shop_id,
            client_id=s.client_id,
            shopkeeper_id=s.shopkeeper_id,
            sold_at=s.sold_at,
            total_amount=s.total_amount,
        )
        db.add(sale)
        db.flush()

        for item in s.items:
            # Resolve the SKU id — either already known (server id) or
            # created in this same batch (client id -> server id via map)
            resolved_sku_id = item.sku_id
            if resolved_sku_id is None:
                if item.sku_client_id is None:
                    raise HTTPException(
                        status_code=400,
                        detail="sale item missing both sku_id and sku_client_id",
                    )
                resolved_sku_id = sku_id_map.get(item.sku_client_id)
                if resolved_sku_id is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"sku_client_id {item.sku_client_id} not in this batch",
                    )

            db.add(models.SaleItem(
                sale_id=sale.id,
                sku_id=resolved_sku_id,
                quantity=item.quantity,
                unit_price_at_sale=item.unit_price_at_sale,
                line_total=item.unit_price_at_sale * item.quantity,
            ))

            # Decrement stock only for tracked SKUs
            sku = db.query(models.SKU).filter(models.SKU.id == resolved_sku_id).first()
            if sku and sku.stock_qty is not None:
                sku.stock_qty = max(0, sku.stock_qty - item.quantity)

        synced_sale_ids[s.client_id] = sale.id

    db.commit()

    return schemas.SyncBatchOut(
        synced_sku_ids=sku_id_map,
        synced_sale_ids=synced_sale_ids,
        skipped_duplicate_sales=skipped_duplicates,
    )