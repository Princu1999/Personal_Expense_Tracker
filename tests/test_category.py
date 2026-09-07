import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.user import User
from app.services.category_service import (
    create_category,
    find_category_by_name,
    get_category,
    get_or_create_category,
)


async def test_category_service():
    async with SessionLocal() as session:
        # Get or create a test user
        result = await session.execute(
            select(User).where(User.username == "category_test_user")
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                username="category_test_user",
                email="category_test_user@example.com",
                hashed_password="dummy_hash",
                default_currency="INR",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        user_id = user.id
        unique_name = f"cat_{int(asyncio.get_event_loop().time() * 1000)}"

        # 1. Create category
        category = await create_category(
            session=session,
            user_id=user_id,
            name=unique_name,
        )

        assert category is not None
        assert category.id is not None
        assert category.name == unique_name
        assert category.user_id == user_id

        # 2. Find category by name
        found = await find_category_by_name(
            session=session,
            user_id=user_id,
            name=unique_name,
        )
        assert found is not None
        assert found.id == category.id

        # 3. Get category by ID
        fetched = await get_category(
            session=session,
            user_id=user_id,
            category_id=category.id,
        )
        assert fetched is not None
        assert fetched.id == category.id

        # 4. Get or create existing category
        existing = await get_or_create_category(
            session=session,
            user_id=user_id,
            name=unique_name,
        )
        assert existing is not None
        assert existing.id == category.id

        print("=" * 50)
        print("CATEGORY TESTS PASSED")
        print("=" * 50)
        print("ID:", category.id)
        print("Name:", category.name)
        print("User ID:", category.user_id)


if __name__ == "__main__":
    asyncio.run(test_category_service())
