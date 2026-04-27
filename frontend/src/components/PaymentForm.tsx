/**
 * PaymentForm — Phase 4 minimal integration component.
 *
 * Contract: .github/specs/payment-contract.md
 *
 * Rules:
 * - NO business logic here — all allocation computed server-side
 * - Calls /payments/preview before submit to show breakdown
 * - Confirm → POST /payments with operator_id
 * - All amounts displayed as-is from server (Decimal strings)
 * - No re-implementation of allocation algorithm
 */
import React, { useState } from 'react'
import {
  usePreviewPaymentMutation,
  useProcessPaymentMutation,
} from '../store/api/apiSlice'
import type { PaymentPreview, PaymentAppliedTo } from '../types'

interface PaymentFormProps {
  creditId: string
  operatorId: string // authenticated user id
  onSuccess?: (paymentId: string) => void
  onError?: (message: string) => void
}

type FormStep = 'input' | 'preview' | 'submitting' | 'done'

const TYPE_LABELS: Record<PaymentAppliedTo['type'], string> = {
  OVERDUE_INTEREST: 'Overdue Interest',
  OVERDUE_PRINCIPAL: 'Overdue Principal',
  FUTURE_PRINCIPAL: 'Future Principal',
}

export function PaymentForm({ creditId, operatorId, onSuccess, onError }: PaymentFormProps) {
  const [amount, setAmount] = useState<string>('')
  const [step, setStep] = useState<FormStep>('input')
  const [preview, setPreview] = useState<PaymentPreview | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const [previewPayment, { isLoading: isPreviewing }] = usePreviewPaymentMutation()
  const [processPayment, { isLoading: isSubmitting }] = useProcessPaymentMutation()

  function handleAmountChange(e: React.ChangeEvent<HTMLInputElement>) {
    setAmount(e.target.value)
    setErrorMsg(null)
  }

  async function handlePreview(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg(null)

    const amountNum = parseFloat(amount)
    if (!amount || isNaN(amountNum) || amountNum <= 0) {
      setErrorMsg('Amount must be a positive number.')
      return
    }

    try {
      const result = await previewPayment({
        credit_id: creditId,
        amount: amountNum.toFixed(2),
      }).unwrap()
      setPreview(result)
      setStep('preview')
    } catch (err: any) {
      const detail = err?.data?.detail ?? 'Preview failed. Please try again.'
      setErrorMsg(detail)
      onError?.(detail)
    }
  }

  async function handleConfirm() {
    if (!preview) return
    setStep('submitting')
    setErrorMsg(null)

    try {
      const result = await processPayment({
        credit_id: creditId,
        amount: preview.total_amount,
        operator_id: operatorId,
      }).unwrap()
      setStep('done')
      onSuccess?.(result.payment_id)
    } catch (err: any) {
      setStep('preview')
      if (err?.status === 409) {
        const msg = 'Payment conflict: the credit was modified concurrently. Please retry.'
        setErrorMsg(msg)
        onError?.(msg)
      } else {
        const detail = err?.data?.detail ?? 'Payment failed. Please try again.'
        setErrorMsg(detail)
        onError?.(detail)
      }
    }
  }

  function handleCancel() {
    setStep('input')
    setPreview(null)
    setErrorMsg(null)
  }

  if (step === 'done') {
    return (
      <div role="status" aria-live="polite">
        <p>Payment recorded successfully.</p>
        <button type="button" onClick={handleCancel}>
          Make another payment
        </button>
      </div>
    )
  }

  return (
    <div>
      {step === 'input' && (
        <form onSubmit={handlePreview} aria-label="Payment form">
          <fieldset>
            <legend>Register Payment</legend>
            <label htmlFor="payment-amount">
              Amount
              <input
                id="payment-amount"
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={handleAmountChange}
                required
                placeholder="0.00"
                aria-describedby={errorMsg ? 'payment-error' : undefined}
              />
            </label>
            {errorMsg && (
              <p id="payment-error" role="alert" aria-live="assertive">
                {errorMsg}
              </p>
            )}
            <button type="submit" disabled={isPreviewing}>
              {isPreviewing ? 'Calculating...' : 'Preview Breakdown'}
            </button>
          </fieldset>
        </form>
      )}

      {step === 'preview' && preview && (
        <div role="region" aria-label="Payment breakdown">
          <h3>Payment Breakdown</h3>
          <p>
            <strong>Total Amount:</strong> {preview.total_amount}
          </p>

          {preview.applied_to.length === 0 ? (
            <p>No installments will be covered by this payment.</p>
          ) : (
            <table aria-label="Allocation breakdown">
              <thead>
                <tr>
                  <th scope="col">Installment</th>
                  <th scope="col">Type</th>
                  <th scope="col">Amount</th>
                </tr>
              </thead>
              <tbody>
                {preview.applied_to.map((entry, idx) => (
                  <tr key={`${entry.installment_id}-${entry.type}-${idx}`}>
                    <td>
                      <code title={entry.installment_id}>
                        {entry.installment_id.slice(0, 8)}...
                      </code>
                    </td>
                    <td>{TYPE_LABELS[entry.type] ?? entry.type}</td>
                    <td>{entry.amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {parseFloat(preview.unallocated) > 0 && (
            <p>
              <strong>Unallocated:</strong> {preview.unallocated}
            </p>
          )}

          <div>
            <p>
              <strong>After payment — Pending Capital:</strong>{' '}
              {preview.updated_credit_snapshot.pending_capital}
            </p>
            <p>
              <strong>Mora status:</strong>{' '}
              {preview.updated_credit_snapshot.mora ? 'In mora' : 'Clear'}
            </p>
          </div>

          {errorMsg && (
            <p role="alert" aria-live="assertive">
              {errorMsg}
            </p>
          )}

          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting || step === 'submitting'}
            aria-busy={isSubmitting}
          >
            {isSubmitting ? 'Processing...' : 'Confirm Payment'}
          </button>
          <button type="button" onClick={handleCancel} disabled={isSubmitting}>
            Cancel
          </button>
        </div>
      )}

      {step === 'submitting' && (
        <p role="status" aria-live="polite" aria-busy="true">
          Processing payment...
        </p>
      )}
    </div>
  )
}
