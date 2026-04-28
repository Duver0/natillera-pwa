/**
 * ClientDetailPage — page integration tests (renders tabs, owner info).
 */
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders, authenticatedState } from '../../test-utils'
import { ClientDetailPage } from '../ClientDetailPage'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useParams: () => ({ clientId: 'c1' }) }
})

vi.mock('../../store/api/apiSlice', () => ({
  useGetClientQuery: () => ({
    data: {
      id: 'c1',
      user_id: 'u1',
      first_name: 'Carlos',
      last_name: 'Gomez',
      phone: '3119998888',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      mora_count: 0,
    },
    isLoading: false,
  }),
  useGetCreditsQuery: () => ({ data: [] }),
  useGetCreditQuery: () => ({ data: undefined }),
  useGetSavingsQuery: () => ({ data: [] }),
  useGetHistoryQuery: () => ({ data: [] }),
  useAddContributionMutation: () => [vi.fn(), {}],
  useLiquidateSavingsMutation: () => [vi.fn(), { isLoading: false }],
}))

vi.mock('../../components/PaymentModal', () => ({
  PaymentModal: () => null,
}))

function render() {
  return renderWithProviders(<ClientDetailPage />, {
    preloadedState: authenticatedState,
    initialEntries: ['/clients/c1'],
  })
}

describe('ClientDetailPage page integration', () => {
  it('renders client full name', () => {
    render()
    expect(screen.getByText('Carlos Gomez')).toBeInTheDocument()
  })

  it('renders tabs: Credits, Savings, History', () => {
    render()
    expect(screen.getByText('Credits')).toBeInTheDocument()
    expect(screen.getByText('Savings')).toBeInTheDocument()
    expect(screen.getByText('History')).toBeInTheDocument()
  })

  it('switches tabs on click', () => {
    render()
    fireEvent.click(screen.getByText('Savings'))
    expect(screen.getByText('Liquidate')).toBeInTheDocument()
  })

  it('shows Back button', () => {
    render()
    expect(screen.getByText('Back')).toBeInTheDocument()
  })
})
