import os
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

# ── Hardcoded admin password ─────────────────────────────────────────────────
# Change this to something strong before deploying.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "faida-admin-2024")

# Simple session store — cookie value -> True
_admin_sessions: set = set()


def _check_session(request: Request):
    token = request.cookies.get("admin_session")
    if not token or token not in _admin_sessions:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return True


# ── Login ────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Faida Admin</title>
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui, sans-serif; background: #0f1f14;
               min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .card { background: #fff; border-radius: 12px; padding: 40px; width: 360px; }
        h1 { font-size: 22px; color: #2E5339; margin-bottom: 4px; }
        p { font-size: 13px; color: #888; margin-bottom: 28px; }
        label { display: block; font-size: 11px; font-weight: 700;
                color: #5B574E; letter-spacing: 1px; margin-bottom: 6px; }
        input { width: 100%; padding: 12px; border: 1px solid #D8D2C2;
                border-radius: 8px; font-size: 15px; margin-bottom: 20px; }
        button { width: 100%; padding: 14px; background: #2E5339; color: #fff;
                 border: none; border-radius: 8px; font-weight: 700;
                 font-size: 15px; cursor: pointer; }
        .error { color: #9C3B2E; font-size: 13px; margin-bottom: 16px; font-weight: 600; }
      </style>
    </head>
    <body>
      <div class="card">
        <h1>Faida Admin</h1>
        <p>Internal management panel</p>
        <form method="POST" action="/admin/login">
          <label>PASSWORD</label>
          <input type="password" name="password" autofocus />
          <button type="submit">Sign in</button>
        </form>
      </div>
    </body>
    </html>
    """


@router.post("/login")
def login_submit(request: Request, password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        return HTMLResponse("""
        <!DOCTYPE html><html><head><meta charset="UTF-8"/>
        <title>Faida Admin</title>
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { font-family: system-ui, sans-serif; background: #0f1f14;
                 min-height: 100vh; display: flex; align-items: center; justify-content: center; }
          .card { background: #fff; border-radius: 12px; padding: 40px; width: 360px; }
          h1 { font-size: 22px; color: #2E5339; margin-bottom: 4px; }
          p { font-size: 13px; color: #888; margin-bottom: 28px; }
          label { display: block; font-size: 11px; font-weight: 700;
                  color: #5B574E; letter-spacing: 1px; margin-bottom: 6px; }
          input { width: 100%; padding: 12px; border: 1px solid #D8D2C2;
                  border-radius: 8px; font-size: 15px; margin-bottom: 20px; }
          button { width: 100%; padding: 14px; background: #2E5339; color: #fff;
                   border: none; border-radius: 8px; font-weight: 700;
                   font-size: 15px; cursor: pointer; }
          .error { color: #9C3B2E; font-size: 13px; margin-bottom: 16px; font-weight: 600; }
        </style>
        </head><body>
          <div class="card">
            <h1>Faida Admin</h1>
            <p>Internal management panel</p>
            <div class="error">Wrong password. Try again.</div>
            <form method="POST" action="/admin/login">
              <label>PASSWORD</label>
              <input type="password" name="password" autofocus />
              <button type="submit">Sign in</button>
            </form>
          </div>
        </body></html>
        """, status_code=401)

    import secrets
    token = secrets.token_hex(32)
    _admin_sessions.add(token)
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie("admin_session", token, httponly=True)
    return response


@router.get("/logout")
def logout(request: Request):
    token = request.cookies.get("admin_session")
    _admin_sessions.discard(token)
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response


# ── Dashboard ─────────────────────────────────────────────────────────────────

def _nav():
    return """
    <nav>
      <span class="logo">Faida Admin</span>
      <div class="nav-links">
        <a href="/admin">Dashboard</a>
        <a href="/admin/shops">Shops</a>
        <a href="/admin/owners">Owners</a>
        <a href="/admin/logout">Logout</a>
      </div>
    </nav>
    """


def _base(title: str, body: str):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>{title} — Faida Admin</title>
      <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: system-ui, sans-serif; background: #F5F5F0; color: #211F1B; }}
        nav {{ background: #2E5339; padding: 14px 28px; display: flex;
               align-items: center; justify-content: space-between; }}
        .logo {{ color: #fff; font-weight: 900; font-size: 18px; letter-spacing: 2px; }}
        .nav-links a {{ color: rgba(255,255,255,0.8); text-decoration: none;
                        margin-left: 24px; font-size: 14px; font-weight: 600; }}
        .nav-links a:hover {{ color: #fff; }}
        .container {{ max-width: 1000px; margin: 32px auto; padding: 0 24px; }}
        h1 {{ font-size: 24px; margin-bottom: 24px; }}
        h2 {{ font-size: 16px; margin-bottom: 14px; color: #2E5339; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }}
        .stat {{ background: #fff; border-radius: 10px; padding: 20px;
                 border: 1px solid #D8D2C2; }}
        .stat-label {{ font-size: 11px; font-weight: 700; color: #888;
                       letter-spacing: 1px; margin-bottom: 8px; }}
        .stat-value {{ font-size: 28px; font-weight: 900; color: #2E5339; }}
        .card {{ background: #fff; border-radius: 10px; border: 1px solid #D8D2C2;
                 padding: 24px; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; font-size: 11px; font-weight: 700; color: #888;
              letter-spacing: 1px; padding: 8px 12px; border-bottom: 2px solid #D8D2C2; }}
        td {{ padding: 12px; border-bottom: 1px solid #F0EDE6; font-size: 14px; }}
        tr:last-child td {{ border-bottom: none; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px;
                  font-size: 11px; font-weight: 700; }}
        .badge-owner {{ background: #E1EAE3; color: #2E5339; }}
        .badge-shopkeeper {{ background: #FBE9DA; color: #C2703D; }}
        form {{ display: flex; flex-direction: column; gap: 12px; }}
        label {{ font-size: 11px; font-weight: 700; color: #888; letter-spacing: 1px; }}
        input, select {{ padding: 10px 12px; border: 1px solid #D8D2C2;
                         border-radius: 8px; font-size: 14px; width: 100%; }}
        .form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        button[type=submit] {{ padding: 12px; background: #2E5339; color: #fff;
                               border: none; border-radius: 8px; font-weight: 700;
                               font-size: 14px; cursor: pointer; margin-top: 4px; }}
        .danger {{ color: #9C3B2E; }}
        a.del {{ color: #9C3B2E; font-size: 13px; text-decoration: none; font-weight: 600; }}
      </style>
    </head>
    <body>
      {_nav()}
      <div class="container">
        {body}
      </div>
    </body>
    </html>
    """


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    _check_session(request)

    total_shops = db.query(models.Shop).count()
    total_owners = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.role == "owner"
    ).count()
    total_shopkeepers = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.role == "shopkeeper"
    ).count()
    total_sales = db.query(models.Sale).count()

    body = f"""
    <h1>Dashboard</h1>
    <div class="stats">
      <div class="stat"><div class="stat-label">SHOPS</div>
        <div class="stat-value">{total_shops}</div></div>
      <div class="stat"><div class="stat-label">OWNERS</div>
        <div class="stat-value">{total_owners}</div></div>
      <div class="stat"><div class="stat-label">SHOPKEEPERS</div>
        <div class="stat-value">{total_shopkeepers}</div></div>
      <div class="stat"><div class="stat-label">TOTAL SALES</div>
        <div class="stat-value">{total_sales}</div></div>
    </div>
    <div class="card">
      <h2>Quick Links</h2>
      <p style="font-size:14px;color:#888;line-height:1.8">
        <a href="/admin/shops">Manage Shops →</a><br/>
        <a href="/admin/owners">Manage Owners →</a><br/>
        <a href="/docs">API Docs →</a>
      </p>
    </div>
    """
    return _base("Dashboard", body)


# ── Shops ─────────────────────────────────────────────────────────────────────

@router.get("/shops", response_class=HTMLResponse)
def shops_page(request: Request, db: Session = Depends(get_db)):
    _check_session(request)
    shops = db.query(models.Shop).order_by(models.Shop.created_at.desc()).all()

    rows = ""
    for s in shops:
        keeper_count = db.query(models.Shopkeeper).filter(
            models.Shopkeeper.shop_id == s.id
        ).count()
        sku_count = db.query(models.SKU).filter(
            models.SKU.shop_id == s.id
        ).count()
        owner = db.query(models.Shopkeeper).filter(
            models.Shopkeeper.shop_id == s.id,
            models.Shopkeeper.role == "owner",
        ).first()
        rows += f"""
        <tr>
          <td><strong>{s.name}</strong></td>
          <td style="font-family:monospace;font-size:11px;color:#888">{s.id}</td>
          <td>{owner.name if owner else '—'}<br/>
            <span style="font-size:11px;color:#888">{owner.phone if owner else ''}</span>
          </td>
          <td>{keeper_count} staff · {sku_count} SKUs</td>
          <td>{s.created_at.strftime('%d %b %Y')}</td>
          <td>
            <a href="/admin/shops/{s.id}/edit" style="color:#2E5339;font-weight:700;font-size:13px;text-decoration:none;margin-right:12px">Edit</a>
            <a href="/admin/shops/{s.id}/delete"
               onclick="return confirm('Delete {s.name} and ALL its data? This cannot be undone.')"
               style="color:#9C3B2E;font-weight:700;font-size:13px;text-decoration:none">Delete</a>
          </td>
        </tr>"""

    body = f"""
    <h1>Shops</h1>
    <div class="card" style="margin-bottom:24px">
      <h2>Create New Shop</h2>
      <form method="POST" action="/admin/shops">
        <div class="form-row">
          <div><label>SHOP NAME</label><input name="name" placeholder="e.g. Mama Njeri Shop" required/></div>
          <div><label>OWNER NAME</label><input name="owner_name" placeholder="e.g. Jane Wanjiru" required/></div>
        </div>
        <div class="form-row">
          <div><label>OWNER PHONE</label><input name="owner_phone" placeholder="e.g. 0712345678" required/></div>
          <div><label>OWNER PIN</label><input name="owner_pin" type="password" placeholder="4 digits" required/></div>
        </div>
        <button type="submit">Create Shop + Owner Account</button>
      </form>
    </div>
    <div class="card">
      <h2>All Shops ({len(shops)})</h2>
      <table>
        <tr><th>NAME</th><th>ID</th><th>OWNER</th><th>STATS</th><th>CREATED</th><th>ACTIONS</th></tr>
        {rows}
      </table>
    </div>
    """
    return _base("Shops", body)


def _seed_catalog(db, shop_id: str, cat_map: dict):
    """
    Seeds every new shop with the most common Kenyan duka products.
    Prices are set to 0 — the shopkeeper sets real prices from inventory.
    Products with price 0 are flagged needs_price_setup in the mobile app.

    Structure: each entry is (brand_name, manufacturer, category_name, [variants])
    Each variant is (variant_name) — price seeded at 0.
    """
    import uuid

    catalog = [
        # ── Unga & Nafaka ────────────────────────────────────────────────────
        ("Jogoo Unga", "Unga Limited", "Unga & Nafaka", ["2kg", "1kg"]),
        ("Pembe Unga", "Pembe Flour Mills", "Unga & Nafaka", ["2kg", "1kg"]),
        ("Dola Unga", "Unga Limited", "Unga & Nafaka", ["2kg", "1kg"]),
        ("Soko Unga", "Unga Limited", "Unga & Nafaka", ["2kg", "1kg"]),
        ("Ajab Wheat Flour", "Ajab", "Unga & Nafaka", ["2kg", "1kg"]),
        ("Amaize", "Amaize", "Unga & Nafaka", ["2kg", "1kg"]),
        ("Wimbi Uji", "Famila", "Unga & Nafaka", ["500g", "1kg"]),
        ("Soko Rice", "Soko", "Unga & Nafaka", ["2kg", "1kg", "500g"]),
        ("Pishori Rice", "Mwea Pishori", "Unga & Nafaka", ["1kg", "500g"]),
        ("Ndovu Unga", "Ndovu", "Unga & Nafaka", ["2kg", "1kg"]),
        ("Hostess Unga", "Unga Limited", "Unga & Nafaka", ["2kg", "1kg"]),

        # ── Sukari & Chumvi ──────────────────────────────────────────────────
        ("Kabras Sugar", "Kabras Sugar", "Sukari & Chumvi", ["2kg", "1kg", "500g"]),
        ("Mumias Sugar", "Mumias Sugar", "Sukari & Chumvi", ["2kg", "1kg", "500g"]),
        ("West Kenya Sugar", "West Kenya Sugar", "Sukari & Chumvi", ["2kg", "1kg"]),
        ("Kensalt", "Kensalt", "Sukari & Chumvi", ["500g", "250g", "1kg"]),
        ("Cookswell Salt", "Cookswell", "Sukari & Chumvi", ["500g", "250g"]),
        ("Royco Mchuzi Mix", "Unilever", "Sukari & Chumvi", ["75g sachet", "200g"]),
        ("Mchuzi Mix", "Kenchic", "Sukari & Chumvi", ["75g sachet"]),

        # ── Mafuta ya Kupika ─────────────────────────────────────────────────
        ("Fresh Fri", "Bidco", "Mafuta ya Kupika", ["2L", "1L", "500ml"]),
        ("Elianto", "Bidco", "Mafuta ya Kupika", ["2L", "1L", "500ml"]),
        ("Fri-King", "Kapa Oil", "Mafuta ya Kupika", ["2L", "1L", "500ml"]),
        ("Golden Fry", "Kapa Oil", "Mafuta ya Kupika", ["2L", "1L", "500ml"]),
        ("Ndume Ghee", "Ndume", "Mafuta ya Kupika", ["400g", "200g"]),
        ("Cowboy Cooking Fat", "Bidco", "Mafuta ya Kupika", ["500g", "250g"]),
        ("Rina Cooking Oil", "Rina", "Mafuta ya Kupika", ["1L", "500ml"]),

        # ── Vinywaji ─────────────────────────────────────────────────────────
        ("Coca-Cola", "Coca-Cola", "Vinywaji", ["500ml", "300ml", "1L", "2L"]),
        ("Fanta Orange", "Coca-Cola", "Vinywaji", ["500ml", "300ml"]),
        ("Fanta Passion", "Coca-Cola", "Vinywaji", ["500ml", "300ml"]),
        ("Sprite", "Coca-Cola", "Vinywaji", ["500ml", "300ml"]),
        ("Stoney Tangawizi", "Coca-Cola", "Vinywaji", ["500ml", "300ml"]),
        ("Alvaro", "East African Breweries", "Vinywaji", ["500ml", "330ml"]),
        ("Novida", "East African Breweries", "Vinywaji", ["500ml", "330ml"]),
        ("Minute Maid", "Coca-Cola", "Vinywaji", ["500ml", "300ml"]),
        ("Afia Juice", "Juhayna", "Vinywaji", ["500ml", "250ml"]),
        ("Dasani Water", "Coca-Cola", "Vinywaji", ["500ml", "1L"]),
        ("Keringet Water", "Keringet", "Vinywaji", ["500ml", "1L"]),
        ("Highlands Water", "Highlands", "Vinywaji", ["500ml", "1L"]),
        ("Predator Energy", "Coca-Cola", "Vinywaji", ["500ml", "250ml"]),
        ("Monster Energy", "Coca-Cola", "Vinywaji", ["500ml"]),
        ("Mirinda", "PepsiCo", "Vinywaji", ["500ml", "300ml"]),
        ("Pepsi", "PepsiCo", "Vinywaji", ["500ml", "300ml"]),
        ("Ribena", "Suntory", "Vinywaji", ["500ml", "250ml"]),

        # ── Maziwa & Mayai ───────────────────────────────────────────────────
        ("Brookside Milk", "Brookside", "Maziwa & Mayai", ["500ml", "1L"]),
        ("Fresha Milk", "Fresha", "Maziwa & Mayai", ["500ml", "1L"]),
        ("KCC Milk", "KCC", "Maziwa & Mayai", ["500ml", "1L"]),
        ("Mala", "Brookside", "Maziwa & Mayai", ["500ml", "1L"]),
        ("Tuzo Milk", "Tuzo", "Maziwa & Mayai", ["500ml", "1L"]),
        ("Blue Band", "Upfield", "Maziwa & Mayai", ["500g", "250g", "30g"]),
        ("Eggs", "", "Maziwa & Mayai", ["1 piece", "6 pack", "tray (30)"]),
        ("Illovo Yoghurt", "Illovo", "Maziwa & Mayai", ["150ml", "500ml"]),

        # ── Mkate & Mandazi ──────────────────────────────────────────────────
        ("Supa Loaf", "Supa Loaf", "Mkate & Mandazi", ["400g", "600g"]),
        ("Festive Bread", "Festive", "Mkate & Mandazi", ["400g", "600g"]),
        ("Bakers Inn", "Bakers Inn", "Mkate & Mandazi", ["400g", "600g"]),
        ("Mandazi", "", "Mkate & Mandazi", ["1 piece", "3 pack"]),
        ("Chapati", "", "Mkate & Mandazi", ["1 piece", "3 pack"]),

        # ── Sabuni & Usafi ───────────────────────────────────────────────────
        ("Omo Detergent", "Unilever", "Sabuni & Usafi", ["1kg", "500g", "200g", "90g"]),
        ("Ariel Detergent", "Procter & Gamble", "Sabuni & Usafi", ["1kg", "500g", "200g"]),
        ("Sunlight Detergent", "Unilever", "Sabuni & Usafi", ["500g", "200g", "1kg"]),
        ("Sunlight Soap", "Unilever", "Sabuni & Usafi", ["1 bar", "3 pack"]),
        ("Geisha Soap", "Kapa Oil", "Sabuni & Usafi", ["1 bar", "3 pack"]),
        ("Protex Soap", "Colgate-Palmolive", "Sabuni & Usafi", ["1 bar", "3 pack"]),
        ("Dettol Soap", "Reckitt", "Sabuni & Usafi", ["1 bar", "3 pack"]),
        ("Harpic", "Reckitt", "Sabuni & Usafi", ["500ml", "1L"]),
        ("Jik Bleach", "SC Johnson", "Sabuni & Usafi", ["1L", "500ml"]),
        ("Vim Powder", "Unilever", "Sabuni & Usafi", ["500g", "200g"]),
        ("Domestos", "Unilever", "Sabuni & Usafi", ["750ml", "500ml"]),
        ("Dettol Liquid", "Reckitt", "Sabuni & Usafi", ["500ml", "250ml"]),

        # ── Karatasi & Choo ──────────────────────────────────────────────────
        ("Softex Tissue", "Softex", "Karatasi & Choo", ["10 pack", "4 pack", "single"]),
        ("Kleenex", "Kimberly-Clark", "Karatasi & Choo", ["10 pack", "4 pack"]),
        ("White Tissue", "White", "Karatasi & Choo", ["10 pack", "4 pack"]),
        ("Always Pads", "Procter & Gamble", "Karatasi & Choo", ["8 pack", "14 pack"]),
        ("Kotex Pads", "Kimberly-Clark", "Karatasi & Choo", ["8 pack", "14 pack"]),
        ("Pampers Diapers", "Procter & Gamble", "Karatasi & Choo", ["10 pack", "20 pack", "single"]),
        ("Huggies", "Kimberly-Clark", "Karatasi & Choo", ["10 pack", "20 pack"]),

        # ── Dawa za Mwili ────────────────────────────────────────────────────
        ("Arimis Jelly", "Tri-Clover", "Dawa za Mwili", ["50g", "100g", "250g"]),
        ("Vaseline", "Unilever", "Dawa za Mwili", ["50g", "100g", "250g"]),
        ("Dawn Skin Light", "Dawn", "Dawa za Mwili", ["50g", "100g"]),
        ("Nivea Lotion", "Beiersdorf", "Dawa za Mwili", ["50ml", "100ml", "200ml"]),
        ("Movit Jelly", "Movit", "Dawa za Mwili", ["50g", "100g"]),
        ("Ori Olive Jelly", "Ori", "Dawa za Mwili", ["50g", "100g"]),

        # ── Nywele ───────────────────────────────────────────────────────────
        ("Dark & Lovely", "Revlon", "Nywele", ["1 pack"]),
        ("Dax Hair Grease", "Dax", "Nywele", ["50g", "100g"]),
        ("Africa's Best", "Soft Sheen Carson", "Nywele", ["1 pack"]),
        ("Relaxer (TCB)", "Alberto Culver", "Nywele", ["1 pack"]),
        ("Comb (Plastic)", "", "Nywele", ["1 piece"]),
        ("Hair Pins", "", "Nywele", ["1 pack"]),

        # ── Viatu & Nguo ─────────────────────────────────────────────────────
        ("Kiwi Shoe Polish Black", "Kiwi", "Viatu & Nguo", ["100ml", "50ml"]),
        ("Kiwi Shoe Polish Brown", "Kiwi", "Viatu & Nguo", ["100ml", "50ml"]),
        ("Tannery Shoe Polish", "Tannery", "Viatu & Nguo", ["100ml", "50ml"]),
        ("Shoe Brush", "", "Viatu & Nguo", ["1 piece"]),

        # ── Simu & Airtime ───────────────────────────────────────────────────
        ("Safaricom Airtime", "Safaricom", "Simu & Airtime", ["10", "20", "50", "100", "200", "500"]),
        ("Airtel Airtime", "Airtel", "Simu & Airtime", ["10", "20", "50", "100"]),
        ("Telkom Airtime", "Telkom", "Simu & Airtime", ["10", "20", "50"]),
        ("Safaricom Data Bundle", "Safaricom", "Simu & Airtime", ["20", "50", "100", "200"]),

        # ── Dawa (OTC Medicine) ──────────────────────────────────────────────
        ("Panadol", "GSK", "Dawa", ["2 tabs", "strip (10)", "24 tabs"]),
        ("Aspirin", "Bayer", "Dawa", ["2 tabs", "strip (10)"]),
        ("Hedex", "GSK", "Dawa", ["2 tabs", "strip (10)"]),
        ("Eno Salts", "GSK", "Dawa", ["sachet", "150g"]),
        ("Gelusil", "Pfizer", "Dawa", ["2 tabs", "strip (10)"]),
        ("Strepsils", "Reckitt", "Dawa", ["2 tabs", "strip (8)"]),
        ("ORS Sachet", "", "Dawa", ["1 sachet", "10 pack"]),

        # ── Sigara & Pombe ───────────────────────────────────────────────────
        ("Supermatch Cigarettes", "BAT Kenya", "Sigara & Pombe", ["1 stick", "10 pack", "20 pack"]),
        ("Rooster Cigarettes", "BAT Kenya", "Sigara & Pombe", ["1 stick", "10 pack", "20 pack"]),
        ("Safari Cigarettes", "BAT Kenya", "Sigara & Pombe", ["1 stick", "10 pack", "20 pack"]),
        ("Embassy Cigarettes", "BAT Kenya", "Sigara & Pombe", ["1 stick", "10 pack", "20 pack"]),
        ("Tusker Lager", "East African Breweries", "Sigara & Pombe", ["500ml", "330ml"]),
        ("Senator Keg", "East African Breweries", "Sigara & Pombe", ["500ml"]),
        ("Pilsner", "East African Breweries", "Sigara & Pombe", ["500ml", "330ml"]),

        # ── Chakula cha Watoto ───────────────────────────────────────────────
        ("Weetabix", "Weetabix", "Chakula cha Watoto", ["430g", "215g"]),
        ("Nestlé Cerelac", "Nestlé", "Chakula cha Watoto", ["400g", "200g"]),
        ("Nestlé Nan", "Nestlé", "Chakula cha Watoto", ["400g", "200g"]),
        ("Uji wa Mtoto", "", "Chakula cha Watoto", ["500g", "250g"]),

        # ── Stationery ───────────────────────────────────────────────────────
        ("Bic Pen (Blue)", "Bic", "Stationery", ["1 piece", "4 pack"]),
        ("Bic Pen (Black)", "Bic", "Stationery", ["1 piece", "4 pack"]),
        ("Exercise Book", "", "Stationery", ["1 piece", "3 pack"]),
        ("Pencil", "", "Stationery", ["1 piece", "4 pack"]),
        ("Envelope", "", "Stationery", ["1 piece", "10 pack"]),
        ("Ruler", "", "Stationery", ["1 piece"]),

        # ── Mkaa & Mafuta ya Taa ─────────────────────────────────────────────
        ("Kerosene", "", "Mkaa & Mafuta ya Taa", ["500ml", "1L"]),
        ("Charcoal (Mkaa)", "", "Mkaa & Mafuta ya Taa", ["1 debe", "half debe"]),
        ("Matchbox", "", "Mkaa & Mafuta ya Taa", ["1 box", "10 pack"]),

        # ── Mboga & Matunda ──────────────────────────────────────────────────
        ("Tomatoes", "", "Mboga & Matunda", ["1 piece", "3 pack", "1kg"]),
        ("Onions", "", "Mboga & Matunda", ["1 piece", "1kg", "500g"]),
        ("Sukuma Wiki", "", "Mboga & Matunda", ["1 bunch"]),
        ("Cabbage", "", "Mboga & Matunda", ["half", "whole"]),
        ("Bananas", "", "Mboga & Matunda", ["1 piece", "bunch"]),
        ("Avocado", "", "Mboga & Matunda", ["1 piece", "3 pack"]),

        # ── Vyombo vya Jikoni ────────────────────────────────────────────────
        ("Sufuria (Small)", "", "Vyombo vya Jikoni", ["1 piece"]),
        ("Sufuria (Medium)", "", "Vyombo vya Jikoni", ["1 piece"]),
        ("Plastic Plate", "", "Vyombo vya Jikoni", ["1 piece", "4 pack"]),
        ("Plastic Cup", "", "Vyombo vya Jikoni", ["1 piece", "4 pack"]),
        ("Sufuria Lid", "", "Vyombo vya Jikoni", ["1 piece"]),
    ]

    for brand_name, manufacturer, category_name, variants in catalog:
        cat_id = cat_map.get(category_name)
        if not cat_id:
            continue

        # Create parent product
        product = models.Product(
            shop_id=shop_id,
            client_id=str(uuid.uuid4()),
            brand_name=brand_name,
            manufacturer=manufacturer or None,
            category_id=cat_id,
            created_via=models.CreatedVia.admin,
        )
        db.add(product)
        db.flush()

        # Create SKUs for each variant — price 0, shopkeeper sets real price
        for variant in variants:
            sku_name = f"{brand_name} {variant}" if variant not in ("", "1 piece") else brand_name
            db.add(models.SKU(
                shop_id=shop_id,
                client_id=str(uuid.uuid4()),
                product_id=product.id,
                name=sku_name,
                selling_price=0,
                buying_price=None,
                needs_cost_review=True,
                stock_qty=None,
                created_via=models.CreatedVia.admin,
            ))

@router.post("/shops")
def create_shop_and_owner(
    request: Request,
    name: str = Form(...),
    owner_name: str = Form(...),
    owner_phone: str = Form(...),
    owner_pin: str = Form(...),
    db: Session = Depends(get_db),
):
    _check_session(request)
    import hashlib

    # Create shop
    shop = models.Shop(name=name)
    db.add(shop)
    db.flush()

    # Create owner account tied to this shop
    owner = models.Shopkeeper(
        name=owner_name,
        phone=owner_phone,
        pin_hash=hashlib.sha256(owner_pin.encode()).hexdigest(),
        role=models.ShopkeeperRole.owner,
        shop_id=shop.id,
    )
    db.add(owner)

    # Seed default categories for this shop
    default_categories = [
        "Unga & Nafaka", "Sukari & Chumvi", "Mafuta ya Kupika",
        "Vinywaji", "Maziwa & Mayai", "Mkate & Mandazi",
        "Sigara & Pombe", "Sabuni & Usafi", "Karatasi & Choo",
        "Dawa za Mwili", "Nywele", "Viatu & Nguo",
        "Simu & Airtime", "Mkaa & Mafuta ya Taa",
        "Mboga & Matunda", "Chakula cha Watoto",
        "Dawa", "Stationery", "Vyombo vya Jikoni", "Nyingine",
    ]
    for i, cat_name in enumerate(default_categories):
        db.add(models.Category(shop_id=shop.id, name=cat_name, sort_order=i))

    db.flush()  # get shop.id and category ids before seeding

    # ── Seed default catalog ─────────────────────────────────────────────────
    _seed_catalog(db, shop.id, {c.name: c.id for c in db.query(models.Category).filter(models.Category.shop_id == shop.id).all()})

    db.commit()
    return RedirectResponse(url="/admin/shops", status_code=302)


@router.get("/shops/{shop_id}/edit", response_class=HTMLResponse)
def edit_shop_page(shop_id: str, request: Request, db: Session = Depends(get_db)):
    _check_session(request)
    shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
    if not shop:
        return RedirectResponse(url="/admin/shops", status_code=302)

    owner = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.shop_id == shop_id,
        models.Shopkeeper.role == "owner",
    ).first()

    body = f"""
    <h1>Edit Shop</h1>
    <div class="card">
      <h2>Shop Details</h2>
      <form method="POST" action="/admin/shops/{shop_id}/edit">
        <div class="form-row">
          <div><label>SHOP NAME</label>
            <input name="name" value="{shop.name}" required/></div>
        </div>
        <button type="submit">Save Changes</button>
      </form>
    </div>

    <div class="card" style="margin-top:20px">
      <h2>Owner Account</h2>
      <form method="POST" action="/admin/shops/{shop_id}/edit-owner">
        <div class="form-row">
          <div><label>OWNER NAME</label>
            <input name="owner_name" value="{owner.name if owner else ''}" required/></div>
          <div><label>PHONE</label>
            <input name="owner_phone" value="{owner.phone if owner else ''}" required/></div>
        </div>
        <div class="form-row">
          <div><label>NEW PIN (leave blank to keep current)</label>
            <input name="owner_pin" type="password" placeholder="Leave blank to keep"/></div>
        </div>
        <button type="submit">Update Owner</button>
      </form>
    </div>

    <div class="card" style="margin-top:20px;border:1px solid #9C3B2E">
      <h2 style="color:#9C3B2E">Danger Zone</h2>
      <p style="font-size:13px;color:#888;margin-bottom:16px">
        Deleting a shop removes all its staff, products, SKUs, and sales permanently.
        This cannot be undone.
      </p>
      <a href="/admin/shops/{shop_id}/delete"
         onclick="return confirm('Delete {shop.name} and ALL its data forever?')"
         style="display:inline-block;padding:12px 24px;background:#9C3B2E;color:#fff;
                border-radius:8px;font-weight:700;text-decoration:none">
        Delete This Shop
      </a>
    </div>

    <p style="margin-top:16px"><a href="/admin/shops" style="color:#2E5339">← Back to shops</a></p>
    """
    return _base(f"Edit {shop.name}", body)


@router.post("/shops/{shop_id}/edit")
def edit_shop(
    shop_id: str,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    _check_session(request)
    shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
    if shop:
        shop.name = name
        db.commit()
    return RedirectResponse(url="/admin/shops", status_code=302)


@router.post("/shops/{shop_id}/edit-owner")
def edit_owner(
    shop_id: str,
    request: Request,
    owner_name: str = Form(...),
    owner_phone: str = Form(...),
    owner_pin: str = Form(""),
    db: Session = Depends(get_db),
):
    _check_session(request)
    import hashlib
    owner = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.shop_id == shop_id,
        models.Shopkeeper.role == "owner",
    ).first()
    if owner:
        owner.name = owner_name
        owner.phone = owner_phone
        if owner_pin.strip():
            owner.pin_hash = hashlib.sha256(owner_pin.encode()).hexdigest()
        db.commit()
    return RedirectResponse(url=f"/admin/shops/{shop_id}/edit", status_code=302)


@router.get("/shops/{shop_id}/delete")
def delete_shop(shop_id: str, request: Request, db: Session = Depends(get_db)):
    _check_session(request)
    shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
    if not shop:
        return RedirectResponse(url="/admin/shops", status_code=302)

    # Delete in dependency order
    # Sale items first
    sale_ids = [s.id for s in db.query(models.Sale).filter(models.Sale.shop_id == shop_id).all()]
    if sale_ids:
        db.query(models.SaleItem).filter(models.SaleItem.sale_id.in_(sale_ids)).delete(synchronize_session=False)
    db.query(models.Sale).filter(models.Sale.shop_id == shop_id).delete()
    db.query(models.SKU).filter(models.SKU.shop_id == shop_id).delete()
    db.query(models.Product).filter(models.Product.shop_id == shop_id).delete()
    db.query(models.Category).filter(models.Category.shop_id == shop_id).delete()
    db.query(models.Shopkeeper).filter(models.Shopkeeper.shop_id == shop_id).delete()
    db.delete(shop)
    db.commit()

    return RedirectResponse(url="/admin/shops", status_code=302)


# ── Owners ────────────────────────────────────────────────────────────────────

@router.get("/owners", response_class=HTMLResponse)
def owners_page(request: Request, db: Session = Depends(get_db)):
    _check_session(request)
    owners = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.role == "owner"
    ).order_by(models.Shopkeeper.created_at.desc()).all()

    rows = ""
    for o in owners:
        shop_name = o.shop.name if o.shop else "—"
        status = "Active" if o.is_active else "Inactive"
        status_color = "#2E5339" if o.is_active else "#9C3B2E"
        toggle_label = "Deactivate" if o.is_active else "Reactivate"
        rows += f"""
        <tr>
          <td><strong>{o.name}</strong></td>
          <td>{o.phone}</td>
          <td>{shop_name}</td>
          <td><span style="color:{status_color};font-weight:700">{status}</span></td>
          <td>{o.created_at.strftime('%d %b %Y')}</td>
          <td>
            <a href="/admin/owners/{o.id}/reset-pin"
               style="color:#2E5339;font-weight:700;font-size:13px;
                      text-decoration:none;margin-right:12px">Reset PIN</a>
            <a href="/admin/owners/{o.id}/toggle"
               style="color:#9C3B2E;font-weight:700;font-size:13px;text-decoration:none">
               {toggle_label}</a>
          </td>
        </tr>"""

    body = f"""
    <h1>Owners</h1>
    <div class="card">
      <h2>All Owners ({len(owners)})</h2>
      <p style="font-size:13px;color:#888;margin-bottom:16px">
        Owners are created automatically when you create a shop.
        Use the Shop edit page to update their name, phone, or PIN.
      </p>
      <table>
        <tr><th>NAME</th><th>PHONE</th><th>SHOP</th><th>STATUS</th><th>JOINED</th><th>ACTIONS</th></tr>
        {rows}
      </table>
    </div>
    """
    return _base("Owners", body)


@router.get("/owners/{owner_id}/toggle")
def toggle_owner(owner_id: str, request: Request, db: Session = Depends(get_db)):
    _check_session(request)
    owner = db.query(models.Shopkeeper).filter(models.Shopkeeper.id == owner_id).first()
    if owner:
        owner.is_active = not owner.is_active
        db.commit()
    return RedirectResponse(url="/admin/owners", status_code=302)


@router.get("/owners/{owner_id}/reset-pin", response_class=HTMLResponse)
def reset_pin_page(owner_id: str, request: Request, db: Session = Depends(get_db)):
    _check_session(request)
    owner = db.query(models.Shopkeeper).filter(models.Shopkeeper.id == owner_id).first()
    if not owner:
        return RedirectResponse(url="/admin/owners", status_code=302)

    body = f"""
    <h1>Reset PIN — {owner.name}</h1>
    <div class="card">
      <form method="POST" action="/admin/owners/{owner_id}/reset-pin">
        <label>NEW PIN (4 digits)</label>
        <input name="new_pin" type="password" maxlength="4"
               placeholder="e.g. 5678" required style="margin-bottom:16px"/>
        <button type="submit">Set New PIN</button>
      </form>
    </div>
    <p style="margin-top:16px">
      <a href="/admin/owners" style="color:#2E5339">← Back to owners</a>
    </p>
    """
    return _base(f"Reset PIN — {owner.name}", body)


@router.post("/owners/{owner_id}/reset-pin")
def reset_pin(
    owner_id: str,
    request: Request,
    new_pin: str = Form(...),
    db: Session = Depends(get_db),
):
    _check_session(request)
    import hashlib
    owner = db.query(models.Shopkeeper).filter(models.Shopkeeper.id == owner_id).first()
    if owner:
        owner.pin_hash = hashlib.sha256(new_pin.encode()).hexdigest()
        db.commit()
    return RedirectResponse(url="/admin/owners", status_code=302)