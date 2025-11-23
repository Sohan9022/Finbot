# core/auth.py
"""
Authentication helper for registering and logging in users.

Improvements:
- Clear typing and docstrings
- Helper methods: get_user_by_username / get_user_by_email / get_user_by_id
- Change password helper
- Deactivate user helper
- Use SECRET_KEY from env (fallback preserved)
- Consistent return types: (result, error) tuples
- Defensive DB handling and clearer error messages
"""

import os
import re
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any

import bcrypt
import jwt

try:
    from core.database import DatabaseOperations
    from core.config import settings
except Exception:
    # allow running modules directly in some contexts
    import sys as _sys, os as _os
    _sys.path.append(_os.path.join(_os.path.dirname(__file__), ".."))
    from core.database import DatabaseOperations  # type: ignore
    try:
        from core.config import settings  # type: ignore
    except Exception:
        settings = None  # optional

# Read secret key: prefer central settings if available
SECRET_KEY = (getattr(settings, "SECRET_KEY", None) if settings else None) or os.getenv(
    "SECRET_KEY", "change-this-secret-in-production"
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_DAYS = int(os.getenv("JWT_EXP_DAYS", "7"))


class Authentication:
    """Authentication helper for registering/logging in users."""

    # -----------------------
    # Password Utilities
    # -----------------------
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a plaintext password against the stored bcrypt hash."""
        if not password or not hashed:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    # -----------------------
    # JWT Utilities
    # -----------------------
    @staticmethod
    def generate_token(user_id: int, username: str, expires_days: int = JWT_EXPIRES_DAYS) -> str:
        """
        Generate a JWT token.
        Returns a string token (should be 'Bearer <token>' on transport if desired).
        """
        payload = {
            "user_id": int(user_id),
            "username": username,
            "exp": datetime.utcnow() + timedelta(days=int(expires_days)),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
        # PyJWT may return bytes in older versions
        return token if isinstance(token, str) else token.decode("utf-8")

    @staticmethod
    def decode_token(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Decode and validate a JWT token.
        Returns (payload, None) on success or (None, error_message) on failure.
        """
        if not token:
            return None, "Token missing"

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, "Token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"
        except Exception as e:
            return None, f"Token decode error: {str(e)}"

    # -----------------------
    # Email & Username Validation
    # -----------------------
    @staticmethod
    def validate_email(email: str) -> bool:
        """Basic email format validation."""
        if not email:
            return False
        pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_username(username: str) -> bool:
        """Allow alphanum, dash, underscore and dot; length 3..150."""
        if not username or len(username) < 3 or len(username) > 150:
            return False
        return re.match(r"^[A-Za-z0-9_\-\.]+$", username) is not None

    # -----------------------
    # DB Helpers
    # -----------------------
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Return the user row by username or None."""
        try:
            query = "SELECT id, username, email, password_hash, full_name, role, is_active FROM users WHERE username = %s LIMIT 1"
            res = DatabaseOperations.execute_query(query, (username,), fetch=True)
            return dict(res[0]) if res else None
        except Exception:
            return None

    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Return the user row by email or None."""
        try:
            query = "SELECT id, username, email, password_hash, full_name, role, is_active FROM users WHERE email = %s LIMIT 1"
            res = DatabaseOperations.execute_query(query, (email,), fetch=True)
            return dict(res[0]) if res else None
        except Exception:
            return None

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Return the user row by id or None."""
        try:
            query = "SELECT id, username, email, full_name, role, is_active FROM users WHERE id = %s LIMIT 1"
            res = DatabaseOperations.execute_query(query, (user_id,), fetch=True)
            return dict(res[0]) if res else None
        except Exception:
            return None

    # -----------------------
    # Registration
    # -----------------------
    @staticmethod
    def register(username: str, email: str, password: str, full_name: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Register a new user.
        Returns (user_dict, None) on success or (None, error_message) on failure.
        """
        try:
            # Basic validations
            if not Authentication.validate_username(username):
                return None, "Invalid username. Use 3-150 chars: letters, numbers, ._-"
            if not Authentication.validate_email(email):
                return None, "Invalid email format"
            if not password or len(password) < 6:
                return None, "Password must be at least 6 characters"
            if not full_name or len(full_name.strip()) < 2:
                return None, "Full name must be at least 2 characters"

            # Check duplicates (defensive)
            existing = Authentication.get_user_by_username(username)
            if existing:
                return None, "Username already exists"

            existing = Authentication.get_user_by_email(email)
            if existing:
                return None, "Email already registered"

            password_hash = Authentication.hash_password(password)

            query = """
                INSERT INTO users (username, email, password_hash, full_name, created_at, is_active)
                VALUES (%s, %s, %s, %s, NOW(), TRUE)
                RETURNING id, username, email, full_name, role
            """
            result = DatabaseOperations.execute_query(query, (username, email, password_hash, full_name), fetch=True)

            if result:
                row = dict(result[0])
                user = {
                    "user_id": row.get("id"),
                    "username": row.get("username"),
                    "email": row.get("email"),
                    "full_name": row.get("full_name"),
                    "role": row.get("role") or "user",
                }
                return user, None

            return None, "Registration failed"

        except Exception as e:
            # Attempt to parse common DB uniqueness errors
            err = str(e).lower()
            if "unique" in err or "duplicate" in err:
                if "username" in err:
                    return None, "Username already exists"
                if "email" in err:
                    return None, "Email already registered"
            return None, f"Registration error: {str(e)}"

    # -----------------------
    # Login
    # -----------------------
    @staticmethod
    def login(username: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Authenticate user by username and password.
        Returns (user_dict, None) on success; (None, error_message) on failure.
        """
        try:
            user_row = Authentication.get_user_by_username(username)
            if not user_row:
                return None, "Invalid username or password"

            if not user_row.get("is_active", True):
                return None, "Account is deactivated"

            stored_hash = user_row.get("password_hash") or ""
            if not Authentication.verify_password(password, stored_hash):
                return None, "Invalid username or password"

            # Optional: update last_login (best-effort)
            try:
                DatabaseOperations.execute_query("UPDATE users SET last_login = NOW() WHERE id = %s", (user_row["id"],), fetch=False)
            except Exception:
                pass

            user = {
                "user_id": user_row.get("id"),
                "username": user_row.get("username"),
                "email": user_row.get("email"),
                "full_name": user_row.get("full_name"),
                "role": user_row.get("role") or "user",
            }
            return user, None

        except Exception as e:
            return None, f"Login error: {str(e)}"

    # -----------------------
    # Password & Account Helpers
    # -----------------------
    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Change a user's password. Returns (True, None) on success, (False, error) on failure.
        """
        try:
            user = Authentication.get_user_by_id(user_id)
            if not user:
                return False, "User not found"

            # Fetch stored hash (query directly to ensure we have it)
            q = "SELECT password_hash FROM users WHERE id = %s LIMIT 1"
            res = DatabaseOperations.execute_query(q, (user_id,), fetch=True)
            stored_hash = res[0].get("password_hash") if res else None

            if not stored_hash or not Authentication.verify_password(current_password, stored_hash):
                return False, "Incorrect current password"

            if not new_password or len(new_password) < 6:
                return False, "New password must be at least 6 characters"

            new_hash = Authentication.hash_password(new_password)
            DatabaseOperations.execute_query("UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s", (new_hash, user_id), fetch=False)
            return True, None
        except Exception as e:
            return False, f"Change password error: {str(e)}"

    @staticmethod
    def deactivate_user(user_id: int) -> Tuple[bool, Optional[str]]:
        """Soft-delete / deactivate a user."""
        try:
            DatabaseOperations.execute_query("UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = %s", (user_id,), fetch=False)
            return True, None
        except Exception as e:
            return False, f"Deactivate error: {str(e)}"
