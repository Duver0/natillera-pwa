/**
 * Unit tests for LoginPage component.
 * SPEC-002 §3.2 Phase 1.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import authReducer from '../store/slices/authSlice'
import uiReducer from '../store/slices/uiSlice'
import { apiSlice } from '../store/api/apiSlice'
import { LoginPage } from '../pages/LoginPage'

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    login: vi.fn(),
    loginLoading: false,
    user: null,
    tokens: { accessToken: null, refreshToken: null },
    isAuthenticated: false,
    logout: vi.fn(),
    register: vi.fn(),
    registerLoading: false,
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
        <LoginPage />
      </MemoryRouter>
    </Provider>
  )
}

describe('LoginPage', () => {
  it('renders email and password fields', () => {
    renderPage()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('renders sign in button', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows validation error for invalid email', async () => {
    renderPage()
    const emailInput = screen.getByLabelText(/email/i)
    const submitBtn = screen.getByRole('button', { name: /sign in/i })

    await userEvent.type(emailInput, 'not-an-email')
    await userEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument()
    })
  })

  it('renders link to register page', () => {
    renderPage()
    expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument()
  })
})
