/**
 * Tests for AppStartup session persistence.
 * SPEC-002 §3.2 Phase 3.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import React from 'react'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import authReducer, { setTokens } from '../store/slices/authSlice'
import uiReducer from '../store/slices/uiSlice'
import { apiSlice } from '../store/api/apiSlice'
import { AppStartup } from '../components/AppStartup'

const mockRefreshMutation = vi.fn()

vi.mock('../store/api/apiSlice', async () => {
  const actual = await vi.importActual<typeof import('../store/api/apiSlice')>('../store/api/apiSlice')
  return {
    ...actual,
    useRefreshMutation: () => [mockRefreshMutation, {}],
  }
})

function makeStore(preloaded?: object) {
  return configureStore({
    reducer: { auth: authReducer, ui: uiReducer, [apiSlice.reducerPath]: apiSlice.reducer },
    middleware: (d) => d().concat(apiSlice.middleware),
    preloadedState: preloaded,
  })
}

describe('AppStartup — session persistence', () => {
  beforeEach(() => {
    mockRefreshMutation.mockReset()
  })

  it('calls refresh when refresh token exists but no user', async () => {
    mockRefreshMutation.mockReturnValue({
      unwrap: () => Promise.resolve({
        access_token: 'new-access',
        refresh_token: 'new-refresh',
        user: { id: 'u1', email: 'a@b.com' },
      }),
    })

    const store = makeStore({
      auth: {
        user: null,
        tokens: { accessToken: null, refreshToken: 'stored-refresh' },
        isLoading: false,
        error: null,
      },
    })

    render(
      <Provider store={store}>
        <MemoryRouter>
          <AppStartup><div>content</div></AppStartup>
        </MemoryRouter>
      </Provider>
    )

    await waitFor(() => {
      expect(mockRefreshMutation).toHaveBeenCalledWith({ refresh_token: 'stored-refresh' })
    })

    await waitFor(() => {
      const state = store.getState()
      expect(state.auth.user?.id).toBe('u1')
      expect(state.auth.tokens.accessToken).toBe('new-access')
    })
  })

  it('clears auth when refresh fails', async () => {
    mockRefreshMutation.mockReturnValue({
      unwrap: () => Promise.reject(new Error('Token expired')),
    })

    const store = makeStore({
      auth: {
        user: null,
        tokens: { accessToken: null, refreshToken: 'expired-refresh' },
        isLoading: false,
        error: null,
      },
    })

    render(
      <Provider store={store}>
        <MemoryRouter>
          <AppStartup><div>content</div></AppStartup>
        </MemoryRouter>
      </Provider>
    )

    await waitFor(() => {
      const state = store.getState()
      expect(state.auth.tokens.refreshToken).toBeNull()
    })
  })

  it('skips refresh when no refresh token in store', () => {
    const store = makeStore()

    render(
      <Provider store={store}>
        <MemoryRouter>
          <AppStartup><div>content</div></AppStartup>
        </MemoryRouter>
      </Provider>
    )

    expect(mockRefreshMutation).not.toHaveBeenCalled()
  })

  it('skips refresh when user is already loaded', () => {
    const store = makeStore({
      auth: {
        user: { id: 'u1', email: 'a@b.com' },
        tokens: { accessToken: 'acc', refreshToken: 'ref' },
        isLoading: false,
        error: null,
      },
    })

    render(
      <Provider store={store}>
        <MemoryRouter>
          <AppStartup><div>content</div></AppStartup>
        </MemoryRouter>
      </Provider>
    )

    expect(mockRefreshMutation).not.toHaveBeenCalled()
  })
})
