from sqlalchemy.ext.asyncio import AsyncSession

from app.database import category_crud
from app.models.category import Category


async def create_category(
    session: AsyncSession,
    user_id: int,
    name: str,
) -> Category:
    return await category_crud.create_category(
        session=session,
        user_id=user_id,
        name=name,
    )


async def get_category(
    session: AsyncSession,
    user_id: int,
    category_id: int,
) -> Category | None:
    return await category_crud.get_category(
        session=session,
        user_id=user_id,
        category_id=category_id,
    )


async def find_category_by_name(
    session: AsyncSession,
    user_id: int,
    name: str,
) -> Category | None:
    return await category_crud.find_category_by_name(
        session=session,
        user_id=user_id,
        name=name,
    )


async def get_or_create_category(
    session: AsyncSession,
    user_id: int,
    name: str,
) -> Category:
    return await category_crud.get_or_create_category(
        session=session,
        user_id=user_id,
        name=name,
    )