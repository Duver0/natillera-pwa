import { useState, useRef, useEffect } from 'react'
import { useGetSavingsQuery, useAddContributionMutation, useLiquidateSavingsMutation } from '../store/api/savingsApi'
import type { SavingsLiquidation } from '../types'

interface Props {
  clientId: string
}

interface ContributionFormState {
  amount: string
  date: string
}

function ContributionForm({ clientId, onSuccess }: { clientId: string; onSuccess: () => void }) {
  const [form, setForm] = useState<ContributionFormState>({
    amount: '',
    date: new Date().toISOString().split('T')[0],
  })
  const [error, setError] = useState<string | null>(null)
  const errorRef = useRef<HTMLDivElement>(null)
  const [addContribution, { isLoading }] = useAddContributionMutation()

  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.focus()
    }
  }, [error])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const amount = parseFloat(form.amount)
    if (isNaN(amount) || amount <= 0) {
      setError('Amount must be a positive number')
      return
    }

    try {
      await addContribution({
        client_id: clientId,
        contribution_amount: amount,
        contribution_date: form.date,
      }).unwrap()
      setForm({ amount: '', date: new Date().toISOString().split('T')[0] })
      onSuccess()
    } catch {
      setError('Failed to add contribution. Please try again.')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-4 mb-4" noValidate>
      <h3 className="font-medium text-gray-800 mb-3">Add Contribution</h3>

      {error && (
        <div
          ref={errorRef}
          role="alert"
          aria-live="assertive"
          tabIndex={-1}
          className="mb-3 p-2 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200"
        >
          {error}
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <label htmlFor="contribution-amount" className="block text-sm text-gray-600 mb-1">
            Amount
          </label>
          <input
            id="contribution-amount"
            type="number"
            min="0.01"
            step="0.01"
            required
            aria-required="true"
            value={form.amount}
            onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="0.00"
          />
        </div>

        <div className="flex-1">
          <label htmlFor="contribution-date" className="block text-sm text-gray-600 mb-1">
            Date
          </label>
          <input
            id="contribution-date"
            type="date"
            required
            aria-required="true"
            value={form.date}
            onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={isLoading}
            aria-label="Add savings contribution"
            className="w-full sm:w-auto bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            {isLoading ? 'Adding...' : 'Add'}
          </button>
        </div>
      </div>
    </form>
  )
}

interface LiquidateModalProps {
  onConfirm: () => void
  onCancel: () => void
  isLoading: boolean
}

function LiquidateModal({ onConfirm, onCancel, isLoading }: LiquidateModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    cancelRef.current?.focus()
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onCancel])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="liquidate-title"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4"
    >
      <div className="bg-white rounded-xl shadow-xl w-full sm:max-w-sm p-6">
        <h2 id="liquidate-title" className="text-lg font-semibold text-gray-900 mb-2">
          Confirm Liquidation
        </h2>
        <p className="text-sm text-gray-600 mb-5">
          This will liquidate all active savings for this client. This action cannot be undone.
        </p>
        <div className="flex gap-3">
          <button
            ref={cancelRef}
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-gray-400"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            aria-label="Confirm savings liquidation"
            className="flex-1 bg-yellow-500 text-white py-2 rounded-lg text-sm font-medium hover:bg-yellow-600 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-yellow-500"
          >
            {isLoading ? 'Liquidating...' : 'Confirm Liquidate'}
          </button>
        </div>
      </div>
    </div>
  )
}

interface LiquidationResultProps {
  result: SavingsLiquidation
  onDismiss: () => void
}

function LiquidationResult({ result, onDismiss }: LiquidationResultProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="bg-green-50 border border-green-200 rounded-xl p-4 mb-4"
    >
      <div className="flex justify-between items-start">
        <h3 className="font-semibold text-green-800 mb-2">Liquidation Complete</h3>
        <button
          onClick={onDismiss}
          aria-label="Dismiss liquidation result"
          className="text-green-600 hover:text-green-800 text-lg leading-none focus:outline-none focus:ring-2 focus:ring-green-500 rounded"
        >
          &times;
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
        <div className="bg-white rounded-lg p-2">
          <p className="text-gray-500 text-xs">Total Contributions</p>
          <p className="font-semibold text-gray-900">${result.total_contributions.toFixed(2)}</p>
        </div>
        <div className="bg-white rounded-lg p-2">
          <p className="text-gray-500 text-xs">Interest Earned</p>
          <p className="font-semibold text-green-700">${result.interest_earned.toFixed(2)}</p>
        </div>
        <div className="bg-white rounded-lg p-2 col-span-2 sm:col-span-1">
          <p className="text-gray-500 text-xs">Total Delivered</p>
          <p className="font-semibold text-blue-700">${result.total_delivered.toFixed(2)}</p>
        </div>
      </div>
    </div>
  )
}

export function SavingsView({ clientId }: Props) {
  const [showLiquidateModal, setShowLiquidateModal] = useState(false)
  const [liquidationResult, setLiquidationResult] = useState<SavingsLiquidation | null>(null)

  const { data: savings = [], isLoading } = useGetSavingsQuery(clientId)
  const [liquidate, { isLoading: liquidating }] = useLiquidateSavingsMutation()

  const activeSavings = savings.filter((s) => s.status === 'ACTIVE')

  const handleLiquidate = async () => {
    try {
      const result = await liquidate(clientId).unwrap()
      setLiquidationResult(result)
      setShowLiquidateModal(false)
    } catch {
      setShowLiquidateModal(false)
    }
  }

  return (
    <section aria-label="Savings management">
      <ContributionForm clientId={clientId} onSuccess={() => {}} />

      {liquidationResult && (
        <LiquidationResult result={liquidationResult} onDismiss={() => setLiquidationResult(null)} />
      )}

      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-gray-800">
          Contributions
          {activeSavings.length > 0 && (
            <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
              {activeSavings.length} active
            </span>
          )}
        </h2>
        <button
          onClick={() => setShowLiquidateModal(true)}
          disabled={activeSavings.length === 0}
          aria-label="Liquidate all active savings"
          className="bg-yellow-500 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-yellow-600 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2"
        >
          Liquidate
        </button>
      </div>

      {isLoading ? (
        <p className="text-center text-gray-500 py-6 text-sm">Loading contributions...</p>
      ) : savings.length === 0 ? (
        <p className="text-center text-gray-400 py-6 text-sm">No contributions yet</p>
      ) : (
        <ul className="space-y-2" aria-label="Savings contributions list">
          {savings.map((s) => (
            <li
              key={s.id}
              className="bg-white rounded-xl shadow px-4 py-3 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    s.status === 'ACTIVE'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {s.status}
                </span>
                <span className="text-sm text-gray-600">{s.contribution_date}</span>
              </div>
              <span
                className={`text-sm font-semibold ${
                  s.status === 'LIQUIDATED' ? 'text-gray-400' : 'text-green-700'
                }`}
              >
                ${s.contribution_amount.toFixed(2)}
              </span>
            </li>
          ))}
        </ul>
      )}

      {showLiquidateModal && (
        <LiquidateModal
          onConfirm={handleLiquidate}
          onCancel={() => setShowLiquidateModal(false)}
          isLoading={liquidating}
        />
      )}
    </section>
  )
}
