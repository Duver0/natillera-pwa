import '@testing-library/jest-dom'
import { vi } from 'vitest'

vi.mock('./store/api/apiSlice', () => ({
  apiSlice: {
    reducerPath: 'api',
    reducer: vi.fn(),
    middleware: vi.fn(),
  },
  useLoginMutation: vi.fn(),
  useLogoutMutation: vi.fn(),
  useGetClientsQuery: vi.fn(),
  useGetClientQuery: vi.fn(),
  useGetCreditsQuery: vi.fn(),
  useGetInstallmentsQuery: vi.fn(),
  usePreviewPaymentMutation: vi.fn(),
  useProcessPaymentMutation: vi.fn(),
  useAddContributionMutation: vi.fn(),
  useGetSavingsQuery: vi.fn(),
  useGetHistoryQuery: vi.fn(),
}))
