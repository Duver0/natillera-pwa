/**
 * savingsApi — stable import boundary for savings endpoints.
 * All RTK Query logic lives in apiSlice; this file decouples
 * feature code from apiSlice internals.
 */
export {
  useGetSavingsQuery,
  useAddContributionMutation,
  useLiquidateSavingsMutation,
} from './apiSlice'
