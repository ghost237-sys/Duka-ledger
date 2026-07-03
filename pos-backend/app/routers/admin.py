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
        rows += f"""
        <tr>
          <td>{s.name}</td>
          <td style="font-family:monospace;font-size:12px;color:#888">{s.id}</td>
          <td>{keeper_count}</td>
          <td>{s.created_at.strftime('%d %b %Y')}</td>
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
        <tr><th>NAME</th><th>ID</th><th>STAFF</th><th>CREATED</th></tr>
        {rows}
      </table>
    </div>
    """
    return _base("Shops", body)


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
        rows += f"""
        <tr>
          <td>{o.name}</td>
          <td>{o.phone}</td>
          <td>{shop_name}</td>
          <td><span class="badge badge-owner">owner</span></td>
          <td>{o.created_at.strftime('%d %b %Y')}</td>
        </tr>"""

    body = f"""
    <h1>Owners</h1>
    <div class="card">
      <h2>All Owners ({len(owners)})</h2>
      <p style="font-size:13px;color:#888;margin-bottom:16px">
        Owners are created automatically when you create a shop above.
      </p>
      <table>
        <tr><th>NAME</th><th>PHONE</th><th>SHOP</th><th>ROLE</th><th>JOINED</th></tr>
        {rows}
      </table>
    </div>
    """
    return _base("Owners", body)