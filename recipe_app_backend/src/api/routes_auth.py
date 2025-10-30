from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.security import create_access_token, decode_access_token, hash_password, verify_password
from src.db.models import User
from src.db.schemas import UserCreate, UserRead
from src.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


def _get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def _get_current_user(db: Session, token: str) -> User:
    settings = get_settings()
    try:
        payload = decode_access_token(
            token,
            secret_key=settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = _get_user_by_email(db, sub)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    return user


# PUBLIC_INTERFACE
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """Resolve the current authenticated user from Authorization: Bearer token."""
    return _get_current_user(db, token)


@router.post(
    "/register",
    response_model=UserRead,
    summary="Register user",
    description="Create a new user account with email and password.",
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = _get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(email=payload.email, full_name=payload.full_name, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login",
    description="Authenticate with email and password and receive a JWT access token.",
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = _get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    settings = get_settings()
    token = create_access_token(
        subject=user.email,
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    return Token(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user",
    description="Returns the current authenticated user's profile.",
)
def me(current_user: User = Depends(get_current_user)):
    return current_user
