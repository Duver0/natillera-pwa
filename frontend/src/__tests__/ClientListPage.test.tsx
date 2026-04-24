import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import { ClientListPage } from '../pages/ClientListPage'
import { apiSlice } from '../store/api/apiSlice'
import authReducer from '../store/slices/authSlice'
import uiReducer from '../store/slices/uiSlice'

// Mock RTK Query hooks
vi.mock('../store/api/apiSlice', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../store/api/apiSlice')>()
  return {
    ...actual,
    useGetClientsQuery: vi.fn(),
  }
})

import { useGetClientsQuery } from '../store/api/apiSlice'

const MOCK_CLIENTS = [
  { id: 'c1', first_name: 'Ana', last_name: 'Gomez', phone: '3001', mora_count: 0, total_debt: 0 },
  { id: 'c2', first_name: 'Juan', last_name: 'Perez', phone: '3002', mora_count: 1, total_debt: 500 },
]

function renderPage() {
  const store = configureStore({
    reducer: { auth: authReducer, ui: uiReducer, [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (g) => g().concat(apiSlice.middleware),
  })
  return render(
    <Provider store={store}>
      <MemoryRouter>
        <ClientListPage />
      </MemoryRouter>
    </Provider>
  )
}

describe('ClientListPage', () => {
  beforeEach(() => {
    vi.mocked(useGetClientsQuery).mockReturnValue({
      data: { items: MOCK_CLIENTS, total: MOCK_CLIENTS.length, limit: 20, offset: 0 },
      isLoading: false,
      isFetching: false,
    } as any)
  })

  it('renders client list', () => {
    // GIVEN clients returned from API
    renderPage()
    // THEN list is visible
    expect(screen.getByTestId('client-list')).toBeInTheDocument()
    expect(screen.getByText('Ana Gomez')).toBeInTheDocument()
    expect(screen.getByText('Juan Perez')).toBeInTheDocument()
  })

  it('shows mora badge for clients in mora', () => {
    renderPage()
    expect(screen.getByText('Mora')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    vi.mocked(useGetClientsQuery).mockReturnValue({
      data: { items: [], total: 0, limit: 20, offset: 0 },
      isLoading: true,
      isFetching: false,
    } as any)
    renderPage()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('shows empty state when no clients', () => {
    vi.mocked(useGetClientsQuery).mockReturnValue({
      data: { items: [], total: 0, limit: 20, offset: 0 },
      isLoading: false,
      isFetching: false,
    } as any)
    renderPage()
    expect(screen.getByText('No clients found.')).toBeInTheDocument()
  })

  it('search input updates query', () => {
    const mockQuery = vi.mocked(useGetClientsQuery)
    renderPage()
    const input = screen.getByTestId('client-search')
    fireEvent.change(input, { target: { value: 'Ana' } })
    // THEN search arg passed to hook
    expect(mockQuery).toHaveBeenCalledWith(
      expect.objectContaining({ search: 'Ana' }),
      expect.anything()
    )
  })

  it('pagination shows when more than 20 clients', () => {
    const manyClients = Array.from({ length: 25 }, (_, i) => ({
      id: `c${i}`,
      first_name: `Name${i}`,
      last_name: 'Test',
      phone: '300',
      mora_count: 0,
      total_debt: 0,
    }))
    vi.mocked(useGetClientsQuery).mockReturnValue({
      data: { items: manyClients.slice(0, 20), total: 25, limit: 20, offset: 0 },
      isLoading: false,
      isFetching: false,
    } as any)
    renderPage()
    expect(screen.getByText('1 / 2')).toBeInTheDocument()
  })
})
