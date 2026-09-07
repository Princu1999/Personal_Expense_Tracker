from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation


async def create_conversation(
    session: AsyncSession,
    thread_id: str,
    user_id: int,
    title: str = "New Conversation",
) -> Conversation:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conversation = Conversation(
        id=thread_id,
        user_id=user_id,
        title=title,
        created_at=now,
        updated_at=now,
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def get_conversation(
    session: AsyncSession,
    user_id: int,
    thread_id: str,
) -> Conversation | None:
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == thread_id,
            Conversation.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_user_conversations(
    session: AsyncSession,
    user_id: int,
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def update_conversation_title(
    session: AsyncSession,
    user_id: int,
    thread_id: str,
    title: str,
) -> Conversation | None:
    conversation = await get_conversation(session, user_id, thread_id)
    if conversation:
        conversation.title = title
        conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()
        await session.refresh(conversation)
    return conversation


async def touch_conversation(
    session: AsyncSession,
    user_id: int,
    thread_id: str,
) -> Conversation | None:
    conversation = await get_conversation(session, user_id, thread_id)
    if conversation:
        conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()
        await session.refresh(conversation)
    return conversation


async def delete_conversation(
    session: AsyncSession,
    user_id: int,
    thread_id: str,
) -> bool:
    conversation = await get_conversation(session, user_id, thread_id)
    if not conversation:
        return False
    await session.delete(conversation)
    await session.commit()
    return True
