/**
 * authSlice reducer unit tests.
 */
import authReducer, { setUser, setTokens, clearAuth, setError } from '../authSlice'
import type { User, AuthTokens } from '../../../types'

const USER: User = { id: 'u1', email: 'test@test.com' }
const TOKENS: AuthTokens = { accessToken: 'acc', refreshToken: 'ref' }

function freshState() {
  localStorage.clear()
  return authReducer(undefined, { type: '@@INIT' })
}

describe('authSlice — setUser', () => {
  it('sets the user', () => {
    const state = authReducer(freshState(), setUser(USER))
    expect(state.user).toEqual(USER)
  })

  it('clears user when null', () => {
    const withUser = authReducer(freshState(), setUser(USER))
    const cleared = authReducer(withUser, setUser(null))
    expect(cleared.user).toBeNull()
  })
})

describe('authSlice — setTokens', () => {
  it('sets tokens in state', () => {
    const state = authReducer(freshState(), setTokens(TOKENS))
    expect(state.tokens.accessToken).toBe('acc')
    expect(state.tokens.refreshToken).toBe('ref')
  })

  it('persists tokens to localStorage', () => {
    authReducer(freshState(), setTokens(TOKENS))
    const stored = JSON.parse(localStorage.getItem('natillera_tokens')!)
    expect(stored.accessToken).toBe('acc')
  })
})

describe('authSlice — clearAuth', () => {
  it('resets user and tokens', () => {
    let state = authReducer(freshState(), setUser(USER))
    state = authReducer(state, setTokens(TOKENS))
    state = authReducer(state, clearAuth())
    expect(state.user).toBeNull()
    expect(state.tokens.accessToken).toBeNull()
    expect(state.tokens.refreshToken).toBeNull()
  })

  it('removes tokens from localStorage', () => {
    let state = authReducer(freshState(), setTokens(TOKENS))
    authReducer(state, clearAuth())
    expect(localStorage.getItem('natillera_tokens')).toBeNull()
  })
})

describe('authSlice — setError', () => {
  it('sets error message', () => {
    const state = authReducer(freshState(), setError('Invalid credentials'))
    expect(state.error).toBe('Invalid credentials')
  })

  it('clears error when null', () => {
    let state = authReducer(freshState(), setError('err'))
    state = authReducer(state, setError(null))
    expect(state.error).toBeNull()
  })
})

describe('authSlice — hydration from localStorage', () => {
  it('reads tokens from localStorage on init', () => {
    localStorage.setItem('natillera_tokens', JSON.stringify(TOKENS))
    const state = authReducer(undefined, { type: '@@INIT' })
    expect(state.tokens.accessToken).toBe('acc')
    localStorage.clear()
  })

  it('defaults to null tokens when localStorage is empty', () => {
    localStorage.clear()
    const state = authReducer(undefined, { type: '@@INIT' })
    expect(state.tokens.accessToken).toBeNull()
  })
})

describe('authSlice — isAuthenticated derivation', () => {
  it('is authenticated when user and accessToken are set', () => {
    let state = authReducer(freshState(), setUser(USER))
    state = authReducer(state, setTokens(TOKENS))
    // The slice itself doesn't expose isAuthenticated — derived in useAuth
    expect(!!state.user && !!state.tokens.accessToken).toBe(true)
  })

  it('is not authenticated when user is null', () => {
    const state = authReducer(freshState(), setTokens(TOKENS))
    expect(!!state.user && !!state.tokens.accessToken).toBe(false)
  })
})
