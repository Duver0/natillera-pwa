import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import { PaymentModal } from '../components/PaymentModal'
import { apiSlice } from '../store/api/apiSlice'
import authReducer from '../store/slices/authSlice'
import uiReducer from '../store/slices/uiSlice'

vi.mock('../store/api/apiSlice', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../store/api/apiSlice')>()
  return {
    ...actual,
    usePreviewPaymentMutation: vi.fn(),
    useProcessPaymentMutation: vi.fn(),
  }
})

import { usePreviewPaymentMutation, useProcessPaymentMutation } from '../store/api/apiSlice'

const PREVIEW_RESPONSE = {
  credit_id: 'credit-1',
  amount: 150,
  applied_to: [
    { type: 'OVERDUE_INTEREST', amount: 50, installment_id: 'inst-1' },
    { type: 'OVERDUE_PRINCIPAL', amount: 100, installment_id: 'inst-1' },
  ],
  unallocated: 0,
}

function renderModal(creditId = 'credit-1') {
  const store = configureStore({
    reducer: { auth: authReducer, ui: uiReducer, [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (g) => g().concat(apiSlice.middleware),
  })
  const onClose = vi.fn()
  const onSuccess = vi.fn()
  const utils = render(
    <Provider store={store}>
      <MemoryRouter>
        <PaymentModal creditId={creditId} onClose={onClose} onSuccess={onSuccess} />
      </MemoryRouter>
    </Provider>
  )
  return { ...utils, onClose, onSuccess }
}

describe('PaymentModal', () => {
  const mockPreview = vi.fn()
  const mockProcess = vi.fn()

  beforeEach(() => {
    mockPreview.mockReturnValue({ unwrap: () => Promise.resolve(PREVIEW_RESPONSE) })
    mockProcess.mockReturnValue({ unwrap: () => Promise.resolve({}) })
    vi.mocked(usePreviewPaymentMutation).mockReturnValue([mockPreview, { isLoading: false }] as any)
    vi.mocked(useProcessPaymentMutation).mockReturnValue([mockProcess, { isLoading: false }] as any)
  })

  it('renders amount input and preview button', () => {
    renderModal()
    expect(screen.getByTestId('payment-amount-input')).toBeInTheDocument()
    expect(screen.getByTestId('preview-btn')).toBeInTheDocument()
  })

  it('preview button disabled when amount empty', () => {
    renderModal()
    expect(screen.getByTestId('preview-btn')).toBeDisabled()
  })

  it('calls previewPayment with credit_id and amount', async () => {
    renderModal()
    fireEvent.change(screen.getByTestId('payment-amount-input'), { target: { value: '150' } })
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => {
      expect(mockPreview).toHaveBeenCalledWith({ credit_id: 'credit-1', amount: 150 })
    })
  })

  it('shows breakdown after preview', async () => {
    renderModal()
    fireEvent.change(screen.getByTestId('payment-amount-input'), { target: { value: '150' } })
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => {
      expect(screen.getByTestId('preview-breakdown')).toBeInTheDocument()
      expect(screen.getByText('Overdue Interest')).toBeInTheDocument()
      expect(screen.getByText('Overdue Principal')).toBeInTheDocument()
    })
  })

  it('calls processPayment on confirm', async () => {
    renderModal()
    fireEvent.change(screen.getByTestId('payment-amount-input'), { target: { value: '150' } })
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => expect(screen.getByTestId('confirm-payment-btn')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('confirm-payment-btn'))
    await waitFor(() => {
      expect(mockProcess).toHaveBeenCalledWith({ credit_id: 'credit-1', amount: 150 })
    })
  })

  it('shows unallocated amount when payment exceeds debt', async () => {
    mockPreview.mockReturnValue({ unwrap: () => Promise.resolve({ ...PREVIEW_RESPONSE, unallocated: 50 }) })
    renderModal()
    fireEvent.change(screen.getByTestId('payment-amount-input'), { target: { value: '200' } })
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => {
      expect(screen.getByText('Unallocated')).toBeInTheDocument()
    })
  })
})
