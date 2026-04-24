import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { User, AuthTokens } from '../../types'

interface AuthState {
  user: User | null
  tokens: AuthTokens
  isLoading: boolean
  error: string | null
}

const storedTokens = (): AuthTokens => {
  try {
    const raw = localStorage.getItem('natillera_tokens')
    if (raw) return JSON.parse(raw)
  } catch {}
  return { accessToken: null, refreshToken: null }
}

const initialState: AuthState = {
  user: null,
  tokens: storedTokens(),
  isLoading: false,
  error: null,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setUser(state, action: PayloadAction<User | null>) {
      state.user = action.payload
    },
    setTokens(state, action: PayloadAction<AuthTokens>) {
      state.tokens = action.payload
      try {
        localStorage.setItem('natillera_tokens', JSON.stringify(action.payload))
      } catch {}
    },
    clearAuth(state) {
      state.user = null
      state.tokens = { accessToken: null, refreshToken: null }
      try {
        localStorage.removeItem('natillera_tokens')
      } catch {}
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload
    },
  },
})

export const { setUser, setTokens, clearAuth, setError } = authSlice.actions
export default authSlice.reducer
