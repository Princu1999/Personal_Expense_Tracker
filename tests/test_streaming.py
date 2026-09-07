import asyncio
import json
import pytest
from httpx import AsyncClient, ASGITransport

from app.api.chat import app


@pytest.mark.asyncio
async def test_chat_stream_endpoint_flow():
    """Test streaming endpoint with SSE parsing, metadata, tokens, and multi-turn state persistence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Register test user
        rand_id = int(asyncio.get_event_loop().time() * 1000)
        reg_res = await ac.post(
            "/auth/register",
            json={
                "username": f"streamuser_{rand_id}",
                "email": f"stream_{rand_id}@example.com",
                "password": "password123",
                "default_currency": "INR",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Test turn 1 streaming
        tokens = []
        thread_id = None
        title = None
        done_received = False

        async with ac.stream(
            "POST",
            "/chat/stream",
            json={"message": "Hi, please note that my favorite category is Books & Education."},
            headers=headers,
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    done_received = True
                    break

                event = json.loads(data_str)
                event_type = event.get("type")

                if event_type == "metadata":
                    thread_id = event.get("thread_id")
                    title = event.get("title")
                elif event_type == "token":
                    tokens.append(event.get("content", ""))
                elif event_type == "done":
                    if not thread_id:
                        thread_id = event.get("thread_id")
                    if not title:
                        title = event.get("title")

        full_response1 = "".join(tokens)
        assert thread_id is not None
        assert title is not None
        assert len(tokens) > 0
        assert len(full_response1.strip()) > 0
        assert done_received is True

        # 3. Test turn 2 streaming on same thread: verify checkpointer multi-turn retention
        tokens_turn2 = []
        async with ac.stream(
            "POST",
            "/chat/stream",
            json={
                "message": "What is my favorite category that I mentioned earlier?",
                "thread_id": thread_id,
            },
            headers=headers,
        ) as response2:
            assert response2.status_code == 200
            async for line in response2.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                event = json.loads(data_str)
                if event.get("type") == "token":
                    tokens_turn2.append(event.get("content", ""))

        full_response2 = "".join(tokens_turn2)
        assert len(tokens_turn2) > 0
        assert "book" in full_response2.lower() or "education" in full_response2.lower()

        # 4. Verify conversation detail from checkpointer has stored history
        detail_res = await ac.get(f"/conversations/{thread_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == thread_id
        assert len(detail["messages"]) >= 4  # 2 user messages + 2 assistant messages


@pytest.mark.asyncio
async def test_chat_stream_tool_execution():
    """Test streaming during tool call (record expense)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        rand_id = int(asyncio.get_event_loop().time() * 1000)
        reg_res = await ac.post(
            "/auth/register",
            json={
                "username": f"toolstream_{rand_id}",
                "email": f"toolstream_{rand_id}@example.com",
                "password": "password123",
                "default_currency": "INR",
            },
        )
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        tokens = []
        tool_events = []
        async with ac.stream(
            "POST",
            "/chat/stream",
            json={"message": "I spent 350 on a train ticket today"},
            headers=headers,
        ) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                event = json.loads(data_str)
                if event.get("type") == "token":
                    tokens.append(event.get("content", ""))
                elif event.get("type") in ("tool_start", "tool_end"):
                    tool_events.append(event)

        full_resp = "".join(tokens)
        assert len(tokens) > 0
        assert len(tool_events) >= 1  # record_expense tool called


@pytest.mark.asyncio
async def test_chat_stream_validation():
    """Test validation and error handling on streaming endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Unauthorized check
        unauth_res = await ac.post("/chat/stream", json={"message": "test"})
        assert unauth_res.status_code == 401

        # Register user
        rand_id = int(asyncio.get_event_loop().time() * 1000)
        reg_res = await ac.post(
            "/auth/register",
            json={
                "username": f"validuser_{rand_id}",
                "email": f"valid_{rand_id}@example.com",
                "password": "password123",
                "default_currency": "INR",
            },
        )
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Empty message check
        empty_res = await ac.post("/chat/stream", json={"message": "   "}, headers=headers)
        assert empty_res.status_code == 400
