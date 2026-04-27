/**
 * creditApi — re-exports credit + installment hooks from the central apiSlice.
 *
 * The apiSlice already contains all credit and installment endpoints.
 * This file exists as a stable import boundary so feature code imports
 * from creditApi without coupling directly to apiSlice internals.
 */
export {
  useGetCreditsQuery,
  useGetCreditQuery,
  useCreateCreditMutation,
  useGetInstallmentsQuery as useGetCreditInstallmentsQuery,
} from './apiSlice'
