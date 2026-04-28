from abc import ABC, abstractmethod
from typing import Any
import asyncpg
from supabase._async.client import AsyncClient as SupabaseClient, create_client as create_supabase_client
from app.config import get_settings
from urllib.parse import urlparse


class DatabaseInterface(ABC):
    @abstractmethod
    async def execute(self, query: str, *args: Any):
        pass

    @abstractmethod
    def table(self, table_name: str):
        pass


class TableInterface(ABC):
    @abstractmethod
    def select(self, *columns: str):
        pass

    @abstractmethod
    def insert(self, data: dict):
        pass

    @abstractmethod
    def update(self, data: dict):
        pass


class LocalDatabase(DatabaseInterface):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def execute(self, query: str, *args: Any):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetch(self, query: str, *args: Any):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return rows

    def table(self, table_name: str):
        return LocalTable(self.pool, table_name)


class QueryResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class LocalTable(TableInterface):
    def __init__(self, pool: asyncpg.Pool, table_name: str):
        self.pool = pool
        self.table_name = table_name
        self._columns = "*"
        self._filters = []
        self._filter_type = []
        self._is_delete = False
        self._is_update = False
        self._update_data = {}
        self._insert_data = {}
        self._returning = "*"
        self._count = None
        self._single = False
        self._range_start = None
        self._range_end = None

    def select(self, *columns: str, count=None):
        self._columns = ", ".join(columns) if columns else "*"
        if count:
            self._count = count
        return self

    def eq(self, column: str, value: Any):
        self._filters.append((column, "=", value))
        self._filter_type.append("eq")
        return self

    def is_(self, column: str, value: Any):
        self._filters.append((column, "IS", value))
        self._filter_type.append("is")
        return self

    def in_(self, column: str, values: list):
        self._filters.append((column, "IN", values))
        self._filter_type.append("in")
        return self

    def or_(self, condition: str):
        self._or_condition = condition
        return self

    def lt(self, column: str, value: Any):
        self._filters.append((column, "<", value))
        self._filter_type.append("lt")
        return self

    def gte(self, column: str, value: Any):
        self._filters.append((column, ">=", value))
        self._filter_type.append("gte")
        return self

    def single(self):
        self._single = True
        return self

    def range(self, start: int, end: int):
        self._range_start = start
        self._range_end = end
        return self

    def insert(self, data: dict):
        self._is_insert = True
        self._insert_data = data
        return self

    def update(self, data: dict):
        self._is_update = True
        self._update_data = data
        return self

    async def execute(self):
        if self._is_insert:
            return await self._execute_insert()
        if self._is_update:
            return await self._execute_update()
        return await self._execute_select()

    async def _execute_insert(self):
        columns = list(self._insert_data.keys())
        values = list(self._insert_data.values())
        placeholders = [f"${i+1}" for i in range(len(values))]
        query = f"""INSERT INTO {self.table_name} ({", ".join(columns)}) VALUES ({", ".join(placeholders)}) RETURNING {self._returning}"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return QueryResult([dict(row)] if row else [])

    async def _execute_update(self):
        set_clauses = []
        values = []
        for i, (col, val) in enumerate(self._update_data.items()):
            set_clauses.append(f"{col} = ${i+1}")
            values.append(val)
        params_start = len(values) + 1
        where_clauses = []
        for col, op, val in self._filters:
            if op == "=":
                where_clauses.append(f"{col} = ${params_start}")
            params_start += 1
            values.append(val)
        query = f"""UPDATE {self.table_name} SET {", ".join(set_clauses)} WHERE {" AND ".join(where_clauses)} RETURNING {self._returning}"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return QueryResult([dict(row)] if row else [])

    async def _execute_select(self):
        columns = self._columns
        query = f"SELECT {columns} FROM {self.table_name}"
        values = []
        where_clauses = []
        params_start = 1
        for (col, op, val) in self._filters:
            if op == "=":
                where_clauses.append(f"{col} = ${params_start}")
            elif op == "IS":
                where_clauses.append(f"{col} IS ${params_start}")
            elif op == "IN":
                placeholders = [f"${params_start+i}" for i in range(len(val))]
                where_clauses.append(f"{col} IN ({', '.join(placeholders)})")
                values.extend(val)
                params_start += len(val)
                continue
            elif op == "<":
                where_clauses.append(f"{col} < ${params_start}")
            elif op == ">=":
                where_clauses.append(f"{col} >= ${params_start}")
            params_start += 1
            values.append(val)
        if self._filters:
            query += " WHERE " + " AND ".join(where_clauses)
        if self._range_start is not None and self._range_end is not None:
            query += f" LIMIT {self._range_end - self._range_start + 1} OFFSET {self._range_start}"
        async with self.pool.acquire() as conn:
            if self._single:
                row = await conn.fetchrow(query, *values)
                return QueryResult([dict(row)] if row else [])
            rows = await conn.fetch(query, *values)
            return QueryResult([dict(row) for row in rows])


