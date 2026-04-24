import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from './useStore'
import { setUser, setTokens, clearAuth } from '../store/slices/authSlice'
import { useLoginMutation, useRegisterMutation, useLogoutMutation } from '../store/api/apiSlice'

export function useAuth() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const { user, tokens } = useAppSelector((state) => state.auth)

  const [loginMutation, { isLoading: loginLoading }] = useLoginMutation()
  const [registerMutation, { isLoading: registerLoading }] = useRegisterMutation()
  const [logoutMutation] = useLogoutMutation()

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await loginMutation({ email, password }).unwrap()
      dispatch(setUser(data.user))
      dispatch(setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token }))
      navigate('/dashboard')
    },
    [loginMutation, dispatch, navigate]
  )

  const register = useCallback(
    async (email: string, password: string) => {
      const data = await registerMutation({ email, password }).unwrap()
      dispatch(setUser(data.user))
      dispatch(setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token }))
      navigate('/dashboard')
    },
    [registerMutation, dispatch, navigate]
  )

  const logout = useCallback(async () => {
    try {
      await logoutMutation().unwrap()
    } finally {
      dispatch(clearAuth())
      navigate('/login')
    }
  }, [logoutMutation, dispatch, navigate])

  return {
    user,
    tokens,
    isAuthenticated: !!user && !!tokens.accessToken,
    login,
    register,
    logout,
    loginLoading,
    registerLoading,
  }
}
