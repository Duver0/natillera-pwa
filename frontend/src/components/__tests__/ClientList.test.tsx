/**
 * ClientListPage — component-level tests via renderWithProviders.
 * RTK Query calls are intercepted via vi.mock on apiSlice.
 */
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders, authenticatedState } from '../../test-utils'
import { ClientListPage } from '../../pages/ClientListPage'
import type { Client } from '../../types'

const mockClient = (overrides: Partial<Client> = {}): Client => ({
  id: 'c1',
  user_id: 'u1',
  first_name: 'Ana',
  last_name: 'Lopez',
  phone: '3001234567',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  mora_count: 0,
  total_debt: 0,
  ...overrides,
})

// Mock RTK hooks
const mockUseGetClients = vi.fn()
const mockCreateClient = vi.fn()

vi.mock('../../store/api/clientApi', () => ({
  useGetClientsQuery: (...args: unknown[]) => mockUseGetClients(...args),
  useCreateClientMutation: () => [mockCreateClient, { isLoading: false }],
}))

beforeEach(() => {
  mockUseGetClients.mockReturnValue({ data: undefined, isLoading: false, isFetching: false })
  mockCreateClient.mockResolvedValue({ unwrap: () => Promise.resolve({ id: 'c2' }) })
})

function render(opts = {}) {
  return renderWithProviders(<ClientListPage />, {
    preloadedState: authenticatedState,
    initialEntries: ['/clients'],
    ...opts,
  })
}

describe('ClientListPage — empty state', () => {
  it('shows empty state when no clients', () => {
    mockUseGetClients.mockReturnValue({ data: { items: [], total: 0 }, isLoading: false, isFetching: false })
    render()
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
  })

  it('shows loading indicator', () => {
    mockUseGetClients.mockReturnValue({ data: undefined, isLoading: true, isFetching: false })
    render()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })
})

describe('ClientListPage — with clients', () => {
  beforeEach(() => {
    mockUseGetClients.mockReturnValue({
      data: { items: [mockClient(), mockClient({ id: 'c2', first_name: 'Luis', phone: '3112223333' })], total: 2 },
      isLoading: false,
      isFetching: false,
    })
  })

  it('renders client list', () => {
    render()
    expect(screen.getByTestId('client-list')).toBeInTheDocument()
    expect(screen.getByTestId('client-row-c1')).toBeInTheDocument()
    expect(screen.getByTestId('client-row-c2')).toBeInTheDocument()
  })

  it('shows mora badge when mora_count > 0', () => {
    mockUseGetClients.mockReturnValue({
      data: { items: [mockClient({ mora_count: 2 })], total: 1 },
      isLoading: false,
      isFetching: false,
    })
    render()
    expect(screen.getByText('Mora')).toBeInTheDocument()
  })

  it('shows total_debt when > 0', () => {
    mockUseGetClients.mockReturnValue({
      data: { items: [mockClient({ total_debt: 500 })], total: 1 },
      isLoading: false,
      isFetching: false,
    })
    render()
    expect(screen.getByText('$500.00')).toBeInTheDocument()
  })
})

describe('ClientListPage — search', () => {
  it('updates search input', () => {
    mockUseGetClients.mockReturnValue({ data: { items: [], total: 0 }, isLoading: false, isFetching: false })
    render()
    const search = screen.getByTestId('client-search')
    fireEvent.change(search, { target: { value: 'Ana' } })
    expect(search).toHaveValue('Ana')
  })
})

describe('ClientListPage — pagination', () => {
  it('shows pagination when totalPages > 1', () => {
    mockUseGetClients.mockReturnValue({
      data: { items: Array.from({ length: 20 }, (_, i) => mockClient({ id: `c${i}` })), total: 40 },
      isLoading: false,
      isFetching: false,
    })
    render()
    expect(screen.getByText('1 / 2')).toBeInTheDocument()
    expect(screen.getByText('Next')).toBeInTheDocument()
    expect(screen.getByText('Prev')).toBeInTheDocument()
  })

  it('Prev button is disabled on first page', () => {
    mockUseGetClients.mockReturnValue({
      data: { items: Array.from({ length: 20 }, (_, i) => mockClient({ id: `c${i}` })), total: 40 },
      isLoading: false,
      isFetching: false,
    })
    render()
    expect(screen.getByText('Prev')).toBeDisabled()
  })
})

describe('ClientListPage — modal', () => {
  beforeEach(() => {
    mockUseGetClients.mockReturnValue({ data: { items: [], total: 0 }, isLoading: false, isFetching: false })
  })

  it('opens modal on Add Client click', () => {
    render()
    fireEvent.click(screen.getByTestId('add-client-btn'))
    expect(screen.getByTestId('client-modal')).toBeInTheDocument()
  })

  it('closes modal on Cancel button', () => {
    render()
    fireEvent.click(screen.getByTestId('add-client-btn'))
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByTestId('client-modal')).not.toBeInTheDocument()
  })

  it('closes modal on backdrop click', () => {
    render()
    fireEvent.click(screen.getByTestId('add-client-btn'))
    const backdrop = screen.getByTestId('client-modal')
    fireEvent.click(backdrop)
    expect(screen.queryByTestId('client-modal')).not.toBeInTheDocument()
  })
})
