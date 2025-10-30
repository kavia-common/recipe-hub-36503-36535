from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# Password hashing context using bcrypt
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt."""
    return _pwd_context.hash(plain_password)


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# PUBLIC_INTERFACE
def create_access_token(
    subject: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
    issuer: str = "recipe-hub",
    audience: Optional[str] = None,
) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=60))
    to_encode = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": issuer,
    }
    if audience:
        to_encode["aud"] = audience
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


# PUBLIC_INTERFACE
def decode_access_token(
    token: str,
    secret_key: str,
    algorithms: list[str] | None = None,
    issuer: Optional[str] = "recipe-hub",
    audience: Optional[str] = None,
) -> dict:
    """Decode and validate a JWT token, returning the payload if valid."""
    try:
        options = {"verify_aud": audience is not None}
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=algorithms or ["HS256"],
            issuer=issuer,
            audience=audience if audience else None,
            options=options,
        )
        return payload
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
