/**
 * useAuth hook tests.
 * Renders inside Redux + Router providers; API mutations are mocked.
 */
import { renderHook, act } from '@testing-library/react'
import React from 'react'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { makeStore } from '../../test-utils'
import { useAuth } from '../useAuth'
import type { User } from '../../types'

const USER: User = { id: 'u1', email: 'test@test.com' }

const mockLoginMutation = vi.fn()
const mockRegisterMutation = vi.fn()
const mockLogoutMutation = vi.fn()

vi.mock('../../store/api/apiSlice', async () => {
  const actual = await vi.importActual<typeof import('../../store/api/apiSlice')>('../../store/api/apiSlice')
  return {
    ...actual,
    useLoginMutation: () => [mockLoginMutation, { isLoading: false }],
    useRegisterMutation: () => [mockRegisterMutation, { isLoading: false }],
    useLogoutMutation: () => [mockLogoutMutation, {}],
  }
})

function wrapper({ children }: { children: React.ReactNode }) {
  const store = makeStore()
  return React.createElement(
    Provider,
    { store },
    React.createElement(MemoryRouter, null, children)
  )
}

describe('useAuth — initial state', () => {
  it('returns user=null and isAuthenticated=false by default', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('exposes login, register, logout functions', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(typeof result.current.login).toBe('function')
    expect(typeof result.current.register).toBe('function')
    expect(typeof result.current.logout).toBe('function')
  })
})

describe('useAuth — login', () => {
  it('dispatches setUser and setTokens after successful login', async () => {
    mockLoginMutation.mockReturnValue({
      unwrap: () => Promise.resolve({ user: USER, access_token: 'acc', refresh_token: 'ref' }),
    })
    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => {
      await result.current.login('test@test.com', 'pass')
    })
    expect(result.current.user).toEqual(USER)
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.tokens.accessToken).toBe('acc')
  })
})

describe('useAuth — logout', () => {
  it('clears auth state after logout', async () => {
    mockLoginMutation.mockReturnValue({
      unwrap: () => Promise.resolve({ user: USER, access_token: 'acc', refresh_token: 'ref' }),
    })
    mockLogoutMutation.mockReturnValue({ unwrap: () => Promise.resolve() })

    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => { await result.current.login('test@test.com', 'pass') })
    await act(async () => { await result.current.logout() })
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('clears auth even when logout API throws', async () => {
    mockLoginMutation.mockReturnValue({
      unwrap: () => Promise.resolve({ user: USER, access_token: 'acc', refresh_token: 'ref' }),
    })
    mockLogoutMutation.mockReturnValue({ unwrap: () => Promise.reject(new Error('Network error')) })

    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => { await result.current.login('test@test.com', 'pass') })
    await act(async () => { await result.current.logout() })
    expect(result.current.user).toBeNull()
  })
})
