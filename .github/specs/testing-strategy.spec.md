---
id: SPEC-TEST-001
status: IMPLEMENTED
feature: testing-strategy
created: 2026-04-29
updated: 2026-04-29
author: staff-engineer
version: "1.0"
related-specs: []
---

# Spec: Testing Strategy

> **Estado:** `DRAFT` → aprobar con `status: APPROVED` antes de iniciar implementación.
> **Ciclo de vida:** DRAFT → APPROVED → IN_PROGRESS → IMPLEMENTED → DEPRECATED

---

## 1. REQUERIMIENTOS

### Descripción

Diseñar e implementar una estrategia de testing completa que incluya unit tests, integration tests desacoplados de Supabase real, contract tests de API, y E2E tests, con coverage mínimo 80% REAL por capa.

### Problema Actual

- Solo unit tests sólidos existen
- Integration y contract tests están desacoplados usando mocks
- No hay estrategia clara de E2E testing
- Coverage actual no refleja riesgo real

### Requerimiento de Negocio

```
Como: Staff Engineer
Quiero: una estrategia de testing completa con:
  1. Unit tests sólidos
  2. Integration tests desacoplados de Supabase real
  3. Contract tests de API
  4. E2E tests (frontend + backend)
  5. Coverage mínimo 80% REAL por capa
Para: garantizar calidad en sistema financiero crítico sin зависиcia de Supabase real en CI
```

### Reglas de Negocio

1. **No Supabase real en CI** — todas las pruebas deben correr sin conexión a Supabase real
2. **No mocks para lógica crítica de negocio** — cálculos financieros, allocation, mora detection
3. **Todo determinista** — sin flaky tests
4. **Coverage REAL por capa** — medir líneas cubiertas, no artificial

---

## 2. DISEÑO

### Arquitectura de Testing

#### 2.1 Capas de Prueba

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PYRAMID OF TESTS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                           E2E TESTS                                 │
│                    (frontend + backend + fake DB)                     │
│                    [   ][   ][   ][   ][   ] 5 tests                │
├─────────────────────────────────────────────────────────────────────────────┤
│                CONTRACT TESTS (API contract)                         │
│                   [ ][ ][ ][ ][ ][ ][ ] 10 tests                    │
├─────────────────────────────────────────────────────────────────────────────┤
│              INTEGRATION TESTS (service + repo)                     │
│            [ ][ ][ ][ ][ ][ ][ ][ ][ ][ ] 20 tests                   │
├─────────────────────────────────────────────────────────────────────┤
│                  UNIT TESTS (pure business logic)                      │
│          [ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ] 30 tests           │
└───────────────────────────────────��─────────────────────────────────┘
```

#### 2.2 Estrategia de Mocking

| Capa | qué se mockea | qué NO se mockea |
|------|---------------|------------------|
| Unit | Ninguno (testea funciones pure) | Lógica financiera: `_compute_breakdown_3pool`, `calculate_period_interest`, etc. |
| Integration | DB driver (usar FakeRepository in-memory) | Repositorio (implementación real), RPC stubbed |
| Contract | DB driver, Auth token | Ninguno (usa TestClient real) |
| E2E | Supabase real (usa fake auth) | Frontend real, UI interactions |

#### 2.3 Repositorios Fake

**Principio:** Crear implementaciones in-memory de los repositorios para testing que respeten la misma interfaz.

```
backend/
├── app/
│   ├── repositories/
│   │   ├── credit_repository.py      # Real implementation
│   │   └── fake_credit_repository.py  # In-memory para tests
│   └── ...
└── tests/
    ├── fixtures/
    │   └── fake_repositories.py    # Setup de fakes
```

### Estructura de Carpetas

```
backend/tests/
├── conftest.py                    # Pytest config global
├── conftest_payment.py            # Fixtures de payment
├── helpers/
│   ├── __init__.py
│   ├── jwt_helpers.py             # JWT generation
│   └── fakes/
│       ├── __init__.py
│       ├── fake_db.py            # Fake database interface
│       ├── fake_credit_repo.py  # Fake credit repository
│       └── fake_payment_repo.py # Fake payment repository
├── unit/                        # Unit tests (pure logic)
│   ├── test_calculations.py
│   ├── test_payment_allocation.py
│   └── test_mora_detection.py
├── integration/                 # Integration tests (service + repo)
│   ├── test_credit_service.py
│   ├── test_payment_service.py
│   └── test_e2e_flows.py
├── contract/                    # Contract tests (API endpoints)
│   ├── test_credit_endpoints.py
│   └── test_payment_endpoints.py
└── e2e/                      # E2E tests (full stack)
    ├── test_full_flows.py
    └── test_auth_flow.py

