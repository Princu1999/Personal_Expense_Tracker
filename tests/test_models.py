import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.base import Base
from app.database.connection import engine
from app.models import User, Category, Expense


async def test_create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Tables created successfully.")
    await engine.dispose()


create_tables = test_create_tables

if __name__ == "__main__":
    asyncio.run(test_create_tables())
