import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Provider } from 'react-redux'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import { ClientFormPage } from '../pages/ClientFormPage'
import { apiSlice } from '../store/api/apiSlice'
import authReducer from '../store/slices/authSlice'
import uiReducer from '../store/slices/uiSlice'

vi.mock('../store/api/apiSlice', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../store/api/apiSlice')>()
  return {
    ...actual,
    useGetClientQuery: vi.fn(),
    useCreateClientMutation: vi.fn(),
    useUpdateClientMutation: vi.fn(),
  }
})

import {
  useGetClientQuery,
  useCreateClientMutation,
  useUpdateClientMutation,
} from '../store/api/apiSlice'

function renderCreate() {
  const store = configureStore({
    reducer: { auth: authReducer, ui: uiReducer, [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (g) => g().concat(apiSlice.middleware),
  })
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/clients/new']}>
        <Routes>
          <Route path="/clients/new" element={<ClientFormPage />} />
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </Provider>
  )
}

describe('ClientFormPage — create', () => {
  const mockCreate = vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({ id: 'new-id' }) })

  beforeEach(() => {
    vi.mocked(useGetClientQuery).mockReturnValue({ data: undefined } as any)
    vi.mocked(useCreateClientMutation).mockReturnValue([mockCreate, { isLoading: false }] as any)
    vi.mocked(useUpdateClientMutation).mockReturnValue([vi.fn(), { isLoading: false }] as any)
  })

  it('renders all required fields', () => {
    renderCreate()
    expect(screen.getByTestId('input-first-name')).toBeInTheDocument()
    expect(screen.getByTestId('input-last-name')).toBeInTheDocument()
    expect(screen.getByTestId('input-phone')).toBeInTheDocument()
  })

  it('shows validation errors when required fields empty', async () => {
    renderCreate()
    fireEvent.click(screen.getByTestId('submit-client'))
    await waitFor(() => {
      expect(screen.getByText('First name is required')).toBeInTheDocument()
    })
  })

  it('calls createClient on valid submit', async () => {
    renderCreate()
    fireEvent.change(screen.getByTestId('input-first-name'), { target: { value: 'Ana' } })
    fireEvent.change(screen.getByTestId('input-last-name'), { target: { value: 'Gomez' } })
    fireEvent.change(screen.getByTestId('input-phone'), { target: { value: '3001234567' } })
    fireEvent.click(screen.getByTestId('submit-client'))
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({ first_name: 'Ana', last_name: 'Gomez', phone: '3001234567' })
      )
    })
  })

  it('shows creating state on submit', () => {
    vi.mocked(useCreateClientMutation).mockReturnValue([mockCreate, { isLoading: true }] as any)
    renderCreate()
    expect(screen.getByTestId('submit-client')).toHaveTextContent('Saving...')
  })
})