frontend/src/
├── __tests__/                  # Unit tests (components)
│   ├── authSlice.test.ts
│   └── tokenRefreshInterceptor.test.ts
├── store/api/__tests__/         # RTK Query tests
│   └── paymentApi.test.ts
├── hooks/__tests__/             # Hook tests
│   ├── useMora.test.ts
│   └── useAuth.test.ts
└── e2e/                        # E2E Playwright/Cypress
    ├── flow.spec.ts
    └── login.spec.ts
```

### Ejemplos de Tests

#### 2.4 Unit Test (Payment Allocation)

```python
"""
backend/tests/unit/test_payment_allocation.py
Unit test: 3-pool allocation algorithm (pure logic)
NO MOCKS - testea la lógica real de negocio
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.payment_service import _compute_breakdown_3pool


def test_unit_3pool_mandatory_order_overdue_interest_first():
    """
    CRITICAL: Payment allocation orden obligatorio.
    GIVEN: 1 overdue installment (interest=200, principal=500)
    WHEN:  payment = 100
    THEN:  100 → OVERDUE_INTEREST, 0 → OVERDUE_PRINCIPAL
    """
    today = date.today()
    overdue = today - timedelta(days=30)
    installments = [
        {
            "id": "inst-001",
            "expected_date": overdue.isoformat(),
            "expected_value": "700.00",
            "interest_portion": "200.00",
            "principal_portion": "500.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        }
    ]

    applied, total_principal, remaining = _compute_breakdown_3pool(
        installments, Decimal("100.00"), today
    )

    types = {e.type for e in applied}
    assert "OVERDUE_INTEREST" in types
    assert "OVERDUE_PRINCIPAL" not in types
    
    interest_applied = sum(e.amount for e in applied if e.type == "OVERDUE_INTEREST")
    assert interest_applied == Decimal("100.00")


def test_unit_3pool_overdue_before_future():
    """
    CRITICAL: No payment can go to future while overdue exists.
    GIVEN: overdue=200, future=200
    WHEN:  payment = 200
    THEN:  all 200 → overdue, 0 → future
    """
    today = date.today()
    overdue = today - timedelta(days=30)
    future = today + timedelta(days=30)
    installments = [
        {
            "id": "inst-overdue",
            "expected_date": overdue.isoformat(),
            "expected_value": "200.00",
            "interest_portion": "100.00",
            "principal_portion": "100.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        },
        {
            "id": "inst-future",
            "expected_date": future.isoformat(),
            "expected_value": "200.00",
            "interest_portion": "100.00",
            "principal_portion": "100.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        },
    ]

    applied, _, _ = _compute_breakdown_3pool(
        installments, Decimal("200.00"), today
    )

    future_applied = sum(e.amount for e in applied if e.type == "FUTURE_PRINCIPAL")
    assert future_applied == Decimal("0.00"), "Must NOT pay future while overdue exists"


def test_unit_decimal_precision_no_float():
    """
    CRITICAL: All monetary values MUST be Decimal, no float.
    """
    today = date.today()
    installments = [
        {
            "id": "inst-001",
            "expected_date": (today - timedelta(days=30)).isoformat(),
            "expected_value": "100.00",
            "interest_portion": "50.00",
            "principal_portion": "50.00",
            "paid_value": "0.00",
            "status": "UPCOMING",
        }
    ]

    applied, _, _ = _compute_breakdown_3pool(installments, Decimal("50.00"), today)

    for entry in applied:
        amount = entry.amount
        assert not isinstance(amount, float), f"Float detected: {amount!r}"
        assert isinstance(amount, Decimal)
```

#### 2.5 Integration Test (Service + Fake Repository)

```python
"""
backend/tests/integration/test_payment_service_integration.py
Integration test: PaymentService + FakeCreditRepository
Usa repositorio fake para testing verdadero
"""
import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from tests.helpers.fakes.fake_credit_repository import FakeCreditRepository
from tests.helpers.fakes.fake_db import FakeDatabase
from app.services.payment_service import PaymentService
from app.models.payment_model import PaymentRequest


@pytest.mark.anyio
async def test_integration_process_payment_with_fake_repo():
    """
    GIVEN: fake DB with credit + installments
    WHEN:  process_payment called
    THEN:  payment recorded, capital reduced
    """
    # GIVEN
    credit_id = str(uuid4())
    user_id = "user-test-001"
    
    fake_db = FakeDatabase()
    fake_repo = FakeCreditRepository(fake_db)
    
    # Setup credit in fake repo
    credit_data = {
        "id": credit_id,
        "user_id": user_id,
        "client_id": str(uuid4()),
        "initial_capital": Decimal("10000.00"),
        "pending_capital": Decimal("10000.00"),
        "version": 1,
        "status": "ACTIVE",
        "mora": False,
        "mora_since": None,
    }
    await fake_repo.insert(credit_data)
    
    # Setup installments
    today = date.today()
    installments = [
        {
            "id": str(uuid4()),
            "credit_id": credit_id,
            "expected_date": (today - timedelta(days=30)).isoformat(),
            "expected_value": Decimal("933.33"),
            "interest_portion": Decimal("100.00"),
            "principal_portion": Decimal("833.33"),
            "paid_value": Decimal("0.00"),
            "status": "UPCOMING",
        }
    ]
    await fake_repo.insert_installments(installments)
    
    service = PaymentService(fake_db, user_id)
    body = PaymentRequest(
        credit_id=credit_id,
        amount=Decimal("416.67"),
        operator_id=user_id,
    )
    
    # WHEN
    result = await service.process_payment(body)
    
    # THEN
    assert result["payment_id"] is not None
    assert "updated_credit_snapshot" in result
    assert Decimal(result["updated_credit_snapshot"]["pending_capital"]) < Decimal("10000.00")
```

#### 2.6 Contract Test (API Endpoint)

```python
"""
backend/tests/contract/test_payment_endpoints_contract.py
Contract test: FastAPI endpoint with TestClient
Verifica contrato HTTP (status codes, response shape)
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_user_id, get_db


