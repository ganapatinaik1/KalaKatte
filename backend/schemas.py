"""
schemas.py — Pydantic request/response models.
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "buyer"   # "artisan" | "buyer"

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v):
        if v not in ("artisan", "buyer"):
            raise ValueError("role must be 'artisan' or 'buyer'")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    name: str
    role: str


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
class ProductIn(BaseModel):
    craft: str
    price: float
    hours: Optional[float] = None
    materials_cost: Optional[float] = None
    image_url: Optional[str] = None
    name: str
    artisan_name: Optional[str] = None
    village: Optional[str] = None
    materials: Optional[str] = None
    story: Optional[str] = None
    name_kn: Optional[str] = None
    name_en: Optional[str] = None
    artisan_name_kn: Optional[str] = None
    artisan_name_en: Optional[str] = None
    village_kn: Optional[str] = None
    village_en: Optional[str] = None
    materials_kn: Optional[str] = None
    materials_en: Optional[str] = None
    story_kn: Optional[str] = None
    story_en: Optional[str] = None


class ProductOut(ProductIn):
    id: str
    owner_id: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------
class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    qty: int


class OrderIn(BaseModel):
    items: List[OrderItem]
    total: float
    buyer_name: str
    phone: str
    address: str
    payment_method: str   # "demo" | "cod"


class OrderOut(BaseModel):
    id: str
    items: List[OrderItem]
    total: float
    buyer_name: str
    phone: str
    address: str
    payment_method: str
    status: str
    buyer_id: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrderStatusPatch(BaseModel):
    status: str
