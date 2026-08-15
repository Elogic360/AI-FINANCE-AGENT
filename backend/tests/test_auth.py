"""
FinPilot AI — Auth Endpoint Tests
──────────────────────────────────
Tests for POST /auth/register, POST /auth/login, GET /auth/me.
"""

from __future__ import annotations

import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_register(client):
    """POST /api/v1/auth/register creates a new user and returns tokens."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "business_name": "New Business",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registering with the same email twice returns 409."""
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePass123!",
        "business_name": "Dup Business",
    }
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login(client):
    """POST /api/v1/auth/login returns tokens for valid credentials."""
    # First register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "MyPassword123!",
            "business_name": "Login Biz",
        },
    )

    # Then login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "MyPassword123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Login with wrong password returns 401."""
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpw@example.com",
            "password": "CorrectPass123!",
            "business_name": "Wrong PW Biz",
        },
    )

    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpw@example.com",
            "password": "WrongPassword!",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client):
    """GET /api/v1/auth/me returns the authenticated user's profile."""
    # Register
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "meuser@example.com",
            "password": "MySecurePass123!",
            "business_name": "Me Biz",
        },
    )
    token = reg.json()["access_token"]

    # Get /me
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "meuser@example.com"
    assert data["role"] == "owner"
    assert "id" in data
    assert "business_id" in data


@pytest.mark.asyncio
async def test_get_current_user_no_token(client):
    """GET /api/v1/auth/me without a token returns 403 (no auth header)."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403