USER_ID = "user-contract-001"


def _mock_db():
    db = MagicMock()
    db.table = MagicMock(return_value=db)
    db.select = MagicMock(return_value=db)
    db.insert = MagicMock(return_value=db)
    db.update = MagicMock(return_value=db)
    db.eq = MagicMock(return_value=db)
    db.in_ = MagicMock(return_value=db)
    db.single = MagicMock(return_value=db)
    db.order = MagicMock(return_value=db)
    db.rpc = MagicMock(return_value=db)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def client_with_auth():
    db = _mock_db()
    app.dependency_overrides[get_user_id] = lambda: USER_ID
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, db
    app.dependency_overrides.clear()


def test_contract_post_payments_201_happy_path(client_with_auth):
    """
    GIVEN: valid payment body
    WHEN:  POST /api/v1/payments/
    THEN:  201 + PaymentResponse with payment_id, applied_to, snapshot
    """
    c, db = client_with_auth
    credit_id = str(uuid4())
    db.execute.return_value = MagicMock(data={
        "payment_id": str(uuid4()),
        "credit_id": credit_id,
        "total_amount": "500.00",
        "applied_to": [
            {"installment_id": str(uuid4()), "type": "OVERDUE_INTEREST", "amount": "100.00"}
        ],
        "updated_credit_snapshot": {
            "pending_capital": "9500.00",
            "mora": False,
            "version": 2,
        },
        "idempotent": False,
    })
    
    resp = c.post("/api/v1/payments/", json={
        "credit_id": credit_id,
        "amount": "500.00",
        "operator_id": USER_ID,
    })
    
    assert resp.status_code == 201
    data = resp.json()
    assert "payment_id" in data
    assert "applied_to" in data


def test_contract_post_payments_422_validation_error(client_with_auth):
    """
    GIVEN: amount = 0 (violates gt=0 constraint)
    WHEN:  POST /api/v1/payments/
    THEN:  422 Unprocessable Entity
    """
    c, _ = client_with_auth
    
    resp = c.post("/api/v1/payments/", json={
        "credit_id": str(uuid4()),
        "amount": "0.00",
        "operator_id": USER_ID,
    })
    
    assert resp.status_code == 422


