/**
 * Tests for ProtectedRoute — redirects unauthenticated users to /login.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import authReducer from '../../store/slices/authSlice'
import { ProtectedRoute } from '../ProtectedRoute'
import type { User, AuthTokens } from '../../types'

// ─── helpers ────────────────────────────────────────────────────────────────

const USER: User = { id: 'u1', email: 'user@test.com' }
const TOKENS: AuthTokens = { accessToken: 'acc', refreshToken: 'ref' }

function buildStore(auth: { user: User | null; tokens: AuthTokens }) {
  return configureStore({
    reducer: { auth: authReducer },
    preloadedState: {
      auth: { ...auth, isLoading: false, error: null },
    },
  })
}

function renderProtectedRoute(
  store: ReturnType<typeof buildStore>,
  initialPath = '/dashboard'
) {
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/login" element={<div data-testid="login-page">Login</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div data-testid="protected-content">Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </Provider>
  )
}

// ─── tests ───────────────────────────────────────────────────────────────────

describe('ProtectedRoute — authenticated user', () => {
  it('renders children when user and accessToken are present', () => {
    // GIVEN authenticated store
    const store = buildStore({ user: USER, tokens: TOKENS })

    // WHEN
    renderProtectedRoute(store)

    // THEN
    expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument()
  })
})

describe('ProtectedRoute — unauthenticated user', () => {
  it('redirects to /login when user is null', () => {
    // GIVEN no user
    const store = buildStore({ user: null, tokens: { accessToken: null, refreshToken: null } })

    // WHEN
    renderProtectedRoute(store)

    // THEN
    expect(screen.getByTestId('login-page')).toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })

  it('redirects to /login when user is set but accessToken is null', () => {
    // GIVEN user present but no token (partial state)
    const store = buildStore({ user: USER, tokens: { accessToken: null, refreshToken: 'ref' } })

    // WHEN
    renderProtectedRoute(store)

    // THEN — not authenticated without accessToken
    expect(screen.getByTestId('login-page')).toBeInTheDocument()
  })

  it('redirects to /login when accessToken is set but user is null', () => {
    // GIVEN token present but no user
    const store = buildStore({ user: null, tokens: TOKENS })

    // WHEN
    renderProtectedRoute(store)

    // THEN
    expect(screen.getByTestId('login-page')).toBeInTheDocument()
  })
})

describe('ProtectedRoute — does not render null content when redirecting', () => {
  it('renders nothing in the protected slot when not authenticated', () => {
    // GIVEN
    const store = buildStore({ user: null, tokens: { accessToken: null, refreshToken: null } })

    // WHEN
    renderProtectedRoute(store)

    // THEN — ProtectedRoute returns null, only login page visible
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })
})
