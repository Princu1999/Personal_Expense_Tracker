import asyncio
from datetime import date
from decimal import Decimal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.user import User
from app.services.category_service import (
    create_category,
    find_category_by_name,
    get_category,
)
from app.database.crud import (
    create_expense,
    delete_expense,
    get_expense,
    get_expenses,
    update_expense,
)


async def test_crud_operations():
    async with SessionLocal() as session:

        # --------------------------------
        # GET OR CREATE TEST USER
        # --------------------------------

        print("\n--- Getting or creating test user ---")

        result = await session.execute(
            select(User).where(
                User.username == "crud_test_user"
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                username="crud_test_user",
                email="crud_test_user@example.com",
                hashed_password="dummy_hash",
                default_currency="INR",
            )

            session.add(user)

            await session.commit()
            await session.refresh(user)

            print(
                f"Created test user: "
                f"id={user.id}, "
                f"username={user.username}"
            )
        else:
            print(
                f"Using existing test user: "
                f"id={user.id}, "
                f"username={user.username}"
            )

        user_id = user.id

        # --------------------------------
        # GET OR CREATE TEST CATEGORY
        # --------------------------------

        print("\n--- Getting or creating category ---")

        category = await find_category_by_name(
            session=session,
            user_id=user_id,
            name="Food",
        )

        if category is None:
            category = await create_category(
                session=session,
                user_id=user_id,
                name="Food",
            )

            print(
                f"Created category: "
                f"id={category.id}, "
                f"name={category.name}"
            )
        else:
            print(
                f"Using existing category: "
                f"id={category.id}, "
                f"name={category.name}"
            )

        # --------------------------------
        # FIND CATEGORY BY NAME
        # --------------------------------

        print("\n--- Finding category by name ---")

        found_category = await find_category_by_name(
            session=session,
            user_id=user_id,
            name="Food",
        )

        assert found_category is not None, "Category was not found."

        print(
            f"Found category: "
            f"id={found_category.id}, "
            f"name={found_category.name}"
        )

        # --------------------------------
        # GET CATEGORY BY ID
        # --------------------------------

        print("\n--- Getting category by ID ---")

        fetched_category = await get_category(
            session=session,
            user_id=user_id,
            category_id=category.id,
        )

        assert fetched_category is not None, "Category was not found by ID."

        print(
            f"Fetched category: "
            f"id={fetched_category.id}, "
            f"name={fetched_category.name}"
        )

        # --------------------------------
        # CREATE EXPENSE
        # --------------------------------

        print("\n--- Creating expense ---")

        expense = await create_expense(
            session=session,
            user_id=user_id,
            amount=Decimal("250.00"),
            currency="INR",
            category_id=category.id,
            description="Lunch",
            transaction_date=date.today(),
            raw_text="Spent 250 rupees on lunch",
        )

        assert expense is not None
        assert expense.id is not None

        print(
            f"Created expense: "
            f"id={expense.id}, "
            f"amount={expense.amount}, "
            f"currency={expense.currency}, "
            f"description={expense.description}"
        )

        # --------------------------------
        # GET ONE EXPENSE
        # --------------------------------

        print("\n--- Getting expense ---")

        fetched_expense = await get_expense(
            session=session,
            user_id=user_id,
            expense_id=expense.id,
        )

        assert fetched_expense is not None, "Expense was not found after creation."

        print(
            f"Fetched expense: "
            f"id={fetched_expense.id}, "
            f"amount={fetched_expense.amount}, "
            f"description={fetched_expense.description}"
        )

        # --------------------------------
        # GET ALL EXPENSES
        # --------------------------------

        print("\n--- Getting all expenses ---")

        expenses = await get_expenses(
            session=session,
            user_id=user_id,
        )

        assert len(expenses) > 0
        print(
            f"Found {len(expenses)} expense(s):"
        )

        for item in expenses:
            print(
                f"id={item.id}, "
                f"amount={item.amount}, "
                f"currency={item.currency}, "
                f"description={item.description}"
            )

        # --------------------------------
        # UPDATE EXPENSE
        # --------------------------------

        print("\n--- Updating expense ---")

        updated_expense = await update_expense(
            session=session,
            user_id=user_id,
            expense_id=expense.id,
            amount=Decimal("300.00"),
            description="Updated lunch",
        )

        assert updated_expense is not None, "Expense was not found during update."

        print(
            f"Updated expense: "
            f"id={updated_expense.id}, "
            f"amount={updated_expense.amount}, "
            f"description={updated_expense.description}"
        )

        # --------------------------------
        # VERIFY UPDATE
        # --------------------------------

        print("\n--- Verifying update ---")

        updated_check = await get_expense(
            session=session,
            user_id=user_id,
            expense_id=expense.id,
        )

        assert updated_check is not None, "Expense was not found after update."
        assert updated_check.amount == Decimal("300.00")

        print(
            f"Verified expense: "
            f"id={updated_check.id}, "
            f"amount={updated_check.amount}, "
            f"description={updated_check.description}"
        )

        # --------------------------------
        # DELETE EXPENSE
        # --------------------------------

        print("\n--- Deleting expense ---")

        deleted_expense = await delete_expense(
            session=session,
            user_id=user_id,
            expense_id=expense.id,
        )

        assert deleted_expense is not None, "Expense was not found during deletion."

        print(
            f"Deleted expense: "
            f"id={deleted_expense.id}"
        )

        # --------------------------------
        # VERIFY DELETE
        # --------------------------------

        print("\n--- Verifying deletion ---")

        deleted_check = await get_expense(
            session=session,
            user_id=user_id,
            expense_id=expense.id,
        )

        print(
            f"Expense after deletion: {deleted_check}"
        )

        assert deleted_check is None, "Expense still exists after deletion."

        # --------------------------------
        # SUCCESS
        # --------------------------------

        print("\n========================================")
        print("CRUD TEST PASSED")
        print("========================================")


main = test_crud_operations

if __name__ == "__main__":
    asyncio.run(test_crud_operations())
