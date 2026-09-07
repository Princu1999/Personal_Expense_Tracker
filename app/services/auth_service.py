from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.category import Category
from app.models.user import User
from app.schemas.auth import TokenData, UserCreate

DEFAULT_CATEGORIES = [
    # Daily Essentials & Food
    "Groceries",
    "Food & Dining",
    "Coffee & Snacks",
    "Food",

    # Housing & Utilities
    "Rent & Mortgage",
    "Bills & Utilities",
    "Household & Maintenance",
    "Home Improvement",

    # Transportation & Travel
    "Transport",
    "Fuel & Gas",
    "Taxi & Rideshare",
    "Vehicle Maintenance",
    "Travel & Vacation",

    # Shopping & Personal
    "Shopping",
    "Clothing & Apparel",
    "Electronics & Gadgets",
    "Personal Care & Grooming",

    # Health & Fitness
    "Health",
    "Healthcare & Medical",
    "Pharmacy & Medications",
    "Fitness & Gym",

    # Entertainment & Learning
    "Entertainment",
    "Subscriptions & Streaming",
    "Books & Education",
    "Hobbies & Recreation",

    # Family, Kids & Pets
    "Childcare & Kids",
    "Pet Care & Veterinary",

    # Financial, Legal & Taxes
    "Insurance",
    "Investments & Savings",
    "Debt & Loan Payments",
    "Taxes & Government Fees",
    "Legal & Professional Services",

    # Rare, Occasional & Unexpected
    "Gifts & Celebrations",
    "Charity & Donations",
    "Emergency & Urgent",
    "Moving & Relocation",

    # Fallback / General
    "Bills",
    "Other",
]


def hash_password(password: str) -> str:
    # Truncate to 72 characters if needed due to bcrypt limitation
    pwd_bytes = password[:72].encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password[:72].encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    # Ensure 'sub' is a string for JWT standard compliance
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub: str = payload.get("sub")
        if sub is None:
            return None
        return TokenData(user_id=int(sub))
    except (jwt.PyJWTError, ValueError):
        return None


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.email.ilike(email.strip()))
    )
    return result.scalar_one_or_none()


async def get_user_by_username(
    session: AsyncSession, username: str
) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.username.ilike(username.strip()))
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    hashed = hash_password(user_create.password)
    user = User(
        email=user_create.email.strip().lower(),
        username=user_create.username.strip(),
        hashed_password=hashed,
        default_currency=user_create.default_currency.upper().strip()
        if user_create.default_currency
        else "INR",
        is_active=True,
    )
    session.add(user)
    await session.flush()

    # Seed default categories for this specific user
    for cat_name in DEFAULT_CATEGORIES:
        category = Category(
            user_id=user.id,
            name=cat_name,
        )
        session.add(category)

    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> Optional[User]:
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user