import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AppLayout } from '../components/AppLayout'
import {
  useGetClientQuery,
  useGetCreditsQuery,
  useGetCreditQuery,
  useGetSavingsQuery,
  useAddContributionMutation,
  useLiquidateSavingsMutation,
  useGetHistoryQuery,
} from '../store/api/apiSlice'
import { PaymentModal } from '../components/PaymentModal'
import { Credit } from '../types'

type Tab = 'credits' | 'savings' | 'history'

export function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('credits')
  const [selectedCreditId, setSelectedCreditId] = useState<string | null>(null)
  const [showPaymentModal, setShowPaymentModal] = useState(false)

  const { data: client, isLoading: clientLoading } = useGetClientQuery(clientId!)
  const { data: credits = [] } = useGetCreditsQuery({ client_id: clientId })
  // Fetch full credit detail (with aggregates) only when one is selected
  const { data: selectedCredit } = useGetCreditQuery(selectedCreditId!, { skip: !selectedCreditId })
  const { data: savings = [] } = useGetSavingsQuery(clientId!, { skip: tab !== 'savings' })
  const { data: history = [] } = useGetHistoryQuery({ client_id: clientId }, { skip: tab !== 'history' })

  const [addContribution] = useAddContributionMutation()
  const [liquidate, { isLoading: liquidating }] = useLiquidateSavingsMutation()

  if (clientLoading) return <div className="p-8 text-center">Loading...</div>
  if (!client) return <div className="p-8 text-center text-red-500">Client not found</div>

  return (
    <AppLayout>
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate('/clients')} className="text-blue-600 text-sm">
          Back
        </button>
        <h2 className="text-xl font-semibold text-gray-800">
          {client.first_name} {client.last_name}
        </h2>
        {(client.mora_count ?? 0) > 0 && (
          <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full">Mora</span>
        )}
      </div>

      <div>
        <div className="flex gap-2 mb-4">
          {(['credits', 'savings', 'history'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === t ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border'}`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {tab === 'credits' && (
          <div>
            <div className="flex justify-between items-center mb-3">
              <h2 className="font-semibold text-gray-800">Credits</h2>
              <button
                onClick={() => navigate(`/clients/${clientId}/credits/new`)}
                className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm"
              >
                + New Credit
              </button>
            </div>

            <ul className="space-y-3">
              {credits.map((credit: Credit) => (
                <li
                  key={credit.id}
                  data-testid={`credit-row-${credit.id}`}
                  className={`bg-white rounded-xl shadow p-4 cursor-pointer border-2 ${selectedCreditId === credit.id ? 'border-blue-500' : 'border-transparent'}`}
                  onClick={() => setSelectedCreditId(credit.id === selectedCreditId ? null : credit.id)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-gray-900">
                        Capital: ${credit.pending_capital.toFixed(2)}
                      </p>
                      <p className="text-sm text-gray-500">
                        {credit.periodicity} | {credit.annual_interest_rate}% annual
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${credit.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                        {credit.status}
                      </span>
                      {credit.mora && (
                        <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                          Mora since {credit.mora_since}
                        </span>
                      )}
                    </div>
                  </div>

                  {selectedCreditId === credit.id && selectedCredit && (
                    <div className="mt-3 pt-3 border-t space-y-3" onClick={(e) => e.stopPropagation()}>
                      {/* Precomputed aggregates — no frontend math */}
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-blue-50 rounded-lg p-2">
                          <p className="text-gray-500">Interest this period</p>
                          <p className="font-semibold text-blue-700">
                            ${(selectedCredit.interest_due_current_period ?? 0).toFixed(2)}
                          </p>
                        </div>
                        <div className="bg-red-50 rounded-lg p-2">
                          <p className="text-gray-500">Overdue interest</p>
                          <p className="font-semibold text-red-700">
                            ${(selectedCredit.overdue_interest_total ?? 0).toFixed(2)}
                          </p>
                        </div>
                        <div className="bg-red-50 rounded-lg p-2">
                          <p className="text-gray-500">Overdue capital</p>
                          <p className="font-semibold text-red-700">
                            ${(selectedCredit.overdue_capital_total ?? 0).toFixed(2)}
                          </p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-2">
                          <p className="text-gray-500">Mora</p>
                          <p className={`font-semibold ${selectedCredit.mora_status?.in_mora ? 'text-red-700' : 'text-green-700'}`}>
                            {selectedCredit.mora_status?.in_mora
                              ? `Since ${selectedCredit.mora_status.since_date}`
                              : 'No mora'}
                          </p>
                        </div>
                      </div>

                      <button
                        onClick={() => setShowPaymentModal(true)}
                        data-testid="open-payment-modal"
                        className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700"
                      >
                        Register Payment
                      </button>

                      {(selectedCredit.overdue_installments?.length ?? 0) > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-red-700 mb-1">Overdue Installments</h4>
                          <ul className="space-y-1">
                            {selectedCredit.overdue_installments!.map((inst) => (
                              <li key={inst.id} className="flex justify-between text-sm py-1 border-b last:border-0">
                                <span className="text-red-600">#{inst.period_number} — {inst.expected_date}</span>
                                <span className="font-medium text-red-800">${inst.expected_value.toFixed(2)}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-1">Upcoming</h4>
                        <ul className="space-y-1">
                          {(selectedCredit.upcoming_installments ?? []).slice(0, 5).map((inst) => (
                            <li key={inst.id} className="flex justify-between text-sm py-1 border-b last:border-0">
                              <span className="text-gray-600">#{inst.period_number} — {inst.expected_date}</span>
                              <span className="font-medium text-gray-800">${inst.expected_value.toFixed(2)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {showPaymentModal && selectedCreditId && (
          <PaymentModal
            creditId={selectedCreditId}
            onClose={() => setShowPaymentModal(false)}
            onSuccess={() => setShowPaymentModal(false)}
          />
        )}

        {tab === 'savings' && (
          <div>
            <div className="flex justify-between items-center mb-3">
              <h2 className="font-semibold text-gray-800">Savings</h2>
              <button
                onClick={() => liquidate(clientId!)}
                disabled={liquidating}
                className="bg-yellow-500 text-white px-3 py-1.5 rounded-lg text-sm disabled:opacity-50"
              >
                {liquidating ? 'Liquidating...' : 'Liquidate'}
              </button>
            </div>
            <ul className="space-y-2">
              {savings.map((s) => (
                <li key={s.id} className="bg-white rounded-xl shadow px-4 py-3 flex justify-between">
                  <span className="text-sm text-gray-600">{s.contribution_date}</span>
                  <span className={`text-sm font-medium ${s.status === 'LIQUIDATED' ? 'text-gray-400' : 'text-green-700'}`}>
                    ${s.contribution_amount.toFixed(2)} — {s.status}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {tab === 'history' && (
          <div>
            <h2 className="font-semibold text-gray-800 mb-3">History</h2>
            <ul className="space-y-2">
              {history.map((evt) => (
                <li key={evt.id} className="bg-white rounded-xl shadow px-4 py-3">
                  <div className="flex justify-between">
                    <span className="text-xs text-blue-600 font-medium">{evt.event_type}</span>
                    <span className="text-xs text-gray-400">{new Date(evt.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm text-gray-700 mt-1">{evt.description}</p>
                  {evt.amount != null && (
                    <p className="text-sm font-medium text-gray-900 mt-0.5">${evt.amount.toFixed(2)}</p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
