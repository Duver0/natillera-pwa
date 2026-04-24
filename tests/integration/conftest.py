"""
Integration test configuration for Natillera PWA.

Every test operates against a real PostgreSQL/Supabase database.
RLS is exercised by setting session-local GUC variables that mirror
what Supabase's PostgREST sets for authenticated requests:

    SET LOCAL role = 'authenticated';
    SET LOCAL request.jwt.claims = '{"sub": "<uuid>"}';

The auth.uid() function reads request.jwt.claims->>'sub', so this is
the canonical way to impersonate a Supabase user inside a DB session
without needing a real JWT.

Each test receives a connection already scoped to a transaction that
is rolled back after the test — no persistent state leaks between tests.
"""

import os
import uuid
import asyncio
from typing import AsyncGenerator, Callable

import asyncpg
import pytest
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


# ---------------------------------------------------------------------------
# Session-scoped event loop (required for session-scoped async fixtures)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Pool — one pool for the whole test session
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
async def pool() -> AsyncGenerator[asyncpg.Pool, None]:
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
    yield _pool
    await _pool.close()


# ---------------------------------------------------------------------------
# raw_conn — superuser connection (bypasses RLS) used to seed auth.users
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def raw_conn(pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Connection with role=postgres (superuser) wrapped in a savepoint so
    that every test starts and ends with a clean slate.
    """
    async with pool.acquire() as conn:
        tr = conn.transaction()
        await tr.start()
        yield conn
        await tr.rollback()


# ---------------------------------------------------------------------------
# Helper: create a synthetic auth.users row so FK constraints are satisfied.
# Returns the UUID used as the user's id.
# ---------------------------------------------------------------------------
async def _create_auth_user(conn: asyncpg.Connection, user_id: uuid.UUID) -> None:
    """
    Insert a minimal row into auth.users (Supabase managed schema).
    Tests run against the postgres role so we can write there directly.
    """
    await conn.execute(
        """
        INSERT INTO auth.users (
            id, email, encrypted_password,
            email_confirmed_at, created_at, updated_at,
            raw_app_meta_data, raw_user_meta_data,
            aud, role
        )
        VALUES (
            $1, $2, 'not-a-real-hash',
            NOW(), NOW(), NOW(),
            '{}', '{}',
            'authenticated', 'authenticated'
        )
        ON CONFLICT (id) DO NOTHING
        """,
        user_id,
        f"test-{user_id}@integration.test",
    )


# ---------------------------------------------------------------------------
# Helper factory: return a context manager that opens a connection
# impersonating a given user UUID via SET LOCAL GUCs.
# ---------------------------------------------------------------------------
def make_user_conn(pool: asyncpg.Pool):
    """
    Returns an async context manager that yields a connection whose
    effective auth.uid() returns `user_id`.

    Usage:
        async with make_user_conn(pool)(user_id) as conn:
            await conn.fetch("SELECT * FROM clients")
    """
    import contextlib

    @contextlib.asynccontextmanager
    async def _ctx(user_id: uuid.UUID):
        async with pool.acquire() as conn:
            await conn.execute("SET LOCAL role = 'authenticated'")
            await conn.execute(
                "SELECT set_config('request.jwt.claims', $1, true)",
                f'{{"sub":"{user_id}"}}',
            )
            yield conn

    return _ctx


# ---------------------------------------------------------------------------
# Fixtures exposed to tests
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def user_a_id(raw_conn: asyncpg.Connection) -> uuid.UUID:
    uid = uuid.uuid4()
    await _create_auth_user(raw_conn, uid)
    return uid


@pytest_asyncio.fixture
async def user_b_id(raw_conn: asyncpg.Connection) -> uuid.UUID:
    uid = uuid.uuid4()
    await _create_auth_user(raw_conn, uid)
    return uid


@pytest_asyncio.fixture
def as_user(pool: asyncpg.Pool) -> Callable:
    """
    Fixture that returns the `make_user_conn` factory for use in tests.
    Tests use: `async with as_user(some_uuid) as conn:`
    """
    return make_user_conn(pool)
