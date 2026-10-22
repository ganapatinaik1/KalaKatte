"""
main.py — KalaKatte FastAPI backend.

Endpoints:
  POST  /api/auth/register
  POST  /api/auth/login
  GET   /api/products
  GET   /api/products/:id
  POST  /api/products          (artisan only)
  POST  /api/upload            (artisan only)
  POST  /api/orders
  GET   /api/orders            (own orders for buyers; all for artisans)
  PATCH /api/orders/:id        (artisan only — mark as shipped)

Run locally:
  uvicorn main:app --reload --port 8000

Run in production (gunicorn / start.sh):
  gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000
"""

import json
import os
import uuid
import shutil
from datetime import datetime, timezone
from typing import List, Optional

import aiofiles
from fastapi import (
    Depends, FastAPI, File, HTTPException, UploadFile, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
import auth
from database import Base, engine, get_db

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
try:
    Base.metadata.create_all(bind=engine, checkfirst=True)
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

FRONTEND_DIR = os.path.join(BASE_DIR, "..")   # index.html lives one level up

app = FastAPI(title="KalaKatte API", version="1.0.0")

# ---------------------------------------------------------------------------
# CORS — allow same-origin by default; open up if deploying separately
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten to your domain in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Serve uploaded images at /uploads/<filename>
# ---------------------------------------------------------------------------
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _product_to_out(p: models.Product) -> schemas.ProductOut:
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else str(d["created_at"])
    return schemas.ProductOut(**d)


def _order_to_out(o: models.Order) -> schemas.OrderOut:
    d = {c.name: getattr(o, c.name) for c in o.__table__.columns}
    d["items"] = json.loads(d.pop("items_json", "[]"))
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else str(d["created_at"])
    return schemas.OrderOut(**d)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.post("/api/auth/register", response_model=schemas.AuthResponse, status_code=201)
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        id=str(uuid.uuid4()),
        email=body.email,
        hashed_password=auth.hash_password(body.password),
        name=body.name,
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # TODO: send verification email here once email is configured
    #       auth.send_verification_email(user.email, token=...)

    token = auth.create_access_token(user.id, user.role)
    return schemas.AuthResponse(token=token, user_id=user.id, name=user.name, role=user.role)


@app.post("/api/auth/login", response_model=schemas.AuthResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not auth.verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = auth.create_access_token(user.id, user.role)
    return schemas.AuthResponse(token=token, user_id=user.id, name=user.name, role=user.role)


@app.get("/api/auth/me", response_model=schemas.AuthResponse)
def me(current_user: models.User = Depends(auth.get_current_user)):
    """Returns the current user's info. Useful for the frontend to rehydrate session."""
    token = auth.create_access_token(current_user.id, current_user.role)
    return schemas.AuthResponse(
        token=token,
        user_id=current_user.id,
        name=current_user.name,
        role=current_user.role,
    )


# ---------------------------------------------------------------------------
# Product routes
# ---------------------------------------------------------------------------
@app.get("/api/products", response_model=List[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).order_by(models.Product.created_at.desc()).all()
    return [_product_to_out(p) for p in products]


@app.get("/api/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_out(p)


@app.post("/api/products", response_model=schemas.ProductOut, status_code=201)
def create_product(
    body: schemas.ProductIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_artisan),
):
    product = models.Product(
        id="p" + str(uuid.uuid4()).replace("-", "")[:12],
        owner_id=current_user.id,
        **body.model_dump(),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _product_to_out(product)


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_MB = 5


@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.require_artisan),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WEBP, GIF allowed")

    contents = await file.read()
    if len(contents) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_SIZE_MB} MB)")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(UPLOAD_DIR, filename)

    async with aiofiles.open(dest, "wb") as f:
        await f.write(contents)

    return {"url": f"/uploads/{filename}"}


# ---------------------------------------------------------------------------
# Order routes
# ---------------------------------------------------------------------------
@app.post("/api/orders", response_model=schemas.OrderOut, status_code=201)
def create_order(
    body: schemas.OrderIn,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    # Payment mock: demo -> paid, cod -> placed  (matches frontend mock logic)
    computed_status = "paid" if body.payment_method == "demo" else "placed"

    order = models.Order(
        id="KK" + str(uuid.uuid4().int)[-6:],
        items_json=json.dumps([item.model_dump() for item in body.items]),
        total=body.total,
        buyer_name=body.buyer_name,
        phone=body.phone,
        address=body.address,
        payment_method=body.payment_method,
        status=computed_status,
        buyer_id=current_user.id if current_user else None,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _order_to_out(order)


@app.get("/api/orders", response_model=List[schemas.OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    - Artisans see ALL orders (so they can ship them).
    - Buyers see only their own orders.
    """
    if current_user.role == "artisan":
        orders = db.query(models.Order).order_by(models.Order.created_at.desc()).all()
    else:
        orders = (
            db.query(models.Order)
            .filter(models.Order.buyer_id == current_user.id)
            .order_by(models.Order.created_at.desc())
            .all()
        )
    return [_order_to_out(o) for o in orders]


@app.patch("/api/orders/{order_id}", response_model=schemas.OrderOut)
def set_order_status(
    order_id: str,
    body: schemas.OrderStatusPatch,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_artisan),
):
    o = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed = {"placed", "paid", "shipped"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")

    o.status = body.status
    db.commit()
    db.refresh(o)
    return _order_to_out(o)


# ---------------------------------------------------------------------------
# Serve the frontend (index.html) for all non-API routes
# ---------------------------------------------------------------------------
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    index = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(index)
