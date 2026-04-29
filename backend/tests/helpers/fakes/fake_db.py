"""
Fake Database Interface — in-memory PostgreSQL replacement for testing.
Simula la interfaz de Supabase sin red ni dependencias externas.
"""
from typing import Any, Optional
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from datetime import date, datetime


class FakeDatabase:
    """
    Fake que simula el cliente Supabase.
    Úsalo en tests de integración para no depender de DB real.
    """

    def __init__(self):
        self._tables: dict[str, list[dict]] = {
            "credits": [],
            "installments": [],
            "payments": [],
            "clients": [],
            "savings": [],
            "history": [],
        }
        self._executed_rpc = []

    def table(self, table_name: str):
        """Retorna interfaz de tabla."""
        return _FakeTable(self, table_name)

    def rpc(self, func_name: str, params: dict):
        """Simula llamada RPC."""
        self._executed_rpc.append((func_name, params))
        return _FakeRpc(self)


class _FakeTable:
    """Interfaz de tabla fake."""

    def __init__(self, db: FakeDatabase, table_name: str):
        self._db = db
        self._table_name = table_name
        self._filters = {}
        self._order_field: Optional[str] = None
        self._order_desc = False

    def select(self, *fields):
        return self

    def insert(self, payload: dict | list[dict]):
        if isinstance(payload, list):
            rows = []
            for item in payload:
                item["id"] = item.get("id", str(uuid4()))
                item["created_at"] = datetime.now().isoformat()
                item["updated_at"] = datetime.now().isoformat()
                self._db._tables[self._table_name].append(item)
                rows.append(item.copy())
            return _FakeInsertResult(rows)
        payload["id"] = payload.get("id", str(uuid4()))
        payload["created_at"] = datetime.now().isoformat()
        payload["updated_at"] = datetime.now().isoformat()
        self._db._tables[self._table_name].append(payload)
        return _FakeInsertResult([payload])

    def update(self, payload: dict):
        return _FakeUpdate(self._db, self._table_name, payload)

    def eq(self, field: str, value: Any):
        self._filters[field] = value
        return self

    def in_(self, field: str, values: list):
        self._filters[f"{field}_in"] = values
        return self

    def lt(self, field: str, value: Any):
        self._filters[f"{field}_lt"] = value
        return self

    def gt(self, field: str, value: Any):
        self._filters[f"{field}_gt"] = value
        return self

    def is_(self, field: str, value: Any):
        self._filters[field] = value
        return self

    def single(self):
        return _FakeSingleSelect(self._db, self._table_name, self._filters.copy())

    def order(self, field: str, desc: bool = False):
        self._order_field = field
        self._order_desc = desc
        return self

    def execute(self):
        return _FakeSelectResult(self._db, self._table_name, self._filters.copy())


class _FakeInsertResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    async def execute(self):
        return MagicMock(data=self._rows)


class _FakeUpdate:
    def __init__(self, db: FakeDatabase, table_name: str, payload: dict):
        self._db = db
        self._table_name = table_name
        self._payload = payload
        self._filters = {}

    def eq(self, field: str, value: Any):
        self._filters[field] = value
        return self

    def in_(self, field: str, values: list):
        self._filters[f"{field}_in"] = values
        return self

    async def execute(self):
        table = self._db._tables[self._table_name]
        updated = []
        for row in table:
            match = all(
                row.get(k) == v for k, v in self._filters.items() if not k.endswith("_in")
            )
            if not match:
                continue
            if any(
                row.get(k) in v for k, v in self._filters.items() if k.endswith("_in")
            ):
                match = True
            if not match:
                continue
            row.update(self._payload)
            row["updated_at"] = datetime.now().isoformat()
            updated.append(row)
        return MagicMock(data=updated)


class _FakeSingleSelect:
    """SELECT que retorna una fila."""

    def __init__(self, db: FakeDatabase, table_name: str, filters: dict):
        self._db = db
        self._table_name = table_name
        self._filters = filters

    async def execute(self):
        table = self._db._tables[self._table_name]
        for row in table:
            if all(row.get(k) == v for k, v in self._filters.items() if not k.endswith("_in")):
                return MagicMock(data=row)
        return MagicMock(data=None)


class _FakeSelectResult:
    """Resultado de SELECT."""

    def __init__(self, db: FakeDatabase, table_name: str, filters: dict):
        self._db = db
        self._table_name = table_name
        self._filters = filters

    async def execute(self):
        table = self._db._tables[self._table_name]
        rows = []
        for row in table:
            if all(
                row.get(k) == v
                for k, v in self._filters.items()
                if not k.endswith("_in")
            ):
                rows.append(row)
            elif any(
                row.get(k.rstrip("_in")) in v
                for k, v in self._filters.items()
                if k.endswith("_in")
            ):
                rows.append(row)
        return MagicMock(data=rows)


class _FakeRpc:
    """Resultado de RPC."""

    def __init__(self, db: FakeDatabase):
        self._db = db
        self._response_data = {
            "payment_id": str(uuid4()),
            "total_amount": "500.00",
            "applied_to": [],
            "updated_credit_snapshot": {
                "pending_capital": "9500.00",
                "mora": False,
                "version": 2,
            },
            "idempotent": False,
        }

    def mock_response(self, data: dict):
        self._response_data = data
        return self

    async def execute(self):
        return MagicMock(data=self._response_data)


def create_fake_db_with_credit(
    credit_id: str,
    user_id: str,
    pending_capital: Decimal = Decimal("10000.00"),
    status: str = "ACTIVE",
) -> tuple[FakeDatabase, dict]:
    """Factory: crea DB fake con credit precargado."""
    db = FakeDatabase()
    credit = {
        "id": credit_id,
        "user_id": user_id,
        "client_id": str(uuid4()),
        "initial_capital": str(pending_capital),
        "pending_capital": str(pending_capital),
        "version": 1,
        "status": status,
        "mora": False,
        "mora_since": None,
        "annual_interest_rate": "12.00",
        "periodicity": "MONTHLY",
    }
    db._tables["credits"].append(credit)
    return db, credit


def create_fake_db_with_installments(
    credit_id: str,
    count: int = 6,
    start_date: date = None,
) -> list[dict]:
    """Factory: crea lista de installments."""
    if start_date is None:
        start_date = date.today()
    installments = []
    for i in range(count):
        inst_date = start_date.replace(
            month=((start_date.month - 1 + i) % 12) + 1,
            year=start_date.year + (start_date.month - 1 + i) // 12,
        )
        installments.append({
            "id": str(uuid4()),
            "credit_id": credit_id,
            "expected_date": inst_date.isoformat(),
            "expected_value": "933.33",
            "interest_portion": "100.00",
            "principal_portion": "833.33",
            "paid_value": "0.00",
            "status": "UPCOMING",
            "is_overdue": False,
        })
    return installments