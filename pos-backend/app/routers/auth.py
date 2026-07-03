import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# Simple in-memory token store for now.
# In production replace with JWT or a tokens table in the DB.
_tokens = {}


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def get_shopkeeper_by_token(token: str, db: Session) -> models.Shopkeeper:
    shopkeeper_id = _tokens.get(token)
    if not shopkeeper_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    shopkeeper = db.query(models.Shopkeeper).filter(
        models.Shopkeeper.id == shopkeeper_id,
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
    _tokens[token] = shopkeeper.id

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
    Dev/admin endpoint for creating shopkeeper accounts.
    Call this manually via curl to set up accounts -- not exposed to the app UI.
    """
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