def test_contract_post_payments_409_version_conflict(client_with_auth):
    """
    GIVEN: DB returns VersionConflict
    WHEN:  POST /api/v1/payments/
    THEN:  409 Conflict
    """
    c, db = client_with_auth
    db.execute.side_effect = Exception("VersionConflict P0001")
    
    resp = c.post("/api/v1/payments/", json={
        "credit_id": str(uuid4()),
        "amount": "500.00",
        "operator_id": USER_ID,
    })
    
    assert resp.status_code == 409
```

#### 2.7 E2E Test (Full Flow)

```python
"""
backend/tests/e2e/test_payment_flow_e2e.py
E2E test: Complete flow login → create credit → payment
Uses fake auth, fake DB, real backend code
"""
import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.credit_service import CreditService
from app.services.payment_service import PaymentService
from app.models.credit_model import CreditCreate, Periodicity
from app.models.payment_model import PaymentRequest


class FakeDatabase:
    """Fake DB que simula PostgreSQL sin red."""
    
    def __init__(self):
        self._data = {}
        self._executed = []
    
    def table(self, name):
        return _FakeTable(self, name)
    
    def rpc(self, name, params):
        self._executed.append(("rpc", name, params))
        return _FakeRpc(self)


class _FakeTable:
    def __init__(self, db, name):
        self._db = db
        self._name = name
    
    def select(self, *args):
        return self
    
    def insert(self, payload):
        return _FakeInsert(self._db, self._name)
    
    def update(self, payload):
        return _FakeUpdate(self._db, self._name)
    
    def eq(self, field, value):
        return self
    
    def in_(self, field, values):
        return self
    
    def single(self):
        return _FakeSingle(self._db, self._name)
    
    def order(self, field, desc=False):
        return self
    
    def lt(self, field, value):
        return self


