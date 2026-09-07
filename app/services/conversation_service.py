import re
import uuid
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.database.session import AsyncSessionLocal
from app.database import conversation_crud
from app.models.conversation import Conversation


def _clean_title(text: str) -> str:
    """Clean and sanitize generated title string."""
    # Remove surrounding quotes, special markdown, and unwanted prefixes
    cleaned = text.strip().strip("\"'`")
    cleaned = re.sub(r"^(Title|Topic|Subject):\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("\n", " ").strip()
    
    # Capitalize words if not already
    words = cleaned.split()
    if len(words) > 7:
        cleaned = " ".join(words[:6])
    return cleaned if cleaned else "New Conversation"


async def generate_conversation_title(query: str) -> str:
    """Generate a concise 3-5 word summary title from the user's first query."""
    if not query or not query.strip():
        return "New Conversation"

    cleaned_q = query.strip()

    # If query is very short, format it directly
    if len(cleaned_q.split()) <= 4:
        return cleaned_q.title()

    try:
        if settings.GROQ_API_KEY:
            title_llm = ChatGroq(
                model=settings.GROQ_MODEL,
                temperature=0.2,
                api_key=settings.GROQ_API_KEY,
            )
            prompt = (
                "Generate a concise, natural 3 to 5 word title summarizing the user message below. "
                "Do not include quotes, prefixes, or punctuation. Output only the title.\n\n"
                f"User message: {cleaned_q}"
            )
            response = await title_llm.ainvoke(prompt)
            raw_title = response.content.strip()
            return _clean_title(raw_title)
    except Exception:
        pass

    # Fallback to first few words
    words = cleaned_q.split()[:5]
    fallback = " ".join(words).title()
    return _clean_title(fallback)


async def get_or_create_conversation(
    user_id: int,
    thread_id: str | None = None,
    first_query: str = "",
) -> tuple[Conversation, bool]:
    """
    Get existing conversation or create a new one with a summarized title.
    Returns (Conversation, is_created).
    """
    async with AsyncSessionLocal() as session:
        if thread_id:
            existing = await conversation_crud.get_conversation(session, user_id, thread_id)
            if existing:
                await conversation_crud.touch_conversation(session, user_id, thread_id)
                return existing, False

        # Create new conversation
        new_thread_id = thread_id if thread_id else str(uuid.uuid4())
        title = await generate_conversation_title(first_query) if first_query else "New Conversation"
        new_conv = await conversation_crud.create_conversation(
            session=session,
            thread_id=new_thread_id,
            user_id=user_id,
            title=title,
        )
        return new_conv, True


async def get_user_conversations(user_id: int) -> list[Conversation]:
    """Retrieve all conversations for a user ordered by most recently updated."""
    async with AsyncSessionLocal() as session:
        return await conversation_crud.get_user_conversations(session, user_id)


async def get_conversation(user_id: int, thread_id: str) -> Conversation | None:
    """Retrieve a single conversation ensuring user ownership."""
    async with AsyncSessionLocal() as session:
        return await conversation_crud.get_conversation(session, user_id, thread_id)


async def get_conversation_messages(user_id: int, thread_id: str, graph) -> list[dict]:
    """Retrieve formatted message history for a thread from the LangGraph checkpointer."""
    async with AsyncSessionLocal() as session:
        conv = await conversation_crud.get_conversation(session, user_id, thread_id)
        if not conv:
            return []

    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.aget_state(config)
        if not state or "messages" not in state.values:
            return []

        raw_messages = state.values["messages"]
        formatted_messages = []

        for msg in raw_messages:
            if isinstance(msg, HumanMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if content.strip():
                    formatted_messages.append({
                        "role": "user",
                        "content": content,
                    })
            elif isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if content.strip():
                    formatted_messages.append({
                        "role": "assistant",
                        "content": content,
                    })

        return formatted_messages
    except Exception:
        return []


async def delete_conversation(user_id: int, thread_id: str, checkpointer=None) -> bool:
    """Delete a conversation and its checkpoint history."""
    async with AsyncSessionLocal() as session:
        deleted = await conversation_crud.delete_conversation(session, user_id, thread_id)
        if not deleted:
            return False

    if checkpointer and hasattr(checkpointer, "adelete_thread"):
        try:
            await checkpointer.adelete_thread(thread_id)
        except Exception:
            pass

    return True
