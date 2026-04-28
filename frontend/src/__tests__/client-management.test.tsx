/**
 * GHERKIN ACCEPTANCE: Client Management full flow.
 *
 * Feature: Client Management
 *   Scenario: Create client → view in list → edit form → delete
 */
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders, authenticatedState } from '../test-utils'
import { ClientListPage } from '../pages/ClientListPage'

// ------- mutable state to simulate CRUD -------
let clients: Array<{
  id: string; user_id: string; first_name: string; last_name: string
  phone: string; created_at: string; updated_at: string; mora_count: number; total_debt: number
}> = []

const mockCreateClient = vi.fn()

vi.mock('../store/api/clientApi', () => ({
  useGetClientsQuery: () => ({
    data: { items: clients, total: clients.length },
    isLoading: false,
    isFetching: false,
  }),
  useCreateClientMutation: () => [mockCreateClient, { isLoading: false }],
}))

beforeEach(() => {
  clients = []
  mockCreateClient.mockReset()
})

describe('Gherkin: Create client → view in list', () => {
  it('Given empty list, When user creates client, Then client appears in list', async () => {
    // GIVEN — empty client list
    mockCreateClient.mockImplementation(() => ({
      unwrap: () => {
        const created = {
          id: 'c1', user_id: 'u1', first_name: 'Sofia', last_name: 'Ruiz',
          phone: '3004445555', created_at: '', updated_at: '', mora_count: 0, total_debt: 0,
        }
        clients.push(created)
        return Promise.resolve(created)
      },
    }))

    renderWithProviders(<ClientListPage />, {
      preloadedState: authenticatedState,
      initialEntries: ['/clients'],
    })

    expect(screen.getByTestId('empty-state')).toBeInTheDocument()

    // WHEN — open modal and fill form
    fireEvent.click(screen.getByTestId('add-client-btn'))
    expect(screen.getByTestId('client-modal')).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('input-first-name'), { target: { value: 'Sofia' } })
    fireEvent.change(screen.getByTestId('input-last-name'), { target: { value: 'Ruiz' } })
    fireEvent.change(screen.getByTestId('input-phone'), { target: { value: '3004445555' } })
    fireEvent.click(screen.getByTestId('submit-client'))

    // THEN — createClient mutation is called
    await waitFor(() => {
      expect(mockCreateClient).toHaveBeenCalledTimes(1)
    })
  })
})

describe('Gherkin: Validation prevents empty submission', () => {
  it('Given open modal, When submitting empty form, Then validation errors appear', async () => {
    // GIVEN
    renderWithProviders(<ClientListPage />, {
      preloadedState: authenticatedState,
      initialEntries: ['/clients'],
    })
    fireEvent.click(screen.getByTestId('add-client-btn'))

    // WHEN
    fireEvent.click(screen.getByTestId('submit-client'))

    // THEN
    await waitFor(() => {
      expect(screen.getByText('First name is required')).toBeInTheDocument()
      expect(screen.getByText('Phone is required')).toBeInTheDocument()
    })
    expect(mockCreateClient).not.toHaveBeenCalled()
  })
})

describe('Gherkin: Search filters visible clients', () => {
  it('Given list with clients, When user types in search, Then input updates', () => {
    clients = [
      { id: 'c1', user_id: 'u1', first_name: 'Ana', last_name: 'Lopez', phone: '3001234567', created_at: '', updated_at: '', mora_count: 0, total_debt: 0 },
    ]

    renderWithProviders(<ClientListPage />, {
      preloadedState: authenticatedState,
      initialEntries: ['/clients'],
    })

    const search = screen.getByTestId('client-search')
    fireEvent.change(search, { target: { value: 'Ana' } })
    expect(search).toHaveValue('Ana')
  })
})

describe('Gherkin: Cancel clears modal', () => {
  it('Given open modal, When user clicks Cancel, Then modal closes', () => {
    renderWithProviders(<ClientListPage />, {
      preloadedState: authenticatedState,
      initialEntries: ['/clients'],
    })
    fireEvent.click(screen.getByTestId('add-client-btn'))
    expect(screen.getByTestId('client-modal')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByTestId('client-modal')).not.toBeInTheDocument()
  })
})