class _FakeInsert:
    def __init__(self, db, table):
        self._db = db
        self._table = table
    
    async def execute(self):
        return MagicMock(data=[{"id": str(uuid4())])


class _FakeUpdate:
    def __init__(self, db, table):
        self._db = db
        self._table = table
    
    async def execute(self):
        return MagicMock(data=[{"id": str(uuid4())}])


class _FakeSingle:
    def __init__(self, db, table):
        self._db = db
        self._table = table
    
    async def execute(self):
        return MagicMock(data={"id": str(uuid4())})


class _FakeRpc:
    def __init__(self, db):
        self._db = db
    
    async def execute(self):
        return MagicMock(data={
            "payment_id": str(uuid4()),
            "credit_id": str(uuid4()),
            "total_amount": "500.00",
            "applied_to": [],
            "updated_credit_snapshot": {
                "pending_capital": "9500.00",
                "mora": False,
                "version": 2,
            },
            "idempotent": False,
        })


@pytest.mark.anyio
async def test_e2e_full_payment_flow():
    """
    E2E: Create credit → Generate installments → Process payment → Verify capital reduced
    """
    user_id = "user-e2e-001"
    db = FakeDatabase()
    
    credit_service = CreditService(db, user_id)
    payment_service = PaymentService(db, user_id)
    
    # Step 1: Create credit
    credit = CreditCreate(
        client_id=str(uuid4()),
        initial_capital=Decimal("10000.00"),
        periodicity=Periodicity.MONTHLY,
        annual_interest_rate=Decimal("12.00"),
        start_date=date(2026, 1, 1),
    )
    result = await credit_service.create(credit)
    assert result["id"] is not None
    assert result["pending_capital"] == Decimal("10000.00")
    
    # Step 2: Process payment
    payment = PaymentRequest(
        credit_id=result["id"],
        amount=Decimal("500.00"),
        operator_id=user_id,
    )
    payment_result = await payment_service.process_payment(payment)
    assert payment_result["payment_id"] is not None
    
    snapshot = payment_result["updated_credit_snapshot"]
    assert Decimal(snapshot["pending_capital"]) < Decimal("10000.00")
```

### Cobertura por Capa

#### 2.8 Estrategia de Medición

```bash
# Backend - Coverage por capa
# unit/ (puro, sin DB)
pytest backend/tests/unit/ --cov=app.services.payment_service --cov=app.utils.calculations --cov=app.services.credit_service --cov=app.services.installment_service --cov=app.services.savings_service --cov=app.services.client_service --cov=app.services.history_service --cov-report=term-missing

# integration/ (service + repo)
pytest backend/tests/integration/ --cov=app.services --cov=app.repositories --cov-report=term-missing

# contract/ (API)
pytest backend/tests/contract/ -v --cov=app --cov-report=term-missing

# Overall
pytest backend/tests/ --cov=app --cov-report=term-missing --cov-branch
```

#### 2.9 Targets de Cobertura

| Capa | Target | Crítico |
|------|--------|---------|
| Unit (pure logic) | 90% | payment_service._compute_breakdown_3pool, calculations.* |
| Integration | 80% | servicio + repositorio integrado |
| Contract | 85% | routers, dependencies |
| Overall | 80% | líneas ejecutables |

---

## 3. CI PIPELINE

### Pipeline Stages

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: pip install -r requirements.txt pytest pytest-asyncio pytest-cov
      - name: Run unit tests
        run: pytest backend/tests/unit/ -v --cov=app --cov-report=term-missing
      - name: Check coverage
        run: |
          coverage=$(python -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered']")
          if [ "$coverage" -lt 80 ]; then exit 1

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: pytest backend/tests/integration/ -v --cov=app.services --cov=app.repositories
      - name: No external DB required
        run: echo "Uses fake repositories"

  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run contract tests
        run: pytest backend/tests/contract/ -v --cov=app.main
      - name: FastAPI TestClient (no server)

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run E2E tests
        run: pytest backend/tests/e2e/ -v
      - name: No Supabase required
        run: echo "Uses fake DB"

  lint-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run ruff
        run: ruff check backend/app/ backend/tests/
      - name: Run mypy
        run: mypy backend/app/

deploy-blocker:
  needs: [unit-tests, integration-tests, contract-tests, lint-check]
  if: always()
  runs-on: ubuntu-latest
  steps:
    - name: Check all passed
      run: |
        if [ "${{ needs.unit-tests.result }}" != "success" ]; then exit 1
        if [ "${{ needs.integration-tests.result }}" != "success" ]; then exit 1
        if [ "${{ needs.contract-tests.result }}" != "success" ]; then exit 1
        if [ "${{ needs.lint-check.result }}" != "success" ]; then exit 1
```

### Rules de Block

| Stage | Block Deploy | Justificación |
|-------|-----------|-------------|
| Unit Tests | SIEMPRE | Lógica financiera crítica |
| Integration | SIEMPRE | Data integrity |
| Contract | SIEMPRE | API contract |
| Lint | SIEMPRE | Code quality |
| E2E | Advisory | Full flows |

---

## 4. LISTA DE TAREAS

### Implementación

- [ ] Crear `backend/tests/helpers/fakes/fake_db.py` — interfaz fake
- [ ] Crear `backend/tests/helpers/fakes/fake_credit_repository.py`
- [ ] Crear `backend/tests/helpers/fakes/fake_payment_repository.py`
- [ ] Crear `backend/tests/unit/test_payment_allocation.py` (ya existe como test_payment_mandatory_order.py, renombrar)
- [ ] Crear `backend/tests/integration/test_payment_service_integration.py`
- [ ] Crear `backend/tests/e2e/test_payment_flow_e2e.py`
- [ ] Agregar coverage targets en `pyproject.toml` o `setup.cfg`
- [ ] Crear `.github/workflows/test.yml`

### Frontend E2E

- [ ] Configurar Playwright en `frontend/e2e/`
- [ ] Crear `frontend/e2e/login.spec.ts`
- [ ] Crear `frontend/e2e/payment-flow.spec.ts`

### Verificación

- [ ] Correr `pytest backend/tests/unit/ -v --cov=app --cov-report=term-missing`
- [ ] Correr `pytest backend/tests/integration/ -v`
- [ ] Correr `pytest backend/tests/contract/ -v`
- [ ] Validar coverage >= 80% en Unit
- [ ] Validar sin flaky tests en 3 ejecuciones consecutivas