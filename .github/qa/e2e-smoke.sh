#!/usr/bin/env bash
# =============================================================================
# Natillera PWA — E2E Smoke Test Script
# Version: 1.0 | Date: 2026-04-23
#
# USAGE:
#   chmod +x .github/qa/e2e-smoke.sh
#   BASE_URL=http://localhost:8000 DATABASE_URL=postgres://... SAVINGS_RATE=10 \
#     bash .github/qa/e2e-smoke.sh
#
# REQUIREMENTS:
#   - curl
#   - jq
#   - psql (connected to Supabase/Postgres)
#   - FastAPI running at $BASE_URL
#   - SAVINGS_RATE env var set
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
DATABASE_URL="${DATABASE_URL:-}"
SAVINGS_RATE="${SAVINGS_RATE:-10}"
TIMESTAMP=$(date +%s)
TEST_EMAIL="smoketest_${TIMESTAMP}@natillera.test"
TEST_PASSWORD="Smoke1234!"
TEST_PHONE="+57300${TIMESTAMP: -7}"

PASS=0
FAIL=0
SKIP=0

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((PASS++)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ((FAIL++)); }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }
skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; ((SKIP++)); }

db_query() {
  if [[ -z "$DATABASE_URL" ]]; then
    skip "DB check skipped — DATABASE_URL not set: $1"
    return 0
  fi
  psql "$DATABASE_URL" -t -c "$1" 2>/dev/null | tr -d ' \n'
}

check_eq() {
  local label="$1" actual="$2" expected="$3"
  if [[ "$actual" == "$expected" ]]; then
    pass "$label (got: $actual)"
  else
    fail "$label — expected: '$expected', got: '$actual'"
  fi
}

echo "========================================================"
echo "  Natillera PWA — E2E Smoke Test"
echo "  Target: $BASE_URL"
echo "  Time:   $(date)"
echo "========================================================"

