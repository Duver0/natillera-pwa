/**
 * GHERKIN ACCEPTANCE: Credit + Payment flow.
 *
 * Feature: Credit and Payment
 *   Scenario: Create credit → view installments → register payment → verify mora cleared
 *
 * RTK endpoints are called directly against msw-intercepted HTTP.
 */
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import { makeStore } from '../test-utils'
import { apiSlice } from '../store/api/apiSlice'
import type { Credit, Installment, PaymentPreview, PaymentResponse } from '../types'

const BASE = 'http://localhost:8000/api/v1'

// ---- fixtures ----
const CREDIT: Credit = {
  id: 'cr1', user_id: 'u1', client_id: 'c1',
  initial_capital: 1200, pending_capital: 1200, version: 1,
  periodicity: 'MONTHLY', annual_interest_rate: 24,
  status: 'ACTIVE', start_date: '2024-01-01',
  mora: false,
  created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
}

const INSTALLMENTS: Installment[] = [
  {
    id: 'i1', user_id: 'u1', credit_id: 'cr1',
    period_number: 1, expected_date: '2024-02-01',
    expected_value: 124, principal_portion: 100, interest_portion: 24,
    paid_value: 0, is_overdue: true, status: 'UPCOMING',
    created_at: '2024-01-01T00:00:00Z',
  },
]

const PREVIEW: PaymentPreview = {
  credit_id: 'cr1', total_amount: '124.00',
  applied_to: [{ type: 'OVERDUE_INTEREST', amount: '24.00', installment_id: 'i1' }],
  unallocated: '0.00',
  updated_credit_snapshot: { pending_capital: '1100.00', mora: false, version: 2 },
}

const PAYMENT_RESP: PaymentResponse = {
  payment_id: 'p1', credit_id: 'cr1', total_amount: '124.00',
  applied_to: PREVIEW.applied_to,
  updated_credit_snapshot: { pending_capital: '1100.00', mora: false, version: 2 },
}

const server = setupServer(
  http.post(`${BASE}/credits`, () => HttpResponse.json(CREDIT, { status: 201 })),
  http.get(`${BASE}/installments`, () => HttpResponse.json(INSTALLMENTS)),
  http.post(`${BASE}/payments/preview`, () => HttpResponse.json(PREVIEW)),
  http.post(`${BASE}/payments`, () => HttpResponse.json(PAYMENT_RESP, { status: 201 })),
  http.get(`${BASE}/credits/:id`, () => HttpResponse.json({ ...CREDIT, mora: false, version: 2 })),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function getStore() {
  return makeStore({
    auth: { user: null, tokens: { accessToken: 'tok', refreshToken: null }, isLoading: false, error: null },
  })
}

describe('Gherkin: Create credit', () => {
  it('Given client exists, When createCredit is called, Then credit is returned with ACTIVE status', async () => {
    // GIVEN — store with auth token
    const store = getStore()

    // WHEN — dispatch createCredit
    const result = await store.dispatch(
      apiSlice.endpoints.createCredit.initiate({
        client_id: 'c1', initial_capital: 1200, periodicity: 'MONTHLY',
        annual_interest_rate: 24, start_date: '2024-01-01',
      })
    )

    // THEN
    expect(result.data?.status).toBe('ACTIVE')
    expect(result.data?.client_id).toBe('c1')
    expect(result.data?.mora).toBe(false)
  })
})

describe('Gherkin: View installments', () => {
  it('Given active credit, When getInstallments is called, Then overdue installment is visible', async () => {
    // GIVEN
    const store = getStore()

    // WHEN
    const result = await store.dispatch(
      apiSlice.endpoints.getInstallments.initiate({ credit_id: 'cr1' })
    )

    // THEN
    expect(result.data).toHaveLength(1)
    expect(result.data![0].is_overdue).toBe(true)
    expect(result.data![0].expected_value).toBe(124)
  })
})

describe('Gherkin: Preview payment', () => {
  it('Given overdue installment, When previewPayment is called, Then applied_to includes OVERDUE_INTEREST', async () => {
    // GIVEN
    const store = getStore()

    // WHEN
    const result = await store.dispatch(
      apiSlice.endpoints.previewPayment.initiate({ credit_id: 'cr1', amount: '124.00' })
    )

    // THEN
    expect(result.data?.applied_to[0].type).toBe('OVERDUE_INTEREST')
    expect(result.data?.updated_credit_snapshot.mora).toBe(false)
  })
})

describe('Gherkin: Register payment → mora cleared', () => {
  it('Given preview confirmed, When processPayment is called, Then mora=false in snapshot', async () => {
    // GIVEN
    const store = getStore()

    // WHEN
    const result = await store.dispatch(
      apiSlice.endpoints.processPayment.initiate({
        credit_id: 'cr1', amount: '124.00', operator_id: 'u1', notes: 'Cuota mensual',
      })
    )

    // THEN
    expect(result.data?.payment_id).toBe('p1')
    expect(result.data?.updated_credit_snapshot.mora).toBe(false)
    expect(result.data?.updated_credit_snapshot.pending_capital).toBe('1100.00')
  })
})

describe('Gherkin: 409 conflict on concurrent payment', () => {
  it('Given concurrent modification, When processPayment returns 409, Then error is surfaced', async () => {
    // GIVEN — server returns conflict
    server.use(
      http.post(`${BASE}/payments`, () =>
        HttpResponse.json({ detail: 'Concurrent modification detected' }, { status: 409 })
      )
    )
    const store = getStore()

    // WHEN
    const result = await store.dispatch(
      apiSlice.endpoints.processPayment.initiate({
        credit_id: 'cr1', amount: '124.00', operator_id: 'u1',
      })
    )

    // THEN
    expect(result.error).toBeDefined()
    expect((result.error as { status: number }).status).toBe(409)
  })
})
