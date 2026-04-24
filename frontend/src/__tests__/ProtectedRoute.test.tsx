/**
 * Unit tests for ProtectedRoute.
 * SPEC-002 §3.2 Phase 3.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import authReducer, { setUser, setTokens } from '../store/slices/authSlice'
import uiReducer from '../store/slices/uiSlice'
import { apiSlice } from '../store/api/apiSlice'
import { ProtectedRoute } from '../components/ProtectedRoute'

function renderProtected(authenticated: boolean) {
  const store = configureStore({
    reducer: { auth: authReducer, ui: uiReducer, [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (d) => d().concat(apiSlice.middleware),
  })

  if (authenticated) {
    store.dispatch(setUser({ id: 'u1', email: 'a@b.com' }))
    store.dispatch(setTokens({ accessToken: 'token-123', refreshToken: 'refresh-abc' }))
  }

  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Dashboard Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </Provider>
  )
}

describe('ProtectedRoute', () => {
  it('renders children when authenticated', () => {
    renderProtected(true)
    expect(screen.getByText('Dashboard Content')).toBeInTheDocument()
  })

  it('redirects to login when unauthenticated', () => {
    renderProtected(false)
    expect(screen.queryByText('Dashboard Content')).not.toBeInTheDocument()
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })
})
