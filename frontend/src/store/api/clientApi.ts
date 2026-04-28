/**
 * clientApi — stable import boundary for client endpoints.
 * All RTK Query logic lives in apiSlice; this file decouples
 * feature code from apiSlice internals.
 */
export {
  useGetClientsQuery,
  useGetClientQuery,
  useCreateClientMutation,
  useUpdateClientMutation,
  useDeleteClientMutation,
  useGetClientSummaryQuery,
} from './apiSlice'
