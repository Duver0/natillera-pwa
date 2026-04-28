/**
 * paymentApi RTK Query integration tests.
 */
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import { makeStore } from '../../../test-utils'
import { apiSlice } from '../apiSlice'
import type { PaymentPreview, PaymentResponse } from '../../../types'

const BASE = 'http://localhost:8000/api/v1'

const PREVIEW: PaymentPreview = {
  credit_id: 'cr1',
  total_amount: '150.00',
  applied_to: [],
  unallocated: '0.00',
  updated_credit_snapshot: { pending_capital: '650.00', mora: false, version: 2 },
}

const PAYMENT_RESPONSE: PaymentResponse = {
  payment_id: 'p1',
  credit_id: 'cr1',
  total_amount: '150.00',
  applied_to: [],
  updated_credit_snapshot: { pending_capital: '650.00', mora: false, version: 2 },
}

const server = setupServer(
  http.post(`${BASE}/payments/preview`, () => HttpResponse.json(PREVIEW)),
  http.post(`${BASE}/payments`, () => HttpResponse.json(PAYMENT_RESPONSE, { status: 201 }))
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function getStore() {
  return makeStore({
    auth: { user: null, tokens: { accessToken: 'tok', refreshToken: null }, isLoading: false, error: null },
  })
}

describe('paymentApi — previewPayment', () => {
  it('returns preview with applied_to breakdown', async () => {
    const store = getStore()
    const result = await store.dispatch(
      apiSlice.endpoints.previewPayment.initiate({ credit_id: 'cr1', amount: '150.00' })
    )
    expect(result.data?.credit_id).toBe('cr1')
    expect(result.data?.total_amount).toBe('150.00')
    expect(result.data?.unallocated).toBe('0.00')
  })
})

describe('paymentApi — processPayment', () => {
  it('sends POST and returns payment response', async () => {
    const store = getStore()
    const result = await store.dispatch(
      apiSlice.endpoints.processPayment.initiate({
        credit_id: 'cr1',
        amount: '150.00',
        operator_id: 'u1',
        notes: 'Pago mensual',
      })
    )
    expect(result.data?.payment_id).toBe('p1')
    expect(result.data?.updated_credit_snapshot.mora).toBe(false)
  })

  it('handles 409 conflict (concurrent payment)', async () => {
    server.use(
      http.post(`${BASE}/payments`, () =>
        HttpResponse.json({ detail: 'Concurrent modification detected' }, { status: 409 })
      )
    )
    const store = getStore()
    const result = await store.dispatch(
      apiSlice.endpoints.processPayment.initiate({
        credit_id: 'cr1',
        amount: '100.00',
        operator_id: 'u1',
      })
    )
    expect(result.error).toBeDefined()
    expect((result.error as { status: number }).status).toBe(409)
  })

  it('handles network error on processPayment', async () => {
    server.use(
      http.post(`${BASE}/payments`, () => HttpResponse.error())
    )
    const store = getStore()
    const result = await store.dispatch(
      apiSlice.endpoints.processPayment.initiate({
        credit_id: 'cr1',
        amount: '100.00',
        operator_id: 'u1',
      })
    )
    expect(result.error).toBeDefined()
  })
})
