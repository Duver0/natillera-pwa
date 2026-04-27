/**
 * Shared test utilities — wraps components with Redux Provider.
 */
import React from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { apiSlice } from './store/api/apiSlice'
import authReducer from './store/slices/authSlice'
import uiReducer from './store/slices/uiSlice'

function makeTestStore() {
  return configureStore({
    reducer: {
      auth: authReducer,
      ui: uiReducer,
      [apiSlice.reducerPath]: apiSlice.reducer,
    },
    middleware: (gDM) => gDM().concat(apiSlice.middleware),
  })
}

function AllProviders({ children }: { children: React.ReactNode }) {
  const store = makeTestStore()
  return <Provider store={store}>{children}</Provider>
}

function customRender(ui: React.ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return render(ui, { wrapper: AllProviders, ...options })
}

export * from '@testing-library/react'
export { customRender as render }
