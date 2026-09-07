import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database.connection import engine


async def test_connection():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        value = result.scalar()
        print(f"Database connection successful: {value}")
        assert value == 1


if __name__ == "__main__":
    asyncio.run(test_connection())
