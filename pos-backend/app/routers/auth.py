import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

team_router = APIRouter(prefix="/team", tags=["team"])

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def get_shopkeeper_by_token(token: str, db: Session) -> models.Shopkeeper:
    row = db.query(models.AuthToken).filter(models.AuthToken.token == token).first()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    shopkeeper = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.id == row.shopkeeper_id,
        models.Shopkeeper.is_active == True,
    ).first()
    if not shopkeeper:
        raise HTTPException(status_code=401, detail="Shopkeeper not found")
    return shopkeeper


@router.post("/login", response_model=schemas.LoginOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    shopkeeper = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.phone == payload.phone,
        models.Shopkeeper.is_active == True,
    ).first()
    if not shopkeeper or shopkeeper.pin_hash != hash_pin(payload.pin):
        raise HTTPException(status_code=401, detail="Wrong phone number or PIN")

    token = secrets.token_hex(32)
    db.add(models.AuthToken(token=token, shopkeeper_id=shopkeeper.id))
    db.commit()

    return schemas.LoginOut(
        token=token,
        shopkeeper=schemas.ShopkeeperOut(
            id=shopkeeper.id,
            name=shopkeeper.name,
            phone=shopkeeper.phone,
            role=shopkeeper.role,
            shop_id=shopkeeper.shop_id,
        )
    )


@router.post("/register")
def register(
    name: str,
    phone: str,
    pin: str,
    role: str = "shopkeeper",
    shop_id: str = None,
    db: Session = Depends(get_db),
):
    """
    Create a shopkeeper account for a shop.
    Used by the owner from the Team screen in the app.
    """
    if not shop_id:
        raise HTTPException(status_code=400, detail="shop_id is required")

    shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    existing = db.query(models.Shopkeeper).filter(models.Shopkeeper.phone == phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    shopkeeper = models.Shopkeeper(
        name=name,
        phone=phone,
        pin_hash=hash_pin(pin),
        role=role,
        shop_id=shop_id,
    )
    db.add(shopkeeper)
    db.commit()
    db.refresh(shopkeeper)
    return {"id": shopkeeper.id, "name": shopkeeper.name, "role": shopkeeper.role}




@router.get("/team")
def get_team(shop_id: str, db: Session = Depends(get_db)):
    """All shopkeepers belonging to a shop."""
    members = (
        db.query(models.Shopkeeper)
        .filter(models.Shopkeeper.shop_id == shop_id)
        .order_by(models.Shopkeeper.created_at)
        .all()
    )
    return [
        {
            "id": m.id,
            "name": m.name,
            "phone": m.phone,
            "role": m.role,
            "is_active": m.is_active,
            "created_at": m.created_at.isoformat(),
        }
        for m in members
    ]


@router.post("/team/{shopkeeper_id}/toggle")
def toggle_active(shopkeeper_id: str, db: Session = Depends(get_db)):
    """Activate or deactivate a shopkeeper account."""
    shopkeeper = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.id == shopkeeper_id
    ).first()
    if not shopkeeper:
        raise HTTPException(status_code=404, detail="Shopkeeper not found")
    shopkeeper.is_active = not shopkeeper.is_active
    db.commit()
    return {"id": shopkeeper.id, "is_active": shopkeeper.is_active}


team_router = APIRouter(prefix="/team", tags=["team"])

@team_router.get("")
def get_team(shop_id: str, db: Session = Depends(get_db)):
    members = (
        db.query(models.Shopkeeper)
        .filter(models.Shopkeeper.shop_id == shop_id)
        .order_by(models.Shopkeeper.created_at)
        .all()
    )
    return [
        {
            "id": m.id,
            "name": m.name,
            "phone": m.phone,
            "role": m.role,
            "is_active": m.is_active,
            "created_at": m.created_at.isoformat(),
        }
        for m in members
    ]


@team_router.post("/{shopkeeper_id}/toggle")
def toggle_active(shopkeeper_id: str, db: Session = Depends(get_db)):
    shopkeeper = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.id == shopkeeper_id
    ).first()
    if not shopkeeper:
        raise HTTPException(status_code=404, detail="Shopkeeper not found")
    shopkeeper.is_active = not shopkeeper.is_active
    db.commit()
    return {"id": shopkeeper.id, "is_active": shopkeeper.is_active}

@team_router.post("/{shopkeeper_id}/edit")
def edit_shopkeeper(
    shopkeeper_id: str,
    name: str,
    phone: str,
    pin: str = None,
    db: Session = Depends(get_db),
):
    import hashlib
    shopkeeper = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.id == shopkeeper_id
    ).first()
    if not shopkeeper:
        raise HTTPException(status_code=404, detail="Shopkeeper not found")

    # Check phone uniqueness if changed
    if phone != shopkeeper.phone:
        existing = db.query(models.Shopkeeper).filter(
            models.Shopkeeper.phone == phone
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Phone number already in use by another account"
            )

    shopkeeper.name = name
    shopkeeper.phone = phone
    if pin and pin.strip():
        shopkeeper.pin_hash = hashlib.sha256(pin.encode()).hexdigest()

    db.commit()
    return {
        "id": shopkeeper.id,
        "name": shopkeeper.name,
        "phone": shopkeeper.phone,
    }