class SupabaseDatabase(DatabaseInterface):
    def __init__(self, client: SupabaseClient):
        self.client = client

    async def execute(self, query: str, *args: Any):
        result = await self.client.rpc("exec_sql", {"query": query, "params": args}).execute()
        return result.data or []

    def table(self, table_name: str):
        return SupabaseTable(self.client, table_name)


class SupabaseTable(TableInterface):
    def __init__(self, client: SupabaseClient, table_name: str):
        self.client = client
        self.table_name = table_name

    def select(self, *columns: str, count=None):
        cols = ", ".join(columns) if columns else "*"
        self._query = self.client.table(self.table_name).select(cols, count=count)
        return self

    def eq(self, column: str, value: Any):
        self._query = self._query.eq(column, value)
        return self

    def is_(self, column: str, value: Any):
        self._query = self._query.is_(column, value)
        return self

    def in_(self, column: str, values: list):
        self._query = self._query.in_(column, values)
        return self

    def or_(self, condition: str):
        self._query = self._query.or_(condition)
        return self

    def lt(self, column: str, value: Any):
        self._query = self._query.lt(column, value)
        return self

    def gte(self, column: str, value: Any):
        self._query = self._query.gte(column, value)
        return self

    def single(self):
        self._query = self._query.single()
        return self

    def range(self, start: int, end: int):
        self._query = self._query.range(start, end)
        return self

    def insert(self, data: dict):
        self._query = self.client.table(self.table_name).insert(data)
        return self

    def update(self, data: dict):
        self._query = self.client.table(self.table_name).update(data)
        return self

    async def execute(self):
        result = await self._query.execute()
        return QueryResult(result.data, count=result.count if hasattr(result, "count") else None)


_db: DatabaseInterface | None = None


async def init_database() -> None:
    global _db
    settings = get_settings()

    if settings.environment == "local":
        _db = await init_local()
    else:
        _db = await init_supabase()


async def init_local() -> LocalDatabase:
    settings = get_settings()
    parsed = urlparse(settings.database_url)
    pool = await asyncpg.create_pool(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        user=parsed.username or "postgres",
        password=parsed.password or "postgres",
        database=parsed.path.lstrip("/") or "postgres",
        min_size=2,
        max_size=10,
    )
    return LocalDatabase(pool)


async def init_supabase() -> SupabaseDatabase:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "Supabase not configured. Set ENVIRONMENT=production and "
            "SUPABASE_URL, SUPABASE_KEY environment variables."
        )
    client = await create_supabase_client(settings.supabase_url, settings.supabase_key)
    return SupabaseDatabase(client)


def get_database() -> DatabaseInterface:
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


def is_supabase() -> bool:
    return get_settings().environment == "production"


async def close_database() -> None:
    global _db
    if _db is not None and isinstance(_db, LocalDatabase):
        await _db.pool.close()
    _db = None