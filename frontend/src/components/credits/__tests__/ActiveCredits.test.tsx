/**
 * Tests for ActiveCredits component.
 * SPEC-001 §US-002, §US-004, §US-006.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '../../../test-utils'
import type { Credit, Installment } from '../../../types'

// Mock module before importing component
vi.mock('../../../store/api/apiSlice', () => ({
  useGetCreditsQuery: vi.fn(),
  useCreateCreditMutation: () => [vi.fn(() => ({ unwrap: vi.fn().mockResolvedValue({}) })), { isLoading: false }],
}))

import { useGetCreditsQuery } from '../../../store/api/apiSlice'
import ActiveCredits from '../ActiveCredits'

function makeCredit(overrides: Partial<Credit> = {}): Credit {
  const nextInst: Installment = {
    id: 'inst-1',
    user_id: 'user-1',
    credit_id: 'credit-1',
    period_number: 1,
    expected_date: '2026-07-01',
    expected_value: 950000,
    principal_portion: 833333,
    interest_portion: 100000,
    paid_value: 0,
    is_overdue: false,
    status: 'UPCOMING',
    created_at: '2026-01-01T00:00:00',
  }
  return {
    id: 'credit-1',
    user_id: 'user-1',
    client_id: 'client-1',
    initial_capital: 10000000,
    pending_capital: 10000000,
    version: 1,
    periodicity: 'MONTHLY',
    annual_interest_rate: 12,
    status: 'ACTIVE',
    start_date: '2026-01-01',
    mora: false,
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
    next_installment: nextInst,
    upcoming_installments: [nextInst],
    ...overrides,
  }
}

describe('ActiveCredits', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state while fetching credits', () => {
    vi.mocked(useGetCreditsQuery).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useGetCreditsQuery>)

    render(<ActiveCredits clientId="client-1" />)
    expect(screen.getByText(/cargando créditos/i)).toBeInTheDocument()
  })

  it('shows error state on fetch failure', () => {
    vi.mocked(useGetCreditsQuery).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    } as ReturnType<typeof useGetCreditsQuery>)

    render(<ActiveCredits clientId="client-1" />)
    expect(screen.getByText(/error al cargar/i)).toBeInTheDocument()
  })

  it('shows empty state when no active credits', () => {
    vi.mocked(useGetCreditsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
    } as ReturnType<typeof useGetCreditsQuery>)

    render(<ActiveCredits clientId="client-1" />)
    expect(screen.getByText(/no hay créditos activos/i)).toBeInTheDocument()
  })

  it('renders credit card with pending_capital', () => {
    const credit = makeCredit({ pending_capital: 10000000 })
    vi.mocked(useGetCreditsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [credit],
    } as ReturnType<typeof useGetCreditsQuery>)

    render(<ActiveCredits clientId="client-1" />)
    // Should show "Capital pendiente" section
    expect(screen.getByText(/capital pendiente/i)).toBeInTheDocument()
  })

  it('shows MORA badge when credit.mora is true', () => {
    const credit = makeCredit({ mora: true, mora_since: '2026-03-01' })
    vi.mocked(useGetCreditsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [credit],
    } as ReturnType<typeof useGetCreditsQuery>)

    render(<ActiveCredits clientId="client-1" />)
    expect(screen.getByText('MORA')).toBeInTheDocument()
  })

  it('does not show MORA badge when credit.mora is false', () => {
    const credit = makeCredit({ mora: false })
    vi.mocked(useGetCreditsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [credit],
    } as ReturnType<typeof useGetCreditsQuery>)

    render(<ActiveCredits clientId="client-1" />)
    expect(screen.queryByText('MORA')).not.toBeInTheDocument()
  })

  it('opens CreditForm modal when "Nuevo crédito" button clicked', () => {
    vi.mocked(useGetCreditsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
    } as ReturnType<typeof useGetCreditsQuery>)

    render(<ActiveCredits clientId="client-1" />)
    fireEvent.click(screen.getByRole('button', { name: /nuevo crédito/i }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('expands to show upcoming installments when expand button clicked', () => {
    const credit = makeCredit()
    vi.mocked(useGetCreditsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [credit],
    } as ReturnType<typeof useGetCreditsQuery>)

    render(<ActiveCredits clientId="client-1" />)
    const expandBtn = screen.getByRole('button', { name: /ver próximas/i })
    fireEvent.click(expandBtn)
    // The installment period_number should now be visible in the expanded section
    expect(screen.getByRole('button', { name: /ocultar cuotas/i })).toBeInTheDocument()
  })
})
