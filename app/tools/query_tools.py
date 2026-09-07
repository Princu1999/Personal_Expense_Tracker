from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from app.services import expense_service


@tool
async def query_expenses(
    query: str = "",
    state: Annotated[dict, InjectedState] = None,
) -> dict:
    """
    Retrieve and query the user's recorded expenses from the database.
    Use this tool whenever the user asks to view, list, search, summarize, or calculate totals of their expenses.

    Parameters:
    - query: Optional search or summary filter description (e.g. "show all", "food expenses", "last week").
    """

    if state is None:
        raise ValueError("Graph state is required.")

    user_id = int(state["user_id"])

    expenses = await expense_service.get_expenses(
        user_id=user_id,
    )

    data = [
        {
            "id": expense.id,
            "amount": float(expense.amount),
            "currency": expense.currency,
            "category": expense.category.name if expense.category else "Uncategorized",
            "category_id": expense.category_id,
            "description": expense.description or "",
            "transaction_date": str(expense.transaction_date),
        }
        for expense in expenses
    ]

    return {
        "success": True,
        "query": query,
        "count": len(data),
        "data": data,
    }