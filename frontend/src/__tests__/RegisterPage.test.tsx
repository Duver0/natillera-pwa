/**
 * Unit tests for RegisterPage component.
 * SPEC-002 §3.2 Phase 1 — password validation.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import authReducer from '../store/slices/authSlice'
import uiReducer from '../store/slices/uiSlice'
import { apiSlice } from '../store/api/apiSlice'
import { RegisterPage } from '../pages/RegisterPage'

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    register: vi.fn(),
    registerLoading: false,
    user: null,
    tokens: { accessToken: null, refreshToken: null },
    isAuthenticated: false,
    login: vi.fn(),
    loginLoading: false,
    logout: vi.fn(),
  }),
}))

function renderPage() {
  const store = configureStore({
    reducer: { auth: authReducer, ui: uiReducer, [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (d) => d().concat(apiSlice.middleware),
  })
  return render(
    <Provider store={store}>
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    </Provider>
  )
}

describe('RegisterPage', () => {
  it('renders registration fields', () => {
    renderPage()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
  })

  it('rejects password shorter than 8 characters', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'short')
    await userEvent.click(screen.getByRole('button', { name: /register/i }))

    await waitFor(() => {
      expect(screen.getByText(/at least 8/i)).toBeInTheDocument()
    })
  })

  it('rejects password without uppercase letter', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'alllower1')
    await userEvent.click(screen.getByRole('button', { name: /register/i }))

    await waitFor(() => {
      expect(screen.getByText(/uppercase/i)).toBeInTheDocument()
    })
  })

  it('rejects password without a number', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'NoNumbers')
    await userEvent.click(screen.getByRole('button', { name: /register/i }))

    await waitFor(() => {
      expect(screen.getByText(/number/i)).toBeInTheDocument()
    })
  })

  it('shows mismatch error when passwords differ', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'ValidPass1')
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'Different1')
    await userEvent.click(screen.getByRole('button', { name: /register/i }))

    await waitFor(() => {
      expect(screen.getByText(/do not match/i)).toBeInTheDocument()
    })
  })
})
