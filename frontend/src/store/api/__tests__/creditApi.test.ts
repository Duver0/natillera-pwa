/**
 * creditApi RTK Query integration tests.
 */
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import { makeStore } from '../../../test-utils'
import { apiSlice } from '../apiSlice'
import type { Credit, Installment } from '../../../types'

const BASE = 'http://localhost:8000/api/v1'

const CREDIT: Credit = {
  id: 'cr1',
  user_id: 'u1',
  client_id: 'c1',
  initial_capital: 1000,
  pending_capital: 800,
  version: 1,
  periodicity: 'MONTHLY',
  annual_interest_rate: 24,
  status: 'ACTIVE',
  start_date: '2024-01-01',
  mora: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const INSTALLMENT: Installment = {
  id: 'i1',
  user_id: 'u1',
  credit_id: 'cr1',
  period_number: 1,
  expected_date: '2024-02-01',
  expected_value: 100,
  principal_portion: 80,
  interest_portion: 20,
  paid_value: 0,
  is_overdue: false,
  status: 'UPCOMING',
  created_at: '2024-01-01T00:00:00Z',
}

const server = setupServer(
  http.get(`${BASE}/credits`, () => HttpResponse.json([CREDIT])),
  http.post(`${BASE}/credits`, async ({ request }) => {
    const body = await request.json() as Partial<Credit>
    return HttpResponse.json({ ...CREDIT, ...body, id: 'cr2' }, { status: 201 })
  }),
  http.get(`${BASE}/installments`, () => HttpResponse.json([INSTALLMENT]))
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function getStore() {
  return makeStore({
    auth: { user: null, tokens: { accessToken: 'tok', refreshToken: null }, isLoading: false, error: null },
  })
}

describe('creditApi — getCredits', () => {
  it('returns credits list', async () => {
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.getCredits.initiate({ client_id: 'c1' }))
    expect(result.data).toHaveLength(1)
    expect(result.data![0].id).toBe('cr1')
  })

  it('filters by status param', async () => {
    server.use(
      http.get(`${BASE}/credits`, ({ request }) => {
        const url = new URL(request.url)
        expect(url.searchParams.get('status')).toBe('ACTIVE')
        return HttpResponse.json([CREDIT])
      })
    )
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.getCredits.initiate({ status: 'ACTIVE' }))
    expect(result.data).toHaveLength(1)
  })
})

describe('creditApi — createCredit', () => {
  it('sends POST and returns new credit', async () => {
    const store = getStore()
    const payload: Partial<Credit> = { client_id: 'c1', initial_capital: 2000, periodicity: 'WEEKLY', annual_interest_rate: 18, start_date: '2024-03-01', pending_capital: 2000, version: 1, user_id: 'u1', mora: false, status: 'ACTIVE', created_at: '', updated_at: '' }
    const result = await store.dispatch(apiSlice.endpoints.createCredit.initiate(payload))
    expect(result.data?.id).toBe('cr2')
    expect(result.data?.initial_capital).toBe(2000)
  })
})

describe('creditApi — getInstallments', () => {
  it('returns installments for a credit', async () => {
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.getInstallments.initiate({ credit_id: 'cr1' }))
    expect(result.data).toHaveLength(1)
    expect(result.data![0].period_number).toBe(1)
  })

  it('filters installments by status', async () => {
    server.use(
      http.get(`${BASE}/installments`, ({ request }) => {
        const url = new URL(request.url)
        expect(url.searchParams.get('status')).toBe('UPCOMING')
        return HttpResponse.json([INSTALLMENT])
      })
    )
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.getInstallments.initiate({ credit_id: 'cr1', status: 'UPCOMING' }))
    expect(result.data).toHaveLength(1)
  })
})
