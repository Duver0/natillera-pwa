/**
 * Tests for InstallmentView component.
 * SPEC-001 §US-004 — installment list with filters.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '../../../test-utils'
import type { Installment } from '../../../types'

const makeInstallment = (overrides: Partial<Installment> = {}): Installment => ({
  id: Math.random().toString(36).slice(2),
  user_id: 'user-1',
  credit_id: 'credit-1',
  period_number: 1,
  expected_date: '2026-06-01',
  expected_value: 950000,
  principal_portion: 833333,
  interest_portion: 100000,
  paid_value: 0,
  is_overdue: false,
  status: 'UPCOMING',
  created_at: '2026-01-01T00:00:00',
  ...overrides,
})

const UPCOMING_INST = makeInstallment({ id: 'up1', period_number: 1, status: 'UPCOMING', is_overdue: false })
const PAID_INST = makeInstallment({ id: 'paid1', period_number: 2, status: 'PAID', is_overdue: false, paid_value: 950000 })
const OVERDUE_INST = makeInstallment({
  id: 'ov1',
  period_number: 3,
  status: 'UPCOMING',
  is_overdue: true,
  expected_date: '2020-01-01',
})

vi.mock('../../../store/api/apiSlice', () => ({
  useGetInstallmentsQuery: vi.fn(),
}))

import { useGetInstallmentsQuery } from '../../../store/api/apiSlice'
import InstallmentView from '../InstallmentView'

describe('InstallmentView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state while fetching', () => {
    vi.mocked(useGetInstallmentsQuery).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useGetInstallmentsQuery>)

    render(<InstallmentView creditId="credit-1" />)
    expect(screen.getByText(/cargando cuotas/i)).toBeInTheDocument()
  })

  it('shows error state on fetch failure', () => {
    vi.mocked(useGetInstallmentsQuery).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    } as ReturnType<typeof useGetInstallmentsQuery>)

    render(<InstallmentView creditId="credit-1" />)
    expect(screen.getByText(/error al cargar/i)).toBeInTheDocument()
  })

  it('renders installment table with period numbers', () => {
    vi.mocked(useGetInstallmentsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [UPCOMING_INST, PAID_INST],
    } as ReturnType<typeof useGetInstallmentsQuery>)

    render(<InstallmentView creditId="credit-1" />)
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows all filter tabs', () => {
    vi.mocked(useGetInstallmentsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
    } as ReturnType<typeof useGetInstallmentsQuery>)

    render(<InstallmentView creditId="credit-1" />)
    expect(screen.getByRole('button', { name: /todas/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pendientes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pagadas/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /vencidas/i })).toBeInTheDocument()
  })

  it('filters to paid installments when Pagadas tab clicked', () => {
    vi.mocked(useGetInstallmentsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [UPCOMING_INST, PAID_INST, OVERDUE_INST],
    } as ReturnType<typeof useGetInstallmentsQuery>)

    render(<InstallmentView creditId="credit-1" />)
    fireEvent.click(screen.getByRole('button', { name: /pagadas/i }))
    // Only period 2 (PAID) should be visible
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.queryByText('3')).not.toBeInTheDocument()
  })

  it('filters to overdue installments when Vencidas tab clicked', () => {
    vi.mocked(useGetInstallmentsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [UPCOMING_INST, PAID_INST, OVERDUE_INST],
    } as ReturnType<typeof useGetInstallmentsQuery>)

    render(<InstallmentView creditId="credit-1" />)
    fireEvent.click(screen.getByRole('button', { name: /vencidas/i }))
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.queryByText('1')).not.toBeInTheDocument()
    expect(screen.queryByText('2')).not.toBeInTheDocument()
  })

  it('shows overdue badge for overdue installments in All tab', () => {
    vi.mocked(useGetInstallmentsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [OVERDUE_INST],
    } as ReturnType<typeof useGetInstallmentsQuery>)

    render(<InstallmentView creditId="credit-1" />)
    expect(screen.getAllByText(/vencida/i)).toHaveLength(2)
  })

  it('shows empty state when no installments match filter', () => {
    vi.mocked(useGetInstallmentsQuery).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [UPCOMING_INST],
    } as ReturnType<typeof useGetInstallmentsQuery>)

    render(<InstallmentView creditId="credit-1" />)
    fireEvent.click(screen.getByRole('button', { name: /pagadas/i }))
    expect(screen.getByText(/no hay cuotas para mostrar/i)).toBeInTheDocument()
  })
})
