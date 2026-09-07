import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.config import settings
from app.database.connection import engine
from app.database.base import Base
from app.models import User, Category, Expense, Conversation
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


async def migrate_database():
    async with engine.begin() as conn:
        print("Migrating users table...")
        await conn.execute(
            text(
                """
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS email VARCHAR(255),
                ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255),
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);
                """
            )
        )
        print("Ensuring all application tables exist...")
        await conn.run_sync(Base.metadata.create_all)
        print("Application tables created successfully.")

    print("Setting up LangGraph PostgreSQL Checkpointer tables...")
    conn_str = settings.postgres_connection_string
    async with AsyncPostgresSaver.from_conn_string(conn_str) as checkpointer:
        await checkpointer.setup()
        print("Checkpointer tables setup successfully.")

    await engine.dispose()
    print("Database migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(migrate_database())
