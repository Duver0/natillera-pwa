/**
 * installmentApi — re-exports installment hooks from the central apiSlice.
 *
 * The apiSlice query `getInstallments` hits GET /installments?credit_id=X.
 * This file provides a named alias so components can import from installmentApi
 * without knowing which slice owns the endpoint.
 */
export { useGetInstallmentsQuery } from './apiSlice'
