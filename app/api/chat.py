import os
import sys
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(override=True)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse
import json
from langchain_core.messages import HumanMessage
from langchain_core.tracers import LangChainTracer
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.api.auth import router as auth_router
from app.api.deps import get_current_user
from app.graph.graph import build_graph
from app.guardrails import guardrails_manager
from app.models.user import User
from app.schemas.conversation import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
    MessageItem,
)
from app.services import conversation_service


# Shared global graph instance and connection pool
_graph = None
_checkpointer = None
_pool = None
_pool_loop = None


async def get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer, _pool, _pool_loop
    current_loop = asyncio.get_running_loop()
    if _checkpointer is None or _pool is None or _pool_loop != current_loop:
        if _pool is not None and not _pool.closed:
            try:
                await _pool.close()
            except Exception:
                pass
        conn_str = settings.postgres_connection_string
        _pool = AsyncConnectionPool(
            conn_str,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            min_size=1,
            max_size=10,
            open=False,
        )
        await _pool.open()
        _pool_loop = current_loop
        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()
    return _checkpointer


async def get_graph():
    global _graph, _pool_loop
    current_loop = asyncio.get_running_loop()
    if _graph is None or _pool_loop != current_loop:
        checkpointer = await get_checkpointer()
        _graph = build_graph(checkpointer=checkpointer)
    return _graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    await get_graph()
    yield
    if _pool and not _pool.closed:
        await _pool.close()


