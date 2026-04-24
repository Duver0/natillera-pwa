import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { RootState } from '../store'
import type {
  Client,
  Credit,
  Installment,
  Payment,
  SavingsContribution,
  SavingsLiquidation,
  HistoryEvent,
  ClientSummary,
  PaymentPreview,
} from '../../types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: `${BASE_URL}/api/v1`,
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.tokens.accessToken
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
      }
      return headers
    },
  }),
  tagTypes: ['Client', 'Credit', 'Installment', 'Payment', 'Savings', 'History'],
  endpoints: (builder) => ({
    // AUTH
    login: builder.mutation<{ access_token: string; refresh_token: string; user: any }, { email: string; password: string }>({
      query: (body) => ({ url: '/auth/login', method: 'POST', body }),
    }),
    register: builder.mutation<{ access_token: string; refresh_token: string; user: any }, { email: string; password: string }>({
      query: (body) => ({ url: '/auth/register', method: 'POST', body }),
    }),
    logout: builder.mutation<void, void>({
      query: () => ({ url: '/auth/logout', method: 'POST' }),
    }),
    refresh: builder.mutation<{ access_token: string; refresh_token: string; user: any }, { refresh_token: string }>({
      query: (body) => ({ url: '/auth/refresh', method: 'POST', body }),
    }),

    // CLIENTS
    getClients: builder.query<
      { items: Client[]; total: number; limit: number; offset: number },
      { search?: string; limit?: number; offset?: number }
    >({
      query: ({ search, limit = 20, offset = 0 } = {}) => {
        const params = new URLSearchParams()
        if (search) params.set('search', search)
        params.set('limit', String(limit))
        params.set('offset', String(offset))
        return `/clients?${params}`
      },
      providesTags: ['Client'],
    }),
    getClient: builder.query<Client, string>({
      query: (id) => `/clients/${id}`,
      providesTags: (_r, _e, id) => [{ type: 'Client', id }],
    }),
    createClient: builder.mutation<Client, Partial<Client>>({
      query: (body) => ({ url: '/clients', method: 'POST', body }),
      invalidatesTags: ['Client'],
    }),
    updateClient: builder.mutation<Client, { id: string; data: Partial<Client> }>({
      query: ({ id, data }) => ({ url: `/clients/${id}`, method: 'PUT', body: data }),
      invalidatesTags: (_r, _e, { id }) => [{ type: 'Client', id }, 'Client'],
    }),
    deleteClient: builder.mutation<void, string>({
      query: (id) => ({ url: `/clients/${id}`, method: 'DELETE' }),
      invalidatesTags: ['Client'],
    }),
    getClientSummary: builder.query<ClientSummary, string>({
      query: (id) => `/clients/${id}/summary`,
      providesTags: (_r, _e, id) => [{ type: 'Client', id }],
    }),

    // CREDITS
    getCredits: builder.query<Credit[], { client_id?: string; status?: string }>({
      query: ({ client_id, status } = {}) => {
        const params = new URLSearchParams()
        if (client_id) params.set('client_id', client_id)
        if (status) params.set('status', status)
        return `/credits?${params}`
      },
      providesTags: ['Credit'],
    }),
    getCredit: builder.query<Credit, string>({
      query: (id) => `/credits/${id}`,
      providesTags: (_r, _e, id) => [{ type: 'Credit', id }],
    }),
    createCredit: builder.mutation<Credit, Partial<Credit>>({
      query: (body) => ({ url: '/credits', method: 'POST', body }),
      invalidatesTags: ['Credit'],
    }),

    // INSTALLMENTS
    getInstallments: builder.query<Installment[], { credit_id: string; status?: string }>({
      query: ({ credit_id, status }) => {
        const params = new URLSearchParams({ credit_id })
        if (status) params.set('status', status)
        return `/installments?${params}`
      },
      providesTags: ['Installment'],
    }),

    // PAYMENTS
    previewPayment: builder.mutation<PaymentPreview, { credit_id: string; amount: number }>({
      query: (body) => ({ url: '/payments/preview', method: 'POST', body }),
    }),
    processPayment: builder.mutation<Payment, { credit_id: string; amount: number; notes?: string }>({
      query: (body) => ({ url: '/payments', method: 'POST', body }),
      invalidatesTags: ['Credit', 'Installment', 'Payment', 'History'],
    }),
    getPayments: builder.query<Payment[], string>({
      query: (credit_id) => `/payments?credit_id=${credit_id}`,
      providesTags: ['Payment'],
    }),

    // SAVINGS
    addContribution: builder.mutation<SavingsContribution, { client_id: string; contribution_amount: number; contribution_date?: string }>({
      query: (body) => ({ url: '/savings/contributions', method: 'POST', body }),
      invalidatesTags: ['Savings'],
    }),
    liquidateSavings: builder.mutation<SavingsLiquidation, string>({
      query: (client_id) => ({ url: `/savings/liquidate?client_id=${client_id}`, method: 'POST' }),
      invalidatesTags: ['Savings', 'History'],
    }),
    getSavings: builder.query<SavingsContribution[], string>({
      query: (client_id) => `/savings?client_id=${client_id}`,
      providesTags: ['Savings'],
    }),

    // HISTORY
    getHistory: builder.query<HistoryEvent[], { client_id?: string; event_type?: string; limit?: number; offset?: number }>({
      query: ({ client_id, event_type, limit = 50, offset = 0 } = {}) => {
        const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
        if (client_id) params.set('client_id', client_id)
        if (event_type) params.set('event_type', event_type)
        return `/history?${params}`
      },
      providesTags: ['History'],
    }),
  }),
})

export const {
  useLoginMutation,
  useRegisterMutation,
  useLogoutMutation,
  useRefreshMutation,
  useGetClientsQuery,
  useGetClientQuery,
  useCreateClientMutation,
  useUpdateClientMutation,
  useDeleteClientMutation,
  useGetClientSummaryQuery,
  useGetCreditsQuery,
  useGetCreditQuery,
  useCreateCreditMutation,
  useGetInstallmentsQuery,
  usePreviewPaymentMutation,
  useProcessPaymentMutation,
  useGetPaymentsQuery,
  useAddContributionMutation,
  useLiquidateSavingsMutation,
  useGetSavingsQuery,
  useGetHistoryQuery,
} = apiSlice
