/**
 * Unit tests for authSlice Redux state.
 * SPEC-002 §3.2 Phase 2.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import authReducer, { setUser, setTokens, clearAuth, setError } from '../store/slices/authSlice'

const initialState = {
  user: null,
  tokens: { accessToken: null, refreshToken: null },
  isLoading: false,
  error: null,
}

describe('authSlice', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('has correct initial state', () => {
    const state = authReducer(undefined, { type: '@@INIT' })
    expect(state.user).toBeNull()
    expect(state.tokens.accessToken).toBeNull()
  })

  it('setUser stores user in state', () => {
    const user = { id: 'uuid-1', email: 'test@example.com' }
    const state = authReducer(initialState, setUser(user))
    expect(state.user).toEqual(user)
  })

  it('setTokens stores tokens and persists to localStorage', () => {
    const tokens = { accessToken: 'access-123', refreshToken: 'refresh-456' }
    const state = authReducer(initialState, setTokens(tokens))
    expect(state.tokens.accessToken).toBe('access-123')
    const stored = JSON.parse(localStorage.getItem('natillera_tokens')!)
    expect(stored.accessToken).toBe('access-123')
  })

  it('clearAuth resets state and removes localStorage tokens', () => {
    localStorage.setItem('natillera_tokens', JSON.stringify({ accessToken: 'x', refreshToken: 'y' }))
    const populated = {
      ...initialState,
      user: { id: '1', email: 'a@b.com' },
      tokens: { accessToken: 'x', refreshToken: 'y' },
    }
    const state = authReducer(populated, clearAuth())
    expect(state.user).toBeNull()
    expect(state.tokens.accessToken).toBeNull()
    expect(localStorage.getItem('natillera_tokens')).toBeNull()
  })

  it('setError stores error message', () => {
    const state = authReducer(initialState, setError('invalid_credentials'))
    expect(state.error).toBe('invalid_credentials')
  })

  it('setError with null clears error', () => {
    const withError = { ...initialState, error: 'some_error' }
    const state = authReducer(withError, setError(null))
    expect(state.error).toBeNull()
  })
})
