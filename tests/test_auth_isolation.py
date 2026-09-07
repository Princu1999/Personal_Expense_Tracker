import asyncio
from datetime import date
from decimal import Decimal
import pytest
from httpx import AsyncClient, ASGITransport

from app.api.chat import app
from app.database.base import Base
from app.database.connection import engine
from app.models import User, Category, Expense
from app.services import auth_service, expense_service


@pytest.mark.asyncio
async def test_full_auth_and_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        
        # Test: Unauthenticated access to /chat
        unauth_resp = await ac.post("/chat", json={"message": "hello"})
        assert unauth_resp.status_code == 401, f"Expected 401 for unauthenticated request, got {unauth_resp.status_code}"

        # 2. Register User 1
        user1_email = f"alice_{asyncio.get_event_loop().time()}@example.com"
        user1_username = f"alice_{int(asyncio.get_event_loop().time() * 1000)}"
        reg1_resp = await ac.post(
            "/auth/register",
            json={
                "username": user1_username,
                "email": user1_email,
                "password": "password123",
                "default_currency": "INR",
            },
        )
        assert reg1_resp.status_code == 201, f"Register failed: {reg1_resp.text}"
        user1_data = reg1_resp.json()
        token1 = user1_data["access_token"]
        user1_id = user1_data["user"]["id"]

        # Verify default categories were seeded for User 1
        from app.database.session import SessionLocal
        from sqlalchemy import select
        async with SessionLocal() as session:
            cats_res = await session.execute(select(Category).where(Category.user_id == user1_id))
            user1_cats = [c.name for c in cats_res.scalars().all()]
            assert len(user1_cats) == len(auth_service.DEFAULT_CATEGORIES)
            assert "Emergency & Urgent" in user1_cats
            assert "Rent & Mortgage" in user1_cats
            assert "Groceries" in user1_cats

        # 3. Register User 2
        user2_email = f"bob_{asyncio.get_event_loop().time()}@example.com"
        user2_username = f"bob_{int(asyncio.get_event_loop().time() * 1000)}"
        reg2_resp = await ac.post(
            "/auth/register",
            json={
                "username": user2_username,
                "email": user2_email,
                "password": "password456",
                "default_currency": "USD",
            },
        )
        assert reg2_resp.status_code == 201, f"Register failed: {reg2_resp.text}"
        user2_data = reg2_resp.json()
        token2 = user2_data["access_token"]
        user2_id = user2_data["user"]["id"]

        # Test: Duplicate email fails
        dup_resp = await ac.post(
            "/auth/register",
            json={
                "username": "unique_user",
                "email": user1_email,
                "password": "password123",
            },
        )
        assert dup_resp.status_code == 400

        # Test: Login with valid credentials
        login_resp = await ac.post(
            "/auth/login",
            json={
                "email": user1_email,
                "password": "password123",
            },
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

        # Test: Login with wrong password fails
        bad_login_resp = await ac.post(
            "/auth/login",
            json={
                "email": user1_email,
                "password": "wrongpassword",
            },
        )
        assert bad_login_resp.status_code == 401

        # Test: /auth/me for User 1
        me_resp1 = await ac.get("/auth/me", headers={"Authorization": f"Bearer {token1}"})
        assert me_resp1.status_code == 200
        assert me_resp1.json()["email"] == user1_email

        # 4. Create expenses directly for each user in service layer to test strict isolation
        exp1 = await expense_service.create_expense(
            user_id=user1_id,
            amount=Decimal("150.00"),
            currency="INR",
            category="Food",
            description="Alice's Pizza",
        )

        exp2 = await expense_service.create_expense(
            user_id=user2_id,
            amount=Decimal("300.00"),
            currency="USD",
            category="Transport",
            description="Bob's Taxi",
        )

        # 5. Verify User 1's expenses only contain exp1
        user1_expenses = await expense_service.get_expenses(user_id=user1_id)
        user1_exp_ids = [e.id for e in user1_expenses]
        assert exp1.id in user1_exp_ids, "Alice's expense should be in Alice's list"
        assert exp2.id not in user1_exp_ids, "Bob's expense MUST NOT be in Alice's list"

        # 6. Verify User 2's expenses only contain exp2
        user2_expenses = await expense_service.get_expenses(user_id=user2_id)
        user2_exp_ids = [e.id for e in user2_expenses]
        assert exp2.id in user2_exp_ids, "Bob's expense should be in Bob's list"
        assert exp1.id not in user2_exp_ids, "Alice's expense MUST NOT be in Bob's list"

        # 7. Verify query_expenses tool returns the category name
        from app.tools.query_tools import query_expenses
        q_res1 = await query_expenses.ainvoke({"query": "show expenses", "state": {"user_id": user1_id}})
        assert q_res1["success"] is True
        assert len(q_res1["data"]) == 1
        assert q_res1["data"][0]["category"] == "Food"
        assert q_res1["data"][0]["amount"] == 150.0

        q_res2 = await query_expenses.ainvoke({"query": "show expenses", "state": {"user_id": user2_id}})
        assert q_res2["success"] is True
        assert len(q_res2["data"]) == 1
        assert q_res2["data"][0]["category"] == "Transport"
        assert q_res2["data"][0]["amount"] == 300.0
