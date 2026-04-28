/**
 * clientApi RTK Query integration tests.
 * Uses a real in-memory Redux store; HTTP is intercepted via msw.
 */
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import { makeStore } from '../../../test-utils'
import { apiSlice } from '../apiSlice'
import type { Client } from '../../../types'

const BASE = 'http://localhost:8000/api/v1'

const CLIENT: Client = {
  id: 'c1',
  user_id: 'u1',
  first_name: 'Ana',
  last_name: 'Lopez',
  phone: '3001234567',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const server = setupServer(
  http.get(`${BASE}/clients`, () =>
    HttpResponse.json({ items: [CLIENT], total: 1, limit: 20, offset: 0 })
  ),
  http.post(`${BASE}/clients`, async ({ request }) => {
    const body = await request.json() as Partial<Client>
    return HttpResponse.json({ ...CLIENT, ...body, id: 'c2' }, { status: 201 })
  }),
  http.put(`${BASE}/clients/:id`, async ({ params, request }) => {
    const body = await request.json() as Partial<Client>
    return HttpResponse.json({ ...CLIENT, ...body, id: params.id as string })
  }),
  http.delete(`${BASE}/clients/:id`, () => new HttpResponse(null, { status: 204 })),
  http.get(`${BASE}/clients/:id`, ({ params }) =>
    params.id === 'notfound'
      ? HttpResponse.json({ detail: 'Not found' }, { status: 404 })
      : HttpResponse.json({ ...CLIENT, id: params.id as string })
  ),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function getStore() {
  return makeStore({
    auth: { user: null, tokens: { accessToken: 'tok', refreshToken: null }, isLoading: false, error: null },
  })
}

describe('clientApi — getClients', () => {
  it('returns list of clients', async () => {
    const store = getStore()
    const promise = store.dispatch(apiSlice.endpoints.getClients.initiate({}))
    const result = await promise
    expect(result.data?.items).toHaveLength(1)
    expect(result.data?.items[0].first_name).toBe('Ana')
  })

  it('handles search param', async () => {
    server.use(
      http.get(`${BASE}/clients`, ({ request }) => {
        const url = new URL(request.url)
        expect(url.searchParams.get('search')).toBe('Ana')
        return HttpResponse.json({ items: [CLIENT], total: 1, limit: 20, offset: 0 })
      })
    )
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.getClients.initiate({ search: 'Ana' }))
    expect(result.data?.items).toHaveLength(1)
  })
})

describe('clientApi — createClient', () => {
  it('sends correct body and returns created client', async () => {
    const store = getStore()
    const result = await store.dispatch(
      apiSlice.endpoints.createClient.initiate({ first_name: 'Luis', last_name: 'Gomez', phone: '3112223333' })
    )
    expect(result.data?.id).toBe('c2')
    expect(result.data?.first_name).toBe('Luis')
  })
})

describe('clientApi — updateClient', () => {
  it('sends PUT and returns updated client', async () => {
    const store = getStore()
    const result = await store.dispatch(
      apiSlice.endpoints.updateClient.initiate({ id: 'c1', data: { first_name: 'Updated' } })
    )
    expect(result.data?.first_name).toBe('Updated')
  })
})

describe('clientApi — deleteClient', () => {
  it('returns 204 with no data', async () => {
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.deleteClient.initiate('c1'))
    expect('error' in result ? result.error : undefined).toBeUndefined()
  })
})

describe('clientApi — error handling', () => {
  it('returns 404 error for unknown client', async () => {
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.getClient.initiate('notfound'))
    expect(result.error).toBeDefined()
    expect((result.error as { status: number }).status).toBe(404)
  })

  it('handles 400 validation error on create', async () => {
    server.use(
      http.post(`${BASE}/clients`, () =>
        HttpResponse.json({ detail: 'Validation error' }, { status: 400 })
      )
    )
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.createClient.initiate({}))
    expect(result.error).toBeDefined()
    expect((result.error as { status: number }).status).toBe(400)
  })

  it('handles 409 conflict on create', async () => {
    server.use(
      http.post(`${BASE}/clients`, () =>
        HttpResponse.json({ detail: 'Client already exists' }, { status: 409 })
      )
    )
    const store = getStore()
    const result = await store.dispatch(apiSlice.endpoints.createClient.initiate({}))
    expect(result.error).toBeDefined()
    expect((result.error as { status: number }).status).toBe(409)
  })
})
