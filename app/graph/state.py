from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ExpenseState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    default_currency: str