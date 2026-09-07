from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


async def create_category(
    session: AsyncSession,
    user_id: int,
    name: str,
) -> Category:
    category = Category(
        user_id=user_id,
        name=name.strip(),
    )

    session.add(category)

    await session.commit()
    await session.refresh(category)

    return category


async def get_category(
    session: AsyncSession,
    user_id: int,
    category_id: int,
) -> Category | None:
    result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        )
    )

    return result.scalar_one_or_none()


async def find_category_by_name(
    session: AsyncSession,
    user_id: int,
    name: str,
) -> Category | None:
    result = await session.execute(
        select(Category).where(
            Category.user_id == user_id,
            Category.name.ilike(name.strip()),
        )
    )

    return result.scalar_one_or_none()


async def get_or_create_category(
    session: AsyncSession,
    user_id: int,
    name: str,
) -> Category:
    cat = await find_category_by_name(session, user_id, name)
    if cat:
        return cat
    return await create_category(session, user_id, name.strip().title())