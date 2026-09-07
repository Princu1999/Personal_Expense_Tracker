from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.category import Category
from app.models.expense import Expense


async def create_expense(
    session: AsyncSession,
    user_id: int,
    amount: Decimal,
    currency: str,
    category_id: int,
    description: str | None,
    transaction_date: date,
    raw_text: str | None = None,
) -> Expense:
    category_result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        )
    )

    category = category_result.scalar_one_or_none()

    if category is None:
        raise ValueError(
            "Category does not exist or does not belong to this user."
        )

    expense = Expense(
        user_id=user_id,
        amount=amount,
        currency=currency,
        category_id=category_id,
        description=description,
        transaction_date=transaction_date,
        raw_text=raw_text,
    )

    session.add(expense)

    await session.commit()
    await session.refresh(expense)

    return expense


async def get_expenses(
    session: AsyncSession,
    user_id: int,
) -> list[Expense]:
    result = await session.execute(
        select(Expense)
        .options(joinedload(Expense.category))
        .where(Expense.user_id == user_id)
        .order_by(Expense.transaction_date.desc())
    )

    return list(result.scalars().all())


async def get_expense(
    session: AsyncSession,
    user_id: int,
    expense_id: int,
) -> Expense | None:
    result = await session.execute(
        select(Expense)
        .options(joinedload(Expense.category))
        .where(
            Expense.id == expense_id,
            Expense.user_id == user_id,
        )
    )

    return result.scalar_one_or_none()


async def update_expense(
    session: AsyncSession,
    user_id: int,
    expense_id: int,
    amount: Decimal | None = None,
    currency: str | None = None,
    category_id: int | None = None,
    description: str | None = None,
    transaction_date: date | None = None,
    raw_text: str | None = None,
) -> Expense | None:
    expense = await get_expense(
        session,
        user_id,
        expense_id,
    )

    if expense is None:
        return None

    if amount is not None:
        expense.amount = amount

    if currency is not None:
        expense.currency = currency

    if category_id is not None:
        category_result = await session.execute(
            select(Category).where(
                Category.id == category_id,
                Category.user_id == user_id,
            )
        )

        category = category_result.scalar_one_or_none()

        if category is None:
            raise ValueError(
                "Category does not exist or does not belong to this user."
            )

        expense.category_id = category_id

    if description is not None:
        expense.description = description

    if transaction_date is not None:
        expense.transaction_date = transaction_date

    if raw_text is not None:
        expense.raw_text = raw_text

    await session.commit()
    await session.refresh(expense)

    return expense


async def delete_expense(
    session: AsyncSession,
    user_id: int,
    expense_id: int,
) -> Expense | None:
    expense = await get_expense(
        session,
        user_id,
        expense_id,
    )

    if expense is None:
        return None

    await session.delete(expense)
    await session.commit()

    return expense