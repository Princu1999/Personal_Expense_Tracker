import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.graph import build_graph


async def run_test(user_message: str):
    graph = build_graph()

    print("=" * 60)
    print("USER")
    print("=" * 60)
    print(user_message)

    result = await graph.ainvoke(
        {
            "user_id": "1",
            "default_currency": "INR",
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        }
    )

    print()
    print("=" * 60)
    print("ASSISTANT")
    print("=" * 60)

    for message in result["messages"]:
        if getattr(message, "type", None) == "ai":
            safe_text = message.content.encode(
                sys.stdout.encoding or "utf-8", errors="replace"
            ).decode(sys.stdout.encoding or "utf-8", errors="replace")
            print(safe_text)


async def test_graph_query():
    graph = build_graph()
    result = await graph.ainvoke(
        {
            "user_id": "1",
            "default_currency": "INR",
            "messages": [
                {
                    "role": "user",
                    "content": "Show me my expenses",
                }
            ],
        }
    )
    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) > 1


if __name__ == "__main__":
    asyncio.run(run_test("Show me my expenses"))
