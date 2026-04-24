import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Provider } from 'react-redux'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import { CreditFormPage } from '../pages/CreditFormPage'
import { apiSlice } from '../store/api/apiSlice'
import authReducer from '../store/slices/authSlice'
import uiReducer from '../store/slices/uiSlice'

vi.mock('../store/api/apiSlice', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../store/api/apiSlice')>()
  return {
    ...actual,
    useCreateCreditMutation: vi.fn(),
  }
})

import { useCreateCreditMutation } from '../store/api/apiSlice'

function renderPage() {
  const store = configureStore({
    reducer: { auth: authReducer, ui: uiReducer, [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (g) => g().concat(apiSlice.middleware),
  })
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/clients/client-1/credits/new']}>
        <Routes>
          <Route path="/clients/:clientId/credits/new" element={<CreditFormPage />} />
          <Route path="/clients/:clientId" element={<div>Client Detail</div>} />
        </Routes>
      </MemoryRouter>
    </Provider>
  )
}

describe('CreditFormPage', () => {
  const mockCreate = vi.fn().mockResolvedValue({ data: {} })

  beforeEach(() => {
    vi.mocked(useCreateCreditMutation).mockReturnValue([mockCreate, { isLoading: false }] as any)
  })

  it('renders all fields', () => {
    renderPage()
    expect(screen.getByTestId('input-capital')).toBeInTheDocument()
    expect(screen.getByTestId('input-rate')).toBeInTheDocument()
    expect(screen.getByTestId('input-periodicity')).toBeInTheDocument()
    expect(screen.getByTestId('input-start-date')).toBeInTheDocument()
  })

  it('shows validation error for zero capital', async () => {
    renderPage()
    fireEvent.change(screen.getByTestId('input-capital'), { target: { value: '0' } })
    fireEvent.click(screen.getByTestId('submit-credit'))
    await waitFor(() => {
      expect(screen.getByText('Capital must be greater than 0')).toBeInTheDocument()
    })
  })

  it('calls createCredit with client_id and form values', async () => {
    renderPage()
    fireEvent.change(screen.getByTestId('input-capital'), { target: { value: '5000' } })
    fireEvent.change(screen.getByTestId('input-rate'), { target: { value: '12' } })
    fireEvent.click(screen.getByTestId('submit-credit'))
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          client_id: 'client-1',
          initial_capital: 5000,
          annual_interest_rate: 12,
        })
      )
    })
  })

  it('shows creating state when loading', () => {
    vi.mocked(useCreateCreditMutation).mockReturnValue([mockCreate, { isLoading: true }] as any)
    renderPage()
    expect(screen.getByTestId('submit-credit')).toHaveTextContent('Creating...')
  })
})
