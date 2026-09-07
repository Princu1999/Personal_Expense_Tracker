from datetime import date
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from app.config import settings
from app.graph.state import ExpenseState
from app.tools.expense_tools import record_expense
from app.tools.query_tools import query_expenses


llm = ChatGroq(
    model=settings.GROQ_MODEL,
    temperature=0,
    api_key=settings.GROQ_API_KEY if settings.GROQ_API_KEY else None,
)


tools = [
    record_expense,
    query_expenses,
]


llm_with_tools = llm.bind_tools(tools)


async def llm_node(state: ExpenseState) -> ExpenseState:
    messages = state["messages"]
    today_str = date.today().isoformat()

    system_message = SystemMessage(
        content=(
            f"You are a helpful and precise personal expense assistant. Today's date is {today_str}.\n\n"
            "Guidelines:\n"
            "- When the user tells you about spending money or wants to record an expense, call the `record_expense` tool.\n"
            "- Choose specific, appropriate categories (e.g. Groceries, Food & Dining, Coffee & Snacks, Bills & Utilities, Rent & Mortgage, Transport, Fuel & Gas, Taxi & Rideshare, Travel & Vacation, Shopping, Clothing & Apparel, Electronics & Gadgets, Healthcare & Medical, Fitness & Gym, Personal Care & Grooming, Entertainment, Subscriptions & Streaming, Books & Education, Childcare & Kids, Pet Care & Veterinary, Insurance, Investments & Savings, Taxes & Government Fees, Gifts & Celebrations, Charity & Donations, Emergency & Urgent, Moving & Relocation, Other).\n"
            "- When the user asks to view, check, list, summarize, or calculate totals of their expenses, call the `query_expenses` tool.\n"
            "- When presenting expenses from `query_expenses`, ALWAYS clearly state the category, amount, currency, date, and description (if available) for each expense.\n"
            "- Accurately convert relative dates (such as 'yesterday', 'last Friday', 'today') to YYYY-MM-DD format using today's date.\n"
            "- For greetings or general questions, respond politely without calling tools."
        )
    )

    response = await llm_with_tools.ainvoke(
        [system_message] + messages
    )

    return {
        "messages": [response],
    }