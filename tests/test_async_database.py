import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database.session import SessionLocal


async def test_database():
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()

        print(f"Database result: {value}")
        print("Connected to PostgreSQL [OK]")
        assert value == 1


if __name__ == "__main__":
    asyncio.run(test_database())
