/**
 * Tests for CreditForm modal.
 * SPEC-001 §US-002 — credit creation form.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../../../test-utils'
import userEvent from '@testing-library/user-event'

// Mock the RTK Query mutation before importing the component
const mockUnwrap = vi.fn()
const mockCreateCredit = vi.fn(() => ({ unwrap: mockUnwrap }))

vi.mock('../../../store/api/apiSlice', () => ({
  useCreateCreditMutation: () => [mockCreateCredit, { isLoading: false, error: null }],
}))

import CreditForm from '../CreditForm'

const DEFAULT_PROPS = {
  clientId: 'client-uuid-1',
  isOpen: true,
  onClose: vi.fn(),
}

describe('CreditForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUnwrap.mockResolvedValue({ id: 'credit-1' })
  })

  it('renders null when isOpen is false', () => {
    const { container } = render(<CreditForm {...DEFAULT_PROPS} isOpen={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders form dialog when isOpen is true', () => {
    render(<CreditForm {...DEFAULT_PROPS} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('renders all required form fields', () => {
    render(<CreditForm {...DEFAULT_PROPS} />)
    expect(screen.getByLabelText(/capital inicial/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/periodicidad/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/tasa de interés/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/fecha de inicio/i)).toBeInTheDocument()
  })

  it('shows periodicity options', () => {
    render(<CreditForm {...DEFAULT_PROPS} />)
    const select = screen.getByLabelText(/periodicidad/i)
    expect(select).toContainHTML('MONTHLY')
    expect(select).toContainHTML('WEEKLY')
  })

  it('shows validation error when submitting with no capital', async () => {
    render(<CreditForm {...DEFAULT_PROPS} />)
    const submitButton = screen.getByRole('button', { name: /crear crédito/i })
    fireEvent.click(submitButton)
    await waitFor(() => {
      // Zod should reject missing/zero capital
      expect(screen.queryByText(/requerido|mayor/i)).toBeTruthy()
    })
  })

  it('calls createCredit mutation on valid submit', async () => {
    render(<CreditForm {...DEFAULT_PROPS} />)

    await userEvent.clear(screen.getByLabelText(/capital inicial/i))
    await userEvent.type(screen.getByLabelText(/capital inicial/i), '5000')
    await userEvent.clear(screen.getByLabelText(/tasa de interés/i))
    await userEvent.type(screen.getByLabelText(/tasa de interés/i), '12')

    fireEvent.click(screen.getByRole('button', { name: /crear crédito/i }))

    await waitFor(() => {
      expect(mockCreateCredit).toHaveBeenCalled()
    })
    const callArg = mockCreateCredit.mock.calls[0][0] as Record<string, unknown>
    expect(callArg.client_id).toBe('client-uuid-1')
    expect(callArg.initial_capital).toBe(5000)
  })

  it('calls onClose after successful mutation', async () => {
    const onClose = vi.fn()
    render(<CreditForm {...DEFAULT_PROPS} onClose={onClose} />)

    await userEvent.type(screen.getByLabelText(/capital inicial/i), '1000')
    await userEvent.type(screen.getByLabelText(/tasa de interés/i), '10')
    fireEvent.click(screen.getByRole('button', { name: /crear crédito/i }))

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('calls onClose when cancel button clicked', () => {
    const onClose = vi.fn()
    render(<CreditForm {...DEFAULT_PROPS} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }))
    expect(onClose).toHaveBeenCalled()
  })
})