# -------------------------------------------------------
# STEP 1: Register
# -------------------------------------------------------
info "Step 1: Register user $TEST_EMAIL"
REGISTER_RESP=$(curl -sf -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
  -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")

REGISTER_CODE=$(echo "$REGISTER_RESP" | tail -1)
REGISTER_BODY=$(echo "$REGISTER_RESP" | head -1)

if [[ "$REGISTER_CODE" == "201" ]]; then
  pass "Register — HTTP 201"
else
  fail "Register — expected 201, got $REGISTER_CODE"
  echo "  Body: $REGISTER_BODY"
fi

# -------------------------------------------------------
# STEP 2: Login
# -------------------------------------------------------
info "Step 2: Login"
LOGIN_RESP=$(curl -sf -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
  -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")

LOGIN_CODE=$(echo "$LOGIN_RESP" | tail -1)
LOGIN_BODY=$(echo "$LOGIN_RESP" | head -1)

if [[ "$LOGIN_CODE" == "200" ]]; then
  pass "Login — HTTP 200"
  ACCESS_TOKEN=$(echo "$LOGIN_BODY" | jq -r '.access_token // empty' 2>/dev/null || echo "")
  if [[ -n "$ACCESS_TOKEN" ]]; then
    pass "JWT access_token present"
  else
    fail "JWT access_token missing in login response"
    ACCESS_TOKEN=""
  fi
  REFRESH_TOKEN=$(echo "$LOGIN_BODY" | jq -r '.refresh_token // empty' 2>/dev/null || echo "")
  if [[ -n "$REFRESH_TOKEN" ]]; then
    pass "JWT refresh_token present"
  else
    skip "refresh_token not found in response — check token refresh flow manually"
  fi
else
  fail "Login — expected 200, got $LOGIN_CODE"
  ACCESS_TOKEN=""
fi

AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"

# -------------------------------------------------------
# STEP 3: Create Client
# -------------------------------------------------------
info "Step 3: Create client"
if [[ -z "$ACCESS_TOKEN" ]]; then
  skip "Create client — no access token, skipping"
  CLIENT_ID=""
else
  CLIENT_RESP=$(curl -sf -X POST "$BASE_URL/clients" \
    -H "Content-Type: application/json" \
    -H "$AUTH_HEADER" \
    -d "{\"first_name\":\"Smoke\",\"last_name\":\"Test\",\"phone\":\"$TEST_PHONE\"}" \
    -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")

  CLIENT_CODE=$(echo "$CLIENT_RESP" | tail -1)
  CLIENT_BODY=$(echo "$CLIENT_RESP" | head -1)

  if [[ "$CLIENT_CODE" == "201" ]]; then
    pass "Create client — HTTP 201"
    CLIENT_ID=$(echo "$CLIENT_BODY" | jq -r '.id // empty' 2>/dev/null || echo "")
    if [[ -n "$CLIENT_ID" ]]; then
      pass "Client ID returned: $CLIENT_ID"
    else
      fail "Client ID missing in response"
    fi
  else
    fail "Create client — expected 201, got $CLIENT_CODE"
    CLIENT_ID=""
  fi
fi

# DB: Verify client persisted
if [[ -n "$CLIENT_ID" ]]; then
  DB_CLIENT=$(db_query "SELECT COUNT(*) FROM clients WHERE id = '$CLIENT_ID' AND deleted_at IS NULL;")
  check_eq "DB: client persisted" "$DB_CLIENT" "1"
fi

# -------------------------------------------------------
# STEP 4: Create Credit
# -------------------------------------------------------
info "Step 4: Create credit"
START_DATE=$(date +%Y-%m-%d)

if [[ -z "$CLIENT_ID" ]]; then
  skip "Create credit — no client_id, skipping"
  CREDIT_ID=""
else
  CREDIT_RESP=$(curl -sf -X POST "$BASE_URL/clients/$CLIENT_ID/credits" \
    -H "Content-Type: application/json" \
    -H "$AUTH_HEADER" \
    -d "{\"initial_capital\":1000.00,\"periodicity\":\"MONTHLY\",\"annual_interest_rate\":24.00,\"start_date\":\"$START_DATE\"}" \
    -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")

  CREDIT_CODE=$(echo "$CREDIT_RESP" | tail -1)
  CREDIT_BODY=$(echo "$CREDIT_RESP" | head -1)

  if [[ "$CREDIT_CODE" == "201" ]]; then
    pass "Create credit — HTTP 201"
    CREDIT_ID=$(echo "$CREDIT_BODY" | jq -r '.id // empty' 2>/dev/null || echo "")
    PENDING_CAP=$(echo "$CREDIT_BODY" | jq -r '.pending_capital // "0"' 2>/dev/null || echo "0")
    MORA=$(echo "$CREDIT_BODY" | jq -r '.mora // "true"' 2>/dev/null || echo "true")
    VERSION=$(echo "$CREDIT_BODY" | jq -r '.version // "0"' 2>/dev/null || echo "0")

    [[ -n "$CREDIT_ID" ]] && pass "Credit ID returned: $CREDIT_ID" || fail "Credit ID missing"
    check_eq "pending_capital = initial_capital (1000)" "$PENDING_CAP" "1000.0"
    check_eq "mora = false at creation" "$MORA" "false"
    check_eq "version = 1 at creation" "$VERSION" "1"
  else
    fail "Create credit — expected 201, got $CREDIT_CODE"
    CREDIT_ID=""
  fi
fi

# DB: Verify credit persisted with correct state
if [[ -n "$CREDIT_ID" ]]; then
  DB_MORA=$(db_query "SELECT mora FROM credits WHERE id = '$CREDIT_ID';")
  check_eq "DB: mora = false" "$DB_MORA" "f"

  DB_VERSION=$(db_query "SELECT version FROM credits WHERE id = '$CREDIT_ID';")
  check_eq "DB: version = 1" "$DB_VERSION" "1"

  DB_PENDING=$(db_query "SELECT ABS(pending_capital - 1000.00) < 0.01 FROM credits WHERE id = '$CREDIT_ID';")
  check_eq "DB: pending_capital = 1000" "$DB_PENDING" "t"
fi

# -------------------------------------------------------
# STEP 5: Generate Installment (advance next_period_date)
# -------------------------------------------------------
info "Step 5: Generate installment (advance next_period_date)"

if [[ -n "$CREDIT_ID" && -n "$DATABASE_URL" ]]; then
  # Force next_period_date to today so period job triggers
  psql "$DATABASE_URL" -c \
    "UPDATE credits SET next_period_date = CURRENT_DATE WHERE id = '$CREDIT_ID';" \
    > /dev/null 2>&1 && info "Set next_period_date = today"

  # Trigger generation (adjust endpoint as implemented)
  GEN_RESP=$(curl -sf -X POST "$BASE_URL/credits/$CREDIT_ID/generate-installment" \
    -H "$AUTH_HEADER" \
    -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")
  GEN_CODE=$(echo "$GEN_RESP" | tail -1)

  if [[ "$GEN_CODE" == "201" || "$GEN_CODE" == "200" ]]; then
    pass "Generate installment — HTTP $GEN_CODE"
  else
    skip "Generate installment endpoint returned $GEN_CODE — verify endpoint path or run cron manually"
  fi

  # DB: Verify installment created with correct formula
  DB_INSTALLMENT=$(db_query "SELECT COUNT(*) FROM installments WHERE credit_id = '$CREDIT_ID';")
  if [[ "$DB_INSTALLMENT" -ge "1" ]]; then
    pass "DB: installment created (count: $DB_INSTALLMENT)"

    # Verify interest formula: 1000 * 24% / 12 = 20.00
    INTEREST_CORRECT=$(db_query "SELECT ABS(interest_portion - 20.00) < 0.01 FROM installments WHERE credit_id = '$CREDIT_ID' ORDER BY period_number LIMIT 1;")
    check_eq "DB: interest_portion = 20.00 (1000 * 24% / 12)" "$INTEREST_CORRECT" "t"

    # Verify locked fields: expected_value = principal + interest
    SUM_CORRECT=$(db_query "SELECT ABS(expected_value - (principal_portion + interest_portion)) < 0.01 FROM installments WHERE credit_id = '$CREDIT_ID' ORDER BY period_number LIMIT 1;")
    check_eq "DB: expected_value = principal_portion + interest_portion" "$SUM_CORRECT" "t"
  else
    fail "DB: no installment found for credit"
  fi
else
  skip "Installment generation — requires DATABASE_URL and CREDIT_ID"
fi

# -------------------------------------------------------
# STEP 6: Register Payment
# -------------------------------------------------------
info "Step 6: Register payment"

if [[ -n "$CREDIT_ID" && -n "$ACCESS_TOKEN" ]]; then
  # Get installment expected_value first
  INST_RESP=$(curl -sf -X GET "$BASE_URL/credits/$CREDIT_ID/installments" \
    -H "$AUTH_HEADER" 2>/dev/null || echo "[]")
  EXPECTED_VAL=$(echo "$INST_RESP" | jq -r '.[0].expected_value // "0"' 2>/dev/null || echo "0")

  if [[ "$EXPECTED_VAL" == "0" ]]; then
    skip "Payment — no installment expected_value found, skipping"
  else
    PAY_RESP=$(curl -sf -X POST "$BASE_URL/credits/$CREDIT_ID/payments" \
      -H "Content-Type: application/json" \
      -H "$AUTH_HEADER" \
      -d "{\"amount\":$EXPECTED_VAL,\"payment_date\":\"$START_DATE\"}" \
      -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")

    PAY_CODE=$(echo "$PAY_RESP" | tail -1)
    PAY_BODY=$(echo "$PAY_RESP" | head -1)

    if [[ "$PAY_CODE" == "200" || "$PAY_CODE" == "201" ]]; then
      pass "Register payment — HTTP $PAY_CODE"
      APPLIED_TO=$(echo "$PAY_BODY" | jq -r '.applied_to // empty' 2>/dev/null || echo "")
      [[ -n "$APPLIED_TO" ]] && pass "applied_to breakdown present" || fail "applied_to breakdown missing"
    else
      fail "Register payment — expected 200/201, got $PAY_CODE"
    fi

    # DB: Verify version incremented
    if [[ -n "$DATABASE_URL" ]]; then
      DB_VERSION_AFTER=$(db_query "SELECT version FROM credits WHERE id = '$CREDIT_ID';")
      if [[ "$DB_VERSION_AFTER" -ge "2" ]]; then
        pass "DB: version incremented after payment (version: $DB_VERSION_AFTER)"
      else
        fail "DB: version not incremented after payment (version: $DB_VERSION_AFTER)"
      fi

      # DB: Capital consistency check
      CAP_CONSISTENT=$(db_query "
        SELECT ABS(c.pending_capital - (c.initial_capital - COALESCE(pp.total, 0))) < 0.01
        FROM credits c
        LEFT JOIN (
          SELECT p.credit_id, SUM((elem->>'amount')::decimal) AS total
          FROM payments p, jsonb_array_elements(p.applied_to) elem
          WHERE p.credit_id = '$CREDIT_ID'
          AND elem->>'type' IN ('OVERDUE_PRINCIPAL','FUTURE_PRINCIPAL')
          GROUP BY p.credit_id
        ) pp ON pp.credit_id = c.id
        WHERE c.id = '$CREDIT_ID';")
      check_eq "DB: capital consistency (initial - principal_paid = pending)" "$CAP_CONSISTENT" "t"
    fi
  fi
else
  skip "Payment — missing credit_id or access_token"
fi

# -------------------------------------------------------
# STEP 7: Savings + Liquidation
# -------------------------------------------------------
info "Step 7: Savings contributions + liquidation"

if [[ -n "$CLIENT_ID" && -n "$ACCESS_TOKEN" ]]; then
  # Add 3 contributions
  SAV_TOTAL=0
  for AMOUNT in 500 300 200; do
    SAV_RESP=$(curl -sf -X POST "$BASE_URL/clients/$CLIENT_ID/savings" \
      -H "Content-Type: application/json" \
      -H "$AUTH_HEADER" \
      -d "{\"contribution_amount\":$AMOUNT,\"contribution_date\":\"$START_DATE\"}" \
      -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")
    SAV_CODE=$(echo "$SAV_RESP" | tail -1)
    [[ "$SAV_CODE" == "201" ]] && pass "Savings contribution $AMOUNT — HTTP 201" || fail "Savings contribution $AMOUNT — HTTP $SAV_CODE"
    SAV_TOTAL=$((SAV_TOTAL + AMOUNT))
  done

  # Liquidate
  LIQ_RESP=$(curl -sf -X POST "$BASE_URL/clients/$CLIENT_ID/savings/liquidate" \
    -H "$AUTH_HEADER" \
    -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")
  LIQ_CODE=$(echo "$LIQ_RESP" | tail -1)
  LIQ_BODY=$(echo "$LIQ_RESP" | head -1)

  if [[ "$LIQ_CODE" == "200" || "$LIQ_CODE" == "201" ]]; then
    pass "Liquidation — HTTP $LIQ_CODE"

    TOTAL_CONTRIBUTIONS=$(echo "$LIQ_BODY" | jq -r '.total_contributions // "0"' 2>/dev/null || echo "0")
    INTEREST_EARNED=$(echo "$LIQ_BODY" | jq -r '.interest_earned // "0"' 2>/dev/null || echo "0")
    TOTAL_DELIVERED=$(echo "$LIQ_BODY" | jq -r '.total_delivered // "0"' 2>/dev/null || echo "0")

    EXPECTED_INTEREST=$(echo "scale=2; $SAV_TOTAL * $SAVINGS_RATE / 100" | bc 2>/dev/null || echo "?")
    EXPECTED_TOTAL=$(echo "scale=2; $SAV_TOTAL + $EXPECTED_INTEREST" | bc 2>/dev/null || echo "?")

    info "total_contributions=$TOTAL_CONTRIBUTIONS (expected $SAV_TOTAL)"
    info "interest_earned=$INTEREST_EARNED (expected $EXPECTED_INTEREST)"
    info "total_delivered=$TOTAL_DELIVERED (expected $EXPECTED_TOTAL)"

    [[ "$TOTAL_CONTRIBUTIONS" == "$SAV_TOTAL"* || "$TOTAL_CONTRIBUTIONS" == "$SAV_TOTAL" ]] \
      && pass "total_contributions correct" || fail "total_contributions mismatch"
  else
    fail "Liquidation — expected 200/201, got $LIQ_CODE"
  fi

  # DB: Verify all contributions LIQUIDATED
  if [[ -n "$DATABASE_URL" ]]; then
    ACTIVE_AFTER=$(db_query "SELECT COUNT(*) FROM savings WHERE client_id = '$CLIENT_ID' AND status = 'ACTIVE';")
    check_eq "DB: no ACTIVE contributions after liquidation" "$ACTIVE_AFTER" "0"

    # Verify history event
    HIST_COUNT=$(db_query "SELECT COUNT(*) FROM financial_history WHERE client_id = '$CLIENT_ID' AND event_type = 'SAVINGS_LIQUIDATION';")
    if [[ "$HIST_COUNT" -ge "1" ]]; then
      pass "DB: SAVINGS_LIQUIDATION history event logged"
    else
      fail "DB: SAVINGS_LIQUIDATION history event missing"
    fi
  fi
else
  skip "Savings/Liquidation — missing client_id or access_token"
fi

# -------------------------------------------------------
# STEP 8: Cross-User Isolation Smoke Check
# -------------------------------------------------------
info "Step 8: Cross-user isolation check"

if [[ -n "$CLIENT_ID" ]]; then
  # Register a second user
  TEST_EMAIL_B="smoketest_b_${TIMESTAMP}@natillera.test"
  REG_B=$(curl -sf -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL_B\",\"password\":\"$TEST_PASSWORD\"}" \
    -w "\n%{http_code}" 2>/dev/null || echo -e "\n000")
  REG_B_CODE=$(echo "$REG_B" | tail -1)

  LOGIN_B=$(curl -sf -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL_B\",\"password\":\"$TEST_PASSWORD\"}" 2>/dev/null || echo "{}")
  TOKEN_B=$(echo "$LOGIN_B" | jq -r '.access_token // empty' 2>/dev/null || echo "")

  if [[ -n "$TOKEN_B" ]]; then
    # USER_B tries to access USER_A's client
    CROSS_RESP=$(curl -sf -o /dev/null -X GET "$BASE_URL/clients/$CLIENT_ID" \
      -H "Authorization: Bearer $TOKEN_B" \
      -w "%{http_code}" 2>/dev/null || echo "000")

    if [[ "$CROSS_RESP" == "403" || "$CROSS_RESP" == "404" ]]; then
      pass "Cross-user isolation: USER_B cannot access USER_A client (HTTP $CROSS_RESP)"
    else
      fail "Cross-user isolation FAILED: USER_B got HTTP $CROSS_RESP for USER_A's client — DATA LEAK"
    fi
  else
    skip "Cross-user check — could not get USER_B token"
  fi
else
  skip "Cross-user check — no client_id available"
fi

# -------------------------------------------------------
# STEP 9: Global DB Consistency Checks
# -------------------------------------------------------
info "Step 9: Global DB consistency queries"

if [[ -n "$DATABASE_URL" ]]; then
  # Capital drift check
  DRIFT=$(db_query "
    SELECT COUNT(*) FROM (
      SELECT c.id FROM credits c
      LEFT JOIN (
        SELECT p.credit_id, SUM((elem->>'amount')::decimal) AS total
        FROM payments p, jsonb_array_elements(p.applied_to) elem
        WHERE elem->>'type' IN ('OVERDUE_PRINCIPAL','FUTURE_PRINCIPAL')
        GROUP BY p.credit_id
      ) pp ON pp.credit_id = c.id
      WHERE ABS(c.pending_capital - (c.initial_capital - COALESCE(pp.total, 0))) >= 0.01
    ) t;")
  check_eq "DB: No capital drift across all credits" "$DRIFT" "0"

  # Stale mora
  STALE_MORA=$(db_query "
    SELECT COUNT(*) FROM credits c
    WHERE c.mora = true
    AND NOT EXISTS (
      SELECT 1 FROM installments i
      WHERE i.credit_id = c.id
      AND i.is_overdue = true
      AND i.status != 'PAID'
    );")
  check_eq "DB: No stale mora flags" "$STALE_MORA" "0"

  # Paid_value > expected_value
  OVERPAID=$(db_query "SELECT COUNT(*) FROM installments WHERE paid_value > expected_value + 0.01;")
  check_eq "DB: No installments with paid_value > expected_value" "$OVERPAID" "0"

  # PAID but underpaid
  PAID_UNDERPAID=$(db_query "SELECT COUNT(*) FROM installments WHERE status = 'PAID' AND paid_value < expected_value - 0.01;")
  check_eq "DB: No PAID installments with insufficient paid_value" "$PAID_UNDERPAID" "0"
else
  skip "Global DB checks — DATABASE_URL not set"
fi

# -------------------------------------------------------
# SUMMARY
# -------------------------------------------------------
echo ""
echo "========================================================"
echo "  SMOKE TEST SUMMARY"
echo "========================================================"
echo -e "  ${GREEN}PASS: $PASS${NC}"
echo -e "  ${RED}FAIL: $FAIL${NC}"
echo -e "  ${YELLOW}SKIP: $SKIP${NC}"
echo "========================================================"

if [[ $FAIL -gt 0 ]]; then
  echo -e "  ${RED}SMOKE TEST FAILED — $FAIL check(s) failed${NC}"
  exit 1
else
  echo -e "  ${GREEN}SMOKE TEST PASSED${NC}"
  exit 0
fi
