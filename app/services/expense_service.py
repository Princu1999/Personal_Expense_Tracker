from datetime import date
from decimal import Decimal

from app.database import crud
from app.database.category_crud import get_or_create_category
from app.database.session import SessionLocal
from app.models.expense import Expense


async def create_expense(
    user_id: int,
    amount: Decimal,
    currency: str,
    category: str,
    description: str | None = None,
    transaction_date: date | None = None,
    raw_text: str | None = None,
) -> Expense:
    async with SessionLocal() as session:
        category_obj = await get_or_create_category(
            session=session,
            user_id=user_id,
            name=category,
        )

        return await crud.create_expense(
            session=session,
            user_id=user_id,
            amount=amount,
            currency=currency,
            category_id=category_obj.id,
            description=description,
            transaction_date=transaction_date or date.today(),
            raw_text=raw_text,
        )


async def get_expenses(
    user_id: int,
) -> list[Expense]:
    async with SessionLocal() as session:
        return await crud.get_expenses(
            session=session,
            user_id=user_id,
        )


async def get_expense(
    user_id: int,
    expense_id: int,
) -> Expense | None:
    async with SessionLocal() as session:
        return await crud.get_expense(
            session=session,
            user_id=user_id,
            expense_id=expense_id,
        )


async def update_expense(
    user_id: int,
    expense_id: int,
    amount: Decimal | None = None,
    currency: str | None = None,
    category_id: int | None = None,
    description: str | None = None,
    transaction_date: date | None = None,
    raw_text: str | None = None,
) -> Expense | None:
    async with SessionLocal() as session:
        return await crud.update_expense(
            session=session,
            user_id=user_id,
            expense_id=expense_id,
            amount=amount,
            currency=currency,
            category_id=category_id,
            description=description,
            transaction_date=transaction_date,
            raw_text=raw_text,
        )


async def delete_expense(
    user_id: int,
    expense_id: int,
) -> Expense | None:
    async with SessionLocal() as session:
        return await crud.delete_expense(
            session=session,
            user_id=user_id,
            expense_id=expense_id,
        )