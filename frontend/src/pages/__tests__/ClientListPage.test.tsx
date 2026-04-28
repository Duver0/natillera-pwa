/**
 * ClientListPage — page integration tests (renders with providers).
 */
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders, authenticatedState } from '../../test-utils'
import { ClientListPage } from '../ClientListPage'

vi.mock('../../store/api/clientApi', () => ({
  useGetClientsQuery: () => ({
    data: {
      items: [
        {
          id: 'c1',
          user_id: 'u1',
          first_name: 'Ana',
          last_name: 'Lopez',
          phone: '3001234567',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          mora_count: 0,
          total_debt: 0,
        },
      ],
      total: 1,
    },
    isLoading: false,
    isFetching: false,
  }),
  useCreateClientMutation: () => [vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({ id: 'c2' }) }), { isLoading: false }],
}))

function render() {
  return renderWithProviders(<ClientListPage />, {
    preloadedState: authenticatedState,
    initialEntries: ['/clients'],
  })
}

describe('ClientListPage page integration', () => {
  it('renders client list', () => {
    render()
    expect(screen.getByTestId('client-list')).toBeInTheDocument()
    expect(screen.getByText('Ana Lopez')).toBeInTheDocument()
  })

  it('renders Add Client button', () => {
    render()
    expect(screen.getByTestId('add-client-btn')).toBeInTheDocument()
  })

  it('opens New Client modal when Add Client is clicked', () => {
    render()
    fireEvent.click(screen.getByTestId('add-client-btn'))
    expect(screen.getByText('New Client')).toBeInTheDocument()
    expect(screen.getByTestId('client-form')).toBeInTheDocument()
  })

  it('renders search input', () => {
    render()
    expect(screen.getByTestId('client-search')).toBeInTheDocument()
  })
})
