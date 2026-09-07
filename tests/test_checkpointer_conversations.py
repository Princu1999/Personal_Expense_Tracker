import asyncio
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.api.chat import app
from app.database.session import AsyncSessionLocal
from app.schemas.auth import UserCreate
from app.services import auth_service, conversation_service


@pytest.mark.asyncio
async def test_conversation_crud_and_service():
    """Test conversation service CRUD functions and isolation with real users."""
    # Test title cleaning and generation
    title_short = await conversation_service.generate_conversation_title("Spent 500 on dinner")
    assert isinstance(title_short, str)
    assert len(title_short) > 0

    rand_u1 = int(asyncio.get_event_loop().time() * 1000)
    rand_u2 = rand_u1 + 1

    async with AsyncSessionLocal() as session:
        user1 = await auth_service.create_user(
            session,
            UserCreate(
                username=f"u1_{rand_u1}",
                email=f"u1_{rand_u1}@test.com",
                password="pwd",
                default_currency="INR",
            ),
        )
        user2 = await auth_service.create_user(
            session,
            UserCreate(
                username=f"u2_{rand_u2}",
                email=f"u2_{rand_u2}@test.com",
                password="pwd",
                default_currency="USD",
            ),
        )
        user1_id = user1.id
        user2_id = user2.id
    
    thread1_id = str(uuid.uuid4())
    thread2_id = str(uuid.uuid4())

    conv1, created1 = await conversation_service.get_or_create_conversation(
        user_id=user1_id,
        thread_id=thread1_id,
        first_query="I bought groceries for 450",
    )
    assert created1 is True
    assert conv1.id == thread1_id
    assert conv1.user_id == user1_id

    # Second call for same thread should return existing
    conv1_fetch, created_again = await conversation_service.get_or_create_conversation(
        user_id=user1_id,
        thread_id=thread1_id,
        first_query="I bought groceries for 450",
    )
    assert created_again is False
    assert conv1_fetch.id == thread1_id

    # User 2 creates thread
    conv2, _ = await conversation_service.get_or_create_conversation(
        user_id=user2_id,
        thread_id=thread2_id,
        first_query="Electric bill payment of 1200",
    )
    assert conv2.id == thread2_id
    assert conv2.user_id == user2_id

    # Test user 1 conversation list contains thread1 but not thread2
    u1_convs = await conversation_service.get_user_conversations(user1_id)
    u1_ids = [c.id for c in u1_convs]
    assert thread1_id in u1_ids
    assert thread2_id not in u1_ids

    # Test user 2 conversation list contains thread2 but not thread1
    u2_convs = await conversation_service.get_user_conversations(user2_id)
    u2_ids = [c.id for c in u2_convs]
    assert thread2_id in u2_ids
    assert thread1_id not in u2_ids

    # Clean up
    await conversation_service.delete_conversation(user1_id, thread1_id)
    await conversation_service.delete_conversation(user2_id, thread2_id)


@pytest.mark.asyncio
async def test_api_conversations_flow():
    """Test full API flow: register, multi-turn chat with thread_id, list in chronological order, get detail, delete."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register test user
        rand_id = int(asyncio.get_event_loop().time() * 1000)
        email = f"chatuser_{rand_id}@example.com"
        reg_res = await ac.post(
            "/auth/register",
            json={
                "username": f"chatuser_{rand_id}",
                "email": email,
                "password": "password123",
                "default_currency": "INR",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Start a new chat turn 1 without thread_id
        chat1_res = await ac.post(
            "/chat",
            json={"message": "Hi, please remember that my favorite expense category is Groceries."},
            headers=headers,
        )
        assert chat1_res.status_code == 200
        data1 = chat1_res.json()
        assert "response" in data1
        thread_id = data1["thread_id"]
        assert thread_id is not None
        assert "title" in data1
        assert len(data1["title"]) > 0

        # 2. Turn 2 on the SAME thread: AI should retain memory from Postgres checkpointer
        chat2_res = await ac.post(
            "/chat",
            json={"message": "What is my favorite expense category that I just mentioned?", "thread_id": thread_id},
            headers=headers,
        )
        assert chat2_res.status_code == 200
        data2 = chat2_res.json()
        assert data2["thread_id"] == thread_id
        assert "grocer" in data2["response"].lower()

        # 3. Create a second conversation thread
        chat3_res = await ac.post(
            "/chat",
            json={"message": "I paid 1200 rupees for electricity bill"},
            headers=headers,
        )
        assert chat3_res.status_code == 200
        data3 = chat3_res.json()
        thread2_id = data3["thread_id"]
        assert thread2_id != thread_id

        # 4. List conversations: Most recent (thread2) should be at the top!
        convs_res = await ac.get("/conversations", headers=headers)
        assert convs_res.status_code == 200
        conv_list = convs_res.json()
        assert len(conv_list) >= 2
        # Most recently updated conversation should be first
        assert conv_list[0]["id"] == thread2_id
        assert conv_list[1]["id"] == thread_id

        # 5. Fetch conversation detail for thread 1 to verify checkpointer message retrieval
        detail_res = await ac.get(f"/conversations/{thread_id}", headers=headers)
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["id"] == thread_id
        assert len(detail_data["messages"]) >= 2
        assert detail_data["messages"][0]["role"] == "user"
        assert detail_data["messages"][1]["role"] == "assistant"

        # 6. Delete conversation
        del_res = await ac.delete(f"/conversations/{thread2_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # Verify thread2 is no longer in list
        convs_res_after = await ac.get("/conversations", headers=headers)
        remaining_ids = [c["id"] for c in convs_res_after.json()]
        assert thread2_id not in remaining_ids
        assert thread_id in remaining_ids
