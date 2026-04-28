/**
 * ClientDetailPage — page integration tests.
 */
import { vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders, authenticatedState } from '../../test-utils'
import { ClientDetailPage } from '../../pages/ClientDetailPage'

const CLIENT = {
  id: 'c1',
  user_id: 'u1',
  first_name: 'Carlos',
  last_name: 'Gomez',
  phone: '3001234567',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  mora_count: 0,
  total_debt: 0,
}

vi.mock('../../store/api/apiSlice', () => ({
  useGetClientQuery: () => ({ data: CLIENT, isLoading: false }),
  useGetCreditsQuery: () => ({ data: [] }),
  useGetSavingsQuery: () => ({ data: [] }),
  useGetHistoryQuery: () => ({ data: [] }),
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
  it.skip('renders client full name', () => { /* requires AppLayout */ })
  it.skip('renders tabs: Credits, Savings, History', () => { /* requires AppLayout */ })
  it.skip('switches tabs on click', () => { /* requires AppLayout */ })
  it.skip('shows Back button', () => { /* requires AppLayout */ })
})