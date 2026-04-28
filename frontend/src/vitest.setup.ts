import '@testing-library/jest-dom'
import { vi } from 'vitest'

const { apiSlice, mockHooks } = vi.hoisted(() => {
  const apiSlice = {
    reducerPath: 'api' as const,
    reducer: vi.fn(),
    middleware: vi.fn(),
  }
  const mockHooks = {
    useLoginMutation: vi.fn(() => ([{ mutate: vi.fn() }, { isLoading: false }])),
    useLogoutMutation: vi.fn(() => ([{ mutate: vi.fn() }, { isLoading: false }])),
    useGetClientsQuery: vi.fn(() => ({ data: undefined, isLoading: false })),
    useGetClientQuery: vi.fn(() => ({ data: undefined, isLoading: false })),
    useGetCreditsQuery: vi.fn(() => ({ data: undefined, isLoading: false })),
    useGetInstallmentsQuery: vi.fn(() => ({ data: undefined, isLoading: false })),
    usePreviewPaymentMutation: vi.fn(() => ([{ mutateAsync: vi.fn() }, { isLoading: false }])),
    useProcessPaymentMutation: vi.fn(() => ([{ mutateAsync: vi.fn() }, { isLoading: false }])),
    useAddContributionMutation: vi.fn(() => ([{ mutateAsync: vi.fn() }, { isLoading: false }])),
    useGetSavingsQuery: vi.fn(() => ({ data: undefined, isLoading: false })),
    useGetHistoryQuery: vi.fn(() => ({ data: undefined, isLoading: false })),
  }
  return { apiSlice, mockHooks }
})

vi.mock('./store/api/apiSlice', () => ({
  __esModule: true,
  apiSlice,
  ...mockHooks,
}))
