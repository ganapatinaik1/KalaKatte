"""
auth.py — JWT token creation/verification + password hashing.

TODO (email sending):
  When you're ready to add email verification or password-reset emails,
  use Python's smtplib + Gmail SMTP (or a free Resend/Mailgun account).
  The hook point is right after user creation in /api/auth/register.
  Example:
      import smtplib, ssl
      from email.message import EmailMessage
      def send_verification_email(to_email: str, token: str):
          msg = EmailMessage()
          msg["Subject"] = "Verify your KalaKatte account"
          msg["From"] = SMTP_USER
          msg["To"] = to_email
          msg.set_content(f"Click to verify: https://kalakatte.duckdns.org/verify?token={token}")
          with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
              s.login(SMTP_USER, SMTP_PASS)
              s.send_message(msg)
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
import models

# ---------------------------------------------------------------------------
# Configuration — override via environment variables in production
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("KK_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return {}


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    """Returns the logged-in user, or None if no / invalid token."""
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_current_user(
    user: Optional[models.User] = Depends(get_current_user_optional),
) -> models.User:
    """Returns the logged-in user; raises 401 if not authenticated."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_artisan(user: models.User = Depends(get_current_user)) -> models.User:
    """Raises 403 if the user is not an artisan."""
    if user.role != "artisan":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Artisan account required")
    return user
