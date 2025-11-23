"""
ChatFinance-AI Authentication Routes (FINAL FIXED)
Includes correct Authorization header handling (alias='Authorization')
"""

import os
import re
import jwt
from datetime import datetime, timedelta
from typing import Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, Field

from core.auth import Authentication
from core.database import DatabaseOperations

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGO = "HS256"
TOKEN_EXPIRE_DAYS = 7


# ------------------------- HELPERS -------------------------
def response(success: bool, data: Any = None, message: str = ""):
    out = {"success": success}
    if data is not None:
        out["data"] = data
    if message:
        out["message"] = message
    return out


def create_token(user_id: int, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGO)


# -------- FIXED: correct token extraction --------
def get_current_user_id(authorization: str = Header(None, alias="Authorization")) -> int:
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization format")

    token = authorization.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        return int(payload["user_id"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except Exception:
        raise HTTPException(401, "Invalid token")


# -------------- Password Strength Validation --------------
def validate_password_strength(pwd: str) -> Optional[str]:
    if len(pwd) < 8:
        return "Password must be ≥ 8 chars"
    if not re.search(r"[A-Z]", pwd):
        return "Password must contain uppercase letter"
    if not re.search(r"[a-z]", pwd):
        return "Password must contain lowercase letter"
    if not re.search(r"[0-9]", pwd):
        return "Password must contain digit"
    if not re.search(r"[!@#$%^&*()_+\-=]", pwd):
        return "Password must contain special character"
    return None


# ------------------------- MODELS -------------------------
class RegisterDTO(BaseModel):
    username: str = Field(..., min_length=3, pattern=r"^[A-Za-z0-9_.]+$")
    email: EmailStr
    password: str
    full_name: str


class LoginDTO(BaseModel):
    username: str
    password: str


class UpdateProfileDTO(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class ChangePasswordDTO(BaseModel):
    current_password: str
    new_password: str


# ------------------------- ROUTES -------------------------

@router.post("/register")
async def register(payload: RegisterDTO):
    err = validate_password_strength(payload.password)
    if err:
        raise HTTPException(400, err)

    user, error = Authentication.register(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )

    if error:
        raise HTTPException(400, error)

    return response(True, {"user": user}, "Registration successful")


@router.post("/login")
async def login(payload: LoginDTO):
    user, error = Authentication.login(payload.username, payload.password)
    if error:
        raise HTTPException(401, error)

    token = create_token(user["user_id"], user["username"])

    return response(True, {"token": token, "user": user}, "Login successful")


@router.get("/profile")
async def profile(user_id: int = Depends(get_current_user_id)):
    q = """
        SELECT id, username, email, full_name, role, created_at
        FROM users 
        WHERE id = %s LIMIT 1
    """
    rows = DatabaseOperations.execute_query(q, (user_id,))
    if not rows:
        raise HTTPException(404, "User not found")

    return response(True, {"profile": rows[0]})


@router.put("/profile")
async def update_profile(payload: UpdateProfileDTO, user_id: int = Depends(get_current_user_id)):
    updates = []
    params = []

    if payload.full_name:
        updates.append("full_name = %s")
        params.append(payload.full_name)

    if payload.email:
        dup = DatabaseOperations.execute_query(
            "SELECT id FROM users WHERE email = %s AND id != %s",
            (payload.email, user_id),
        )
        if dup:
            raise HTTPException(400, "Email already in use")

        updates.append("email = %s")
        params.append(payload.email)

    if not updates:
        return response(True, message="Nothing to update")

    params.append(user_id)

    q = f"""
        UPDATE users 
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE id = %s
        RETURNING id, username, email, full_name, role, created_at
    """

    rows = DatabaseOperations.execute_query(q, tuple(params))

    return response(True, {"profile": rows[0]}, "Profile updated")


@router.put("/change-password")
async def change_password(payload: ChangePasswordDTO, user_id: int = Depends(get_current_user_id)):

    row = DatabaseOperations.execute_query(
        "SELECT password_hash FROM users WHERE id = %s", (user_id,)
    )
    if not row:
        raise HTTPException(404, "User not found")

    if not Authentication.verify_password(payload.current_password, row[0]["password_hash"]):
        raise HTTPException(401, "Incorrect current password")

    err = validate_password_strength(payload.new_password)
    if err:
        raise HTTPException(400, err)

    new_hash = Authentication.hash_password(payload.new_password)

    DatabaseOperations.execute_query(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (new_hash, user_id),
        fetch=False,
    )

    return response(True, message="Password updated successfully")


@router.get("/get-stats")
async def get_stats(user_id: int = Depends(get_current_user_id)):

    q = """
        SELECT 
            COUNT(*) AS total_bills,
            COALESCE(SUM(amount), 0) AS total_spent,
            COUNT(DISTINCT DATE(created_at)) AS active_days
        FROM ocr_documents
        WHERE uploaded_by = %s
    """
    rows = DatabaseOperations.execute_query(q, (user_id,))

    stats = rows[0] if rows else {
        "total_bills": 0,
        "total_spent": 0,
        "active_days": 0
    }

    return response(True, stats)


@router.get("/verify")
async def verify(user_id: int = Depends(get_current_user_id)):
    return response(True, {"user_id": user_id}, "Valid token")


@router.post("/logout")
async def logout():
    return response(True, message="Logged out")
