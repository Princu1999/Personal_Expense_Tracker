from datetime import datetime
from decimal import Decimal
from typing import Annotated, Union

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from app.services import expense_service


@tool
async def record_expense(
    amount: Union[float, int, str],
    category: str,
    description: str = "",
    transaction_date: str = "",
    state: Annotated[dict, InjectedState] = None,
) -> dict:
    """
    Record a user's expense.

    Parameters:
    - amount: Numeric value of the expense (e.g. 1000 or "1000.50").
    - category: Category of expense (e.g. Groceries, Food & Dining, Bills & Utilities, Rent & Mortgage, Transport, Fuel & Gas, Healthcare & Medical, Shopping, Subscriptions & Streaming, Travel & Vacation, Insurance, Education, Gifts & Celebrations, Emergency & Urgent, Other).
    - description: Optional detail or context for the expense.
    - transaction_date: Optional transaction date in YYYY-MM-DD format (e.g. "2026-08-14"). Leave blank for today.
    """

    if state is None:
        raise ValueError("Graph state is required.")

    user_id = state["user_id"]
    currency = state["default_currency"]

    messages = state.get("messages", [])
    raw_text = None

    if messages:
        last_message = messages[-1]
        if hasattr(last_message, "content"):
            raw_text = last_message.content

    # Clean and parse amount safely
    if isinstance(amount, str):
        cleaned_amount = "".join(c for c in amount if c.isdigit() or c in ".-")
        parsed_amount = Decimal(cleaned_amount) if cleaned_amount else Decimal("0.00")
    else:
        parsed_amount = Decimal(str(amount))

    # Parse transaction_date if provided
    parsed_date = None
    if transaction_date and transaction_date.strip():
        try:
            parsed_date = datetime.strptime(transaction_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            parsed_date = None

    expense = await expense_service.create_expense(
        user_id=int(user_id),
        amount=parsed_amount,
        currency=currency,
        category=category,
        description=description or None,
        transaction_date=parsed_date,
        raw_text=raw_text,
    )

    return {
        "success": True,
        "message": "Expense recorded successfully.",
        "expense_id": expense.id,
        "amount": float(expense.amount),
        "currency": expense.currency,
        "category": category,
        "description": expense.description or "",
        "transaction_date": str(expense.transaction_date),
    }