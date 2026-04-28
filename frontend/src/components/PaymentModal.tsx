import { useState } from 'react'
import { useAppSelector } from '../hooks/useStore'
import { usePreviewPaymentMutation, useProcessPaymentMutation } from '../store/api/apiSlice'
import type { PaymentPreview } from '../types'

interface Props {
  creditId: string
  onClose: () => void
  onSuccess: () => void
}

type Step = 'input' | 'preview' | 'confirming'

export function PaymentModal({ creditId, onClose, onSuccess }: Props) {
  const [amount, setAmount] = useState('')
  const [preview, setPreview] = useState<PaymentPreview | null>(null)
  const [step, setStep] = useState<Step>('input')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const operatorId = useAppSelector((state) => state.auth.user?.id ?? 'unknown')

  const [previewPayment, { isLoading: previewing }] = usePreviewPaymentMutation()
  const [processPayment, { isLoading: processing }] = useProcessPaymentMutation()

  const handlePreview = async () => {
    const parsed = parseFloat(amount)
    if (!parsed || parsed <= 0) return
    setErrorMsg(null)
    try {
      const result = await previewPayment({ credit_id: creditId, amount: parsed.toFixed(2) }).unwrap()
      setPreview(result)
      setStep('preview')
    } catch (err: any) {
      setErrorMsg(err?.data?.detail ?? 'Preview failed. Please try again.')
    }
  }

  const handleConfirm = async () => {
    if (!preview) return
    setStep('confirming')
    setErrorMsg(null)
    try {
      await processPayment({
        credit_id: creditId,
        amount: preview.total_amount,
        operator_id: operatorId,
      }).unwrap()
      onSuccess()
      onClose()
    } catch (err: any) {
      setStep('preview')
      if (err?.status === 409) {
        setErrorMsg('Payment conflict: the credit was modified concurrently. Please retry.')
      } else {
        setErrorMsg(err?.data?.detail ?? 'Payment failed. Please try again.')
      }
    }
  }

  const typeLabel: Record<string, string> = {
    OVERDUE_INTEREST: 'Overdue Interest',
    OVERDUE_PRINCIPAL: 'Overdue Principal',
    FUTURE_PRINCIPAL: 'Future Principal',
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      data-testid="payment-modal"
    >
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-gray-900">Register Payment</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            &times;
          </button>
        </div>

        {step === 'input' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
              <input
                type="number"
                step="0.01"
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                data-testid="payment-amount-input"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={handlePreview}
              disabled={!amount || parseFloat(amount) <= 0 || previewing}
              data-testid="preview-btn"
              className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {previewing ? 'Calculating...' : 'Preview Breakdown'}
            </button>
            {errorMsg && (
              <p role="alert" className="text-sm text-red-600 bg-red-50 rounded-lg p-2">
                {errorMsg}
              </p>
            )}
          </div>
        )}

        {step === 'preview' && preview && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Payment: <strong>${parseFloat(amount).toFixed(2)}</strong>
            </p>

            <div className="border rounded-lg divide-y" data-testid="preview-breakdown">
              {preview.applied_to.map((item, i) => (
                <div key={i} className="flex justify-between px-3 py-2 text-sm">
                  <span className="text-gray-700">{typeLabel[item.type] ?? item.type}</span>
                  <span className="font-medium text-gray-900">${item.amount}</span>
                </div>
              ))}
              {parseFloat(preview.unallocated) > 0 && (
                <div className="flex justify-between px-3 py-2 text-sm text-amber-700">
                  <span>Unallocated</span>
                  <span>${preview.unallocated}</span>
                </div>
              )}
            </div>

            {errorMsg && (
              <p role="alert" className="text-sm text-red-600 bg-red-50 rounded-lg p-2">
                {errorMsg}
              </p>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setStep('input')}
                className="flex-1 border text-gray-700 py-2 rounded-lg text-sm"
              >
                Back
              </button>
              <button
                onClick={handleConfirm}
                data-testid="confirm-payment-btn"
                disabled={processing}
                className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
              >
                {processing ? 'Processing...' : 'Confirm Payment'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
