/**
 * Shared test utilities — Redux store + Router wrapper.
 */
import React from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { MemoryRouter } from 'react-router-dom'
import { apiSlice } from './store/api/apiSlice'
import authReducer from './store/slices/authSlice'
import uiReducer from './store/slices/uiSlice'

export function makeStore(preloadedState?: object) {
  return configureStore({
    reducer: {
      auth: authReducer,
      ui: uiReducer,
      [apiSlice.reducerPath]: apiSlice.reducer,
    },
    middleware: (g) => g().concat(apiSlice.middleware),
    preloadedState,
  })
}

interface WrapperOptions {
  preloadedState?: object
  initialEntries?: string[]
}

export function renderWithProviders(
  ui: React.ReactElement,
  options: WrapperOptions & Omit<RenderOptions, 'wrapper'> = {}
) {
  const { preloadedState, initialEntries = ['/'], ...renderOptions } = options
  const store = makeStore(preloadedState)
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </Provider>
    )
  }
  const result = render(ui, { wrapper: Wrapper, ...renderOptions })
  return { ...result, store }
}

export const authenticatedState = {
  auth: {
    user: { id: 'u1', email: 'test@test.com' },
    tokens: { accessToken: 'tok', refreshToken: 'ref' },
    isLoading: false,
    error: null,
  },
}

export * from '@testing-library/react'
