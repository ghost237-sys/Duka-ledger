# POS Backend Skeleton

## Run it
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Defaults to a local SQLite file (`pos_dev.db`) — zero setup. For production,
set `DATABASE_URL` to a Postgres connection string before starting:
```bash
export DATABASE_URL="postgresql://user:password@host:5432/posdb"
```

## Try it
```bash
# Create a shop
curl -X POST "http://127.0.0.1:8000/shops?name=Mama+Njeri+Shop"

# Simulate a phone syncing offline activity: a quick-added product
# (no buying price yet) plus a sale of it, in ONE call.
curl -X POST http://127.0.0.1:8000/sync/batch \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": "<shop id from above>",
    "new_products": [
      {"client_id": "client-prod-001", "name": "Kiwi Shoe Polish", "selling_price": 150}
    ],
    "sales": [{
      "client_id": "client-sale-001",
      "sold_at": "2026-06-20T10:15:00",
      "total_amount": 300,
      "items": [
        {"product_client_id": "client-prod-001", "quantity": 2, "unit_price_at_sale": 150}
      ]
    }]
  }'
```
Send the exact same request again — `skipped_duplicate_sales` will show it
was caught, nothing gets duplicated.

Check the "finish setting up these items" queue (products sold with no cost yet):
```bash
curl "http://127.0.0.1:8000/products/needs-cost-review?shop_id=<shop id>"
```

## Key design decisions (why it's built this way)

- **No inventory pre-load.** Catalog starts empty per shop and grows from
  Quick Add at checkout. There is no "go set up your products first" step.
- **`client_id` on products AND sales.** Generated on the phone the instant
  something is created/sold — before any network call. This is what makes
  offline creation and offline sales possible, and what makes re-syncing a
  batch safe to retry (idempotent dedup on `(shop_id, client_id)`).
- **`buying_price` is nullable forever.** A product is fully sellable with
  just a selling price. `needs_cost_review` auto-flags it so margin reports
  can exclude it until someone fills the cost in — never a blocker.
- **`stock_qty` is nullable per product, not a global switch.** `NULL` =
  not tracked, a number = tracked. Shopkeepers opt in per item, not all at once.
- **One `/sync/batch` endpoint, not separate product/sale endpoints**,
  because a phone coming back online may have BOTH a freshly quick-added
  product AND a sale of that exact product to push up — they have to be
  resolved together, in one transaction, in the right order (products first,
  so sale items can resolve `product_client_id` → real product id).
- **Price snapshot on sale items** (`unit_price_at_sale`). If you change a
  product's selling price next month, last month's sales must not silently
  change value.

## Not yet built (next steps)
- Auth (so one shop can't sync/read another shop's data)
- Stock-decrement-only-if-tracked is implemented but no "low stock" alerting yet
- The PWA frontend (IndexedDB storage + the actual Quick Add UI + background sync trigger)
- Alembic migrations for production schema changes
