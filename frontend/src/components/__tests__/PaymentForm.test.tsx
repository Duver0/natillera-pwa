/**
 * PaymentForm tests — Phase 4.
 *
 * Rules:
 * - RTK Query mutations mocked at the hook level
 * - No business logic re-implementation in tests
 * - Verify: preview called before submit, breakdown displayed, 409 handled
 *
 * Stack: Vitest + @testing-library/react
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { PaymentForm } from '../PaymentForm'

// Mock the RTK Query hooks
const mockPreviewPayment = vi.fn()
const mockProcessPayment = vi.fn()

vi.mock('../../store/api/apiSlice', () => ({
  usePreviewPaymentMutation: () => [
    mockPreviewPayment,
    { isLoading: false },
  ],
  useProcessPaymentMutation: () => [
    mockProcessPayment,
    { isLoading: false },
  ],
}))

const MOCK_PREVIEW = {
  credit_id: 'credit-1',
  total_amount: '200.00',
  applied_to: [
    {
      installment_id: 'inst-1234-abcd',
      type: 'OVERDUE_INTEREST' as const,
      amount: '100.00',
    },
    {
      installment_id: 'inst-1234-abcd',
      type: 'OVERDUE_PRINCIPAL' as const,
      amount: '100.00',
    },
  ],
  unallocated: '0.00',
  updated_credit_snapshot: {
    pending_capital: '900.00',
    mora: false,
    version: 2,
  },
}

const MOCK_PAYMENT_RESPONSE = {
  payment_id: 'payment-uuid-123',
  credit_id: 'credit-1',
  total_amount: '200.00',
  applied_to: MOCK_PREVIEW.applied_to,
  updated_credit_snapshot: MOCK_PREVIEW.updated_credit_snapshot,
}

function renderForm(overrides?: Partial<Parameters<typeof PaymentForm>[0]>) {
  const defaults = {
    creditId: 'credit-1',
    operatorId: 'user-1',
    onSuccess: vi.fn(),
    onError: vi.fn(),
  }
  return render(<PaymentForm {...defaults} {...overrides} />)
}

describe('PaymentForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the payment amount input', () => {
    renderForm()
    expect(screen.getByLabelText(/amount/i)).toBeInTheDocument()
  })

  it('renders Preview Breakdown button', () => {
    renderForm()
    expect(screen.getByRole('button', { name: /preview breakdown/i })).toBeInTheDocument()
  })

  it('calls previewPayment with correct amount on submit', async () => {
    mockPreviewPayment.mockResolvedValue({ data: MOCK_PREVIEW, unwrap: () => Promise.resolve(MOCK_PREVIEW) })

    renderForm()
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '200.00' } })
    fireEvent.click(screen.getByRole('button', { name: /preview breakdown/i }))

    await waitFor(() => {
      expect(mockPreviewPayment).toHaveBeenCalledWith({
        credit_id: 'credit-1',
        amount: '200.00',
      })
    })
  })

  it('displays breakdown table after preview', async () => {
    mockPreviewPayment.mockReturnValue({ unwrap: () => Promise.resolve(MOCK_PREVIEW) })

    renderForm()
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '200.00' } })
    fireEvent.click(screen.getByRole('button', { name: /preview breakdown/i }))

    await waitFor(() => {
      expect(screen.getByRole('table', { name: /allocation breakdown/i })).toBeInTheDocument()
      expect(screen.getByText('Overdue Interest')).toBeInTheDocument()
      expect(screen.getByText('Overdue Principal')).toBeInTheDocument()
    })
  })

  it('shows pending capital and mora in snapshot section', async () => {
    mockPreviewPayment.mockReturnValue({ unwrap: () => Promise.resolve(MOCK_PREVIEW) })

    renderForm()
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '200.00' } })
    fireEvent.click(screen.getByRole('button', { name: /preview breakdown/i }))

    await waitFor(() => {
      expect(screen.getByText(/900\.00/)).toBeInTheDocument()
      expect(screen.getByText(/clear/i)).toBeInTheDocument()
    })
  })

  it('calls processPayment with operator_id on confirm', async () => {
    mockPreviewPayment.mockReturnValue({ unwrap: () => Promise.resolve(MOCK_PREVIEW) })
    mockProcessPayment.mockReturnValue({ unwrap: () => Promise.resolve(MOCK_PAYMENT_RESPONSE) })

    renderForm()
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '200.00' } })
    fireEvent.click(screen.getByRole('button', { name: /preview breakdown/i }))

    await waitFor(() => screen.getByRole('button', { name: /confirm payment/i }))
    fireEvent.click(screen.getByRole('button', { name: /confirm payment/i }))

    await waitFor(() => {
      expect(mockProcessPayment).toHaveBeenCalledWith({
        credit_id: 'credit-1',
        amount: '200.00',
        operator_id: 'user-1',
      })
    })
  })

  it('calls onSuccess with payment_id after successful submission', async () => {
    const onSuccess = vi.fn()
    mockPreviewPayment.mockReturnValue({ unwrap: () => Promise.resolve(MOCK_PREVIEW) })
    mockProcessPayment.mockReturnValue({ unwrap: () => Promise.resolve(MOCK_PAYMENT_RESPONSE) })

    renderForm({ onSuccess })
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '200.00' } })
    fireEvent.click(screen.getByRole('button', { name: /preview breakdown/i }))

    await waitFor(() => screen.getByRole('button', { name: /confirm payment/i }))
    fireEvent.click(screen.getByRole('button', { name: /confirm payment/i }))

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith('payment-uuid-123')
    })
  })

  it('shows conflict error message on 409', async () => {
    const onError = vi.fn()
    mockPreviewPayment.mockReturnValue({ unwrap: () => Promise.resolve(MOCK_PREVIEW) })
    mockProcessPayment.mockReturnValue({
      unwrap: () => Promise.reject({ status: 409, data: { detail: 'conflict' } }),
    })

    renderForm({ onError })
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '200.00' } })
    fireEvent.click(screen.getByRole('button', { name: /preview breakdown/i }))

    await waitFor(() => screen.getByRole('button', { name: /confirm payment/i }))
    fireEvent.click(screen.getByRole('button', { name: /confirm payment/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/conflict/i)
    })
  })

  it('shows error if amount is zero or empty', async () => {
    renderForm()
    fireEvent.click(screen.getByRole('button', { name: /preview breakdown/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
    expect(mockPreviewPayment).not.toHaveBeenCalled()
  })

  it('cancel button returns to input step', async () => {
    mockPreviewPayment.mockReturnValue({ unwrap: () => Promise.resolve(MOCK_PREVIEW) })

    renderForm()
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '200.00' } })
    fireEvent.click(screen.getByRole('button', { name: /preview breakdown/i }))

    await waitFor(() => screen.getByRole('button', { name: /cancel/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

    expect(screen.getByLabelText(/amount/i)).toBeInTheDocument()
  })

  it('does not re-implement allocation logic (no allocation computation in component)', () => {
    // This test verifies the component module contains no allocation keywords
    // Frontend must be presentation-only per spec
    const componentSource = PaymentForm.toString()
    const forbiddenPatterns = [
      'ROUND_HALF',
      'interest_portion',
      'principal_portion',
      'overdue_debt',
      'pending_capital *=',
      'computeBreakdown',
      'allocate',
    ]
    for (const pattern of forbiddenPatterns) {
      expect(componentSource).not.toContain(pattern)
    }
  })
})
