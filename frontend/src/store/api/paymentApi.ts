/**
 * paymentApi — stable import boundary for payment endpoints.
 * All RTK Query logic lives in apiSlice; this file decouples
 * feature code from apiSlice internals.
 */
export {
  usePreviewPaymentMutation,
  useProcessPaymentMutation,
  useGetPaymentsQuery,
} from './apiSlice'
