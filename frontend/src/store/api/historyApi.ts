/**
 * historyApi — stable import boundary for history endpoints.
 * All RTK Query logic lives in apiSlice; this file decouples
 * feature code from apiSlice internals.
 */
export { useGetHistoryQuery } from './apiSlice'
