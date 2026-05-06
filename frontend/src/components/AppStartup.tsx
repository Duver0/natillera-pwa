import { useEffect, useRef } from 'react'
import { useAppDispatch, useAppSelector } from '../hooks/useStore'
import { setUser, setTokens, clearAuth } from '../store/slices/authSlice'
import { useRefreshMutation } from '../store/api/apiSlice'

interface Props {
  children: React.ReactNode
}

export function AppStartup({ children }: Props) {
  const dispatch = useAppDispatch()
  const { tokens, user } = useAppSelector((state) => state.auth)
  const [refresh] = useRefreshMutation()
  const attempted = useRef(false)

  useEffect(() => {
    if (attempted.current) return
    attempted.current = true

    if (!tokens.refreshToken || user) return

    refresh({ refresh_token: tokens.refreshToken })
      .unwrap()
      .then((data) => {
        dispatch(setUser(data.user))
        dispatch(setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token }))
      })
      .catch((error: unknown) => {
        // Solo limpiar sesion si el backend rechazo el token (401 Unauthorized).
        // Errores de red (Mixed Content, timeout, CORS) son transitorios y no
        // invalidan el refreshToken — conservar tokens para permitir reintento.
        const status =
          (error as { status?: number })?.status ??
          (error as { originalStatus?: number })?.originalStatus
        if (status === 401) {
          dispatch(clearAuth())
        }
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>
}
