from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.graph.state import ExpenseState
from app.graph.nodes import (
    llm_node,
    tools,
)


def build_graph(checkpointer=None):
    graph = StateGraph(ExpenseState)

    graph.add_node("llm", llm_node)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "llm")

    graph.add_conditional_edges(
        "llm",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )

    graph.add_edge("tools", "llm")
    workflow = graph.compile(checkpointer=checkpointer)

    return workflow


# if __name__ == "__main__":
#     workflow = build_graph()

#     png_bytes = workflow.get_graph().draw_mermaid_png()

#     with open("expense_graph.png", "wb") as f:
#         f.write(png_bytes)

#     print("Graph saved as expense_graph.png")