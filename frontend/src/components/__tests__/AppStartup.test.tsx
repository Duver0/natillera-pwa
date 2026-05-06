/**
 * Integration tests for AppStartup component — session rehidration logic.
 *
 * vitest.setup.ts already mocks apiSlice globally.
 * We override useRefreshMutation per test to control behavior.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import authReducer, { setUser, setTokens, clearAuth } from '../../store/slices/authSlice'
import { AppStartup } from '../AppStartup'
import type { User, AuthTokens } from '../../types'

// ─── helpers ────────────────────────────────────────────────────────────────

const TOKENS: AuthTokens = { accessToken: 'acc', refreshToken: 'ref-stored' }
const USER: User = { id: 'u1', email: 'user@test.com' }

function buildStore(preloadedAuth?: Partial<{ user: User | null; tokens: AuthTokens; isLoading: boolean; error: string | null }>) {
  return configureStore({
    reducer: { auth: authReducer },
    preloadedState: {
      auth: {
        user: null,
        tokens: { accessToken: null, refreshToken: null },
        isLoading: false,
        error: null,
        ...preloadedAuth,
      },
    },
  })
}

function renderAppStartup(store: ReturnType<typeof buildStore>) {
  return render(
    <Provider store={store}>
      <AppStartup>
        <div data-testid="children">app content</div>
      </AppStartup>
    </Provider>
  )
}

// ─── mock useRefreshMutation ─────────────────────────────────────────────────
// vitest.setup.ts already mocks the apiSlice module globally.
// We use vi.hoisted + vi.mock to inject useRefreshMutation into that same mock.

const { mockRefreshUnwrap, mockRefreshTrigger } = vi.hoisted(() => {
  const mockRefreshUnwrap = vi.fn()
  const mockRefreshTrigger = vi.fn(() => ({ unwrap: mockRefreshUnwrap }))
  return { mockRefreshUnwrap, mockRefreshTrigger }
})

vi.mock('../../store/api/apiSlice', () => ({
  __esModule: true,
  apiSlice: {
    reducerPath: 'api' as const,
    reducer: vi.fn(),
    middleware: vi.fn(),
  },
  useRefreshMutation: () => [mockRefreshTrigger, { isLoading: false }],
}))

// ─── tests ───────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
})

describe('AppStartup — always renders children', () => {
  it('renders children regardless of auth state', () => {
    // GIVEN store with no auth
    const store = buildStore()

    // WHEN
    renderAppStartup(store)

    // THEN
    expect(screen.getByTestId('children')).toBeInTheDocument()
  })
})

describe('AppStartup — no refresh when user already present', () => {
  it('does NOT call refresh if user is already set in state', async () => {
    // GIVEN store with existing user + refreshToken
    const store = buildStore({ user: USER, tokens: TOKENS })

    // WHEN
    renderAppStartup(store)
    await waitFor(() => expect(mockRefreshTrigger).not.toHaveBeenCalled())

    // THEN
    expect(mockRefreshTrigger).not.toHaveBeenCalled()
  })
})

describe('AppStartup — no refresh when no refreshToken', () => {
  it('does NOT call refresh if refreshToken is null', async () => {
    // GIVEN store with no tokens
    const store = buildStore({ tokens: { accessToken: null, refreshToken: null } })

    // WHEN
    renderAppStartup(store)
    await waitFor(() => expect(mockRefreshTrigger).not.toHaveBeenCalled())

    // THEN
    expect(mockRefreshTrigger).not.toHaveBeenCalled()
  })
})

describe('AppStartup — refresh on mount when refreshToken exists but no user', () => {
  it('calls refresh with stored refreshToken', async () => {
    // GIVEN store has refreshToken but no user
    mockRefreshUnwrap.mockResolvedValue({
      access_token: 'new_acc',
      refresh_token: 'new_ref',
      user: USER,
    })
    const store = buildStore({ tokens: TOKENS, user: null })

    // WHEN
    renderAppStartup(store)

    // THEN
    await waitFor(() => expect(mockRefreshTrigger).toHaveBeenCalledWith({ refresh_token: 'ref-stored' }))
  })

  it('dispatches setUser and setTokens on successful refresh', async () => {
    // GIVEN
    mockRefreshUnwrap.mockResolvedValue({
      access_token: 'fresh_acc',
      refresh_token: 'fresh_ref',
      user: USER,
    })
    const store = buildStore({ tokens: TOKENS, user: null })

    // WHEN
    renderAppStartup(store)

    // THEN — Redux state updated
    await waitFor(() => {
      const state = store.getState().auth
      expect(state.user).toEqual(USER)
      expect(state.tokens.accessToken).toBe('fresh_acc')
      expect(state.tokens.refreshToken).toBe('fresh_ref')
    })
  })

  it('dispatches clearAuth when backend explicitly rejects with 401', async () => {
    // GIVEN refresh fails with 401 (invalid/expired token — backend decision)
    mockRefreshUnwrap.mockRejectedValue({ status: 401 })
    const store = buildStore({ tokens: TOKENS, user: null })

    // WHEN
    renderAppStartup(store)

    // THEN — store cleared because backend said token is invalid
    await waitFor(() => {
      const state = store.getState().auth
      expect(state.user).toBeNull()
      expect(state.tokens.accessToken).toBeNull()
      expect(state.tokens.refreshToken).toBeNull()
    })
  })

  it('does NOT dispatch clearAuth on network error (Mixed Content, CORS, timeout)', async () => {
    // GIVEN refresh fails with a network-level error (no HTTP status code)
    // RTK Query represents network errors as { status: 'FETCH_ERROR', error: '...' }
    mockRefreshUnwrap.mockRejectedValue({ status: 'FETCH_ERROR', error: 'TypeError: Failed to fetch' })
    const store = buildStore({ tokens: TOKENS, user: null })

    // WHEN
    renderAppStartup(store)

    // THEN — tokens preserved, user can retry after network recovers
    await waitFor(() => {
      const state = store.getState().auth
      // tokens must still be present (not cleared)
      expect(state.tokens.refreshToken).toBe('ref-stored')
    })
  })
})

describe('AppStartup — idempotency', () => {
  it('does NOT call refresh twice even if re-rendered', async () => {
    // GIVEN
    mockRefreshUnwrap.mockResolvedValue({
      access_token: 'acc2',
      refresh_token: 'ref2',
      user: USER,
    })
    const store = buildStore({ tokens: TOKENS, user: null })
    const { rerender } = renderAppStartup(store)

    // WHEN re-rendered with same provider
    rerender(
      <Provider store={store}>
        <AppStartup>
          <div data-testid="children">app content</div>
        </AppStartup>
      </Provider>
    )

    // THEN refresh called only once (useRef guard)
    await waitFor(() => expect(mockRefreshTrigger).toHaveBeenCalledTimes(1))
  })
})