app = FastAPI(
    title="Personal Expense Tracker API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)


@app.get("/")
async def root():
    return {
        "message": "Personal Expense Tracker API is running"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_req: Request,
    current_user: User = Depends(get_current_user),
):
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    # 1. Execute Input Guardrails (Rate Limiting, Prompt Injection, Toxicity, PII)
    client_ip = http_req.client.host if http_req.client else None
    input_guard_res = await guardrails_manager.validate_input(
        text=request.message,
        user_id=current_user.id,
        client_ip=client_ip,
    )

    if input_guard_res.rate_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=input_guard_res.safe_response,
            headers={"Retry-After": str(input_guard_res.retry_after)},
        )

    if input_guard_res.blocked:
        # Request blocked by prompt injection or toxicity guardrail
        return ChatResponse(
            response=input_guard_res.safe_response or "Request blocked by security guardrails.",
            thread_id=request.thread_id or "security_notice",
            title="Safety Advisory",
        )

    sanitized_message = input_guard_res.sanitized_text

    # Fetch or create conversation thread for current user
    conv, _ = await conversation_service.get_or_create_conversation(
        user_id=current_user.id,
        thread_id=request.thread_id,
        first_query=sanitized_message,
    )

    initial_state = {
        "user_id": current_user.id,
        "default_currency": current_user.default_currency,
        "messages": [
            HumanMessage(content=sanitized_message)
        ],
    }

    config = {
        "configurable": {
            "thread_id": conv.id,
        },
        "metadata": {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "currency": current_user.default_currency,
            "thread_id": conv.id,
        },
        "tags": ["expense-chat", f"user:{current_user.username}", f"thread:{conv.id}"],
        "run_name": f"chat-{current_user.username}",
    }

    graph = await get_graph()
    result = await graph.ainvoke(initial_state, config=config)

    messages = result["messages"]
    raw_response = messages[-1].content if messages else ""

    # Extract tool results for output grounding & hallucination validation
    tool_results = []
    for msg in messages:
        if getattr(msg, "type", "") == "tool" or msg.__class__.__name__ == "ToolMessage":
            content = getattr(msg, "content", None)
            if isinstance(content, dict):
                tool_results.append(content)
            elif isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        tool_results.append(parsed)
                except Exception:
                    pass

    # 2. Execute Output Guardrails (Format validation, Policy compliance, Grounding / Hallucination check)
    output_guard_res = await guardrails_manager.validate_output(
        response_text=raw_response,
        tool_results=tool_results,
    )

    return ChatResponse(
        response=output_guard_res.sanitized_text,
        thread_id=conv.id,
        title=conv.title,
    )


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    http_req: Request,
    current_user: User = Depends(get_current_user),
):
    """Stream conversation responses token-by-token with input & output guardrails applied."""
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    # 1. Execute Input Guardrails
    client_ip = http_req.client.host if http_req.client else None
    input_guard_res = await guardrails_manager.validate_input(
        text=request.message,
        user_id=current_user.id,
        client_ip=client_ip,
    )

    if input_guard_res.rate_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=input_guard_res.safe_response,
            headers={"Retry-After": str(input_guard_res.retry_after)},
        )

    if input_guard_res.blocked:
        # Stream the safe guardrail rejection message directly
        async def blocked_generator():
            yield f"data: {json.dumps({'type': 'metadata', 'thread_id': request.thread_id or 'security_notice', 'title': 'Safety Advisory'})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': input_guard_res.safe_response})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'thread_id': request.thread_id or 'security_notice', 'title': 'Safety Advisory'})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            blocked_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    sanitized_message = input_guard_res.sanitized_text

    # Fetch or create conversation thread for current user
    conv, _ = await conversation_service.get_or_create_conversation(
        user_id=current_user.id,
        thread_id=request.thread_id,
        first_query=sanitized_message,
    )

    initial_state = {
        "user_id": current_user.id,
        "default_currency": current_user.default_currency,
        "messages": [
            HumanMessage(content=sanitized_message)
        ],
    }

    config = {
        "configurable": {
            "thread_id": conv.id,
        },
        "metadata": {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "currency": current_user.default_currency,
            "thread_id": conv.id,
        },
        "tags": ["expense-chat", f"user:{current_user.username}", f"thread:{conv.id}"],
        "run_name": f"chat-stream-{current_user.username}",
    }

    graph = await get_graph()

    async def event_generator():
        try:
            # Yield metadata at start of stream
            yield f"data: {json.dumps({'type': 'metadata', 'thread_id': conv.id, 'title': conv.title})}\n\n"

            streamed_tokens = []
            tool_results = []

            async for event in graph.astream_events(initial_state, config=config, version="v2"):
                kind = event.get("event")
                name = event.get("name", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    content = getattr(chunk, "content", None)
                    if isinstance(content, str) and content:
                        streamed_tokens.append(content)
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                    elif isinstance(content, list):
                        for part in content:
                            if isinstance(part, str) and part:
                                streamed_tokens.append(part)
                                yield f"data: {json.dumps({'type': 'token', 'content': part})}\n\n"
                            elif isinstance(part, dict) and part.get("type") == "text":
                                text = part.get("text", "")
                                if text:
                                    streamed_tokens.append(text)
                                    yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"

                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': name, 'input': event.get('data', {}).get('input', {})})}\n\n"

                elif kind == "on_tool_end":
                    tool_out = event.get("data", {}).get("output")
                    if isinstance(tool_out, dict):
                        tool_results.append(tool_out)
                    elif hasattr(tool_out, "content") and isinstance(tool_out.content, dict):
                        tool_results.append(tool_out.content)
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': name})}\n\n"

            # Post-stream Output Policy Check (e.g. financial advice disclaimer)
            full_streamed_text = "".join(streamed_tokens)
            policy_res = await guardrails_manager.validate_output(full_streamed_text, tool_results=tool_results)
            if policy_res.disclaimer_added and guardrails_manager.settings.FINANCIAL_DISCLAIMER_TEXT not in full_streamed_text:
                disclaimer_chunk = f"\n\n{guardrails_manager.settings.FINANCIAL_DISCLAIMER_TEXT}"
                yield f"data: {json.dumps({'type': 'token', 'content': disclaimer_chunk})}\n\n"

            # Final done event
            yield f"data: {json.dumps({'type': 'done', 'thread_id': conv.id, 'title': conv.title})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



@app.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
):
    """Retrieve all conversations for the authenticated user, ordered by most recent first."""
    conversations = await conversation_service.get_user_conversations(user_id=current_user.id)
    return conversations


@app.get("/conversations/{thread_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieve a specific conversation and its stored message history from the checkpointer."""
    conv = await conversation_service.get_conversation(user_id=current_user.id, thread_id=thread_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    graph = await get_graph()
    messages_data = await conversation_service.get_conversation_messages(
        user_id=current_user.id,
        thread_id=thread_id,
        graph=graph,
    )

    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[MessageItem(**m) for m in messages_data],
    )


@app.delete("/conversations/{thread_id}")
async def delete_conversation(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation thread and its PostgreSQL checkpointer records."""
    checkpointer = await get_checkpointer()
    deleted = await conversation_service.delete_conversation(
        user_id=current_user.id,
        thread_id=thread_id,
        checkpointer=checkpointer,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or cannot be deleted.",
        )

    return {
        "success": True,
        "message": "Conversation deleted successfully.",
        "thread_id": thread_id,
    }