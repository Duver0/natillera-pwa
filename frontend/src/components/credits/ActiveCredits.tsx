import React, { useState } from 'react'
import { useGetCreditsQuery } from '../../store/api/apiSlice'
import type { Credit, Installment } from '../../types'
import MoraAlert from './MoraAlert'
import CreditForm from './CreditForm'

interface ActiveCreditsProps {
  clientId: string
}

const fmt = (amount: number) =>
  amount.toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 })

const fmtDate = (iso?: string | null) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })
}

interface CreditCardProps {
  credit: Credit
}

const CreditCard: React.FC<CreditCardProps> = ({ credit }) => {
  const [expanded, setExpanded] = useState(false)

  const nextInstallments: Installment[] = credit.upcoming_installments?.slice(0, 3) ?? []
  const overdueMoraAmount =
    (credit.overdue_interest_total ?? 0) + (credit.overdue_capital_total ?? 0)

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-4">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">
              {credit.periodicity}
            </span>
            {credit.mora && (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                MORA
              </span>
            )}
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                credit.status === 'ACTIVE'
                  ? 'bg-green-100 text-green-700'
                  : credit.status === 'CLOSED'
                  ? 'bg-gray-100 text-gray-500'
                  : 'bg-yellow-100 text-yellow-700'
              }`}
            >
              {credit.status === 'ACTIVE' ? 'Activo' : credit.status === 'CLOSED' ? 'Cerrado' : 'Suspendido'}
            </span>
          </div>
          <p className="text-xl font-bold text-gray-900">{fmt(credit.pending_capital)}</p>
          <p className="text-xs text-gray-500">Capital pendiente</p>
        </div>
        <div className="text-right text-xs text-gray-500">
          <p>Tasa anual</p>
          <p className="text-base font-semibold text-gray-800">{credit.annual_interest_rate}%</p>
        </div>
      </div>

      {/* Mora alert */}
      {credit.mora && (
        <div className="px-4 pb-3">
          <MoraAlert moraSince={credit.mora_since} moraAmount={overdueMoraAmount} />
        </div>
      )}

      {/* Next installment */}
      {credit.next_installment && (
        <div className="border-t border-gray-100 px-4 py-3">
          <p className="mb-1 text-xs font-medium text-gray-500">Próxima cuota</p>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">
              #{credit.next_installment.period_number} — {fmtDate(credit.next_installment.expected_date)}
            </span>
            <span className="text-sm font-semibold text-gray-900">
              {fmt(credit.next_installment.expected_value)}
            </span>
          </div>
        </div>
      )}

      {/* Expand toggle */}
      {nextInstallments.length > 0 && (
        <div className="border-t border-gray-100">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-2.5 text-xs text-blue-600 hover:bg-blue-50"
          >
            <span>{expanded ? 'Ocultar cuotas' : `Ver próximas ${nextInstallments.length} cuotas`}</span>
            <span>{expanded ? '▲' : '▼'}</span>
          </button>

          {expanded && (
            <div className="divide-y divide-gray-100 px-4 pb-3">
              {nextInstallments.map((inst) => (
                <div key={inst.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="text-gray-500">
                    #{inst.period_number} — {fmtDate(inst.expected_date)}
                  </span>
                  <span className="font-medium text-gray-900">{fmt(inst.expected_value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const ActiveCredits: React.FC<ActiveCreditsProps> = ({ clientId }) => {
  const [showForm, setShowForm] = useState(false)
  const { data: credits, isLoading, isError } = useGetCreditsQuery({ client_id: clientId, status: 'ACTIVE' })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">Créditos activos</h3>
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Nuevo crédito
        </button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8 text-sm text-gray-500">Cargando créditos…</div>
      )}

      {isError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Error al cargar los créditos. Intenta de nuevo.
        </div>
      )}

      {!isLoading && !isError && credits?.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 py-10 text-center text-sm text-gray-400">
          No hay créditos activos.
          <br />
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="mt-2 text-blue-600 underline hover:text-blue-700"
          >
            Crear el primero
          </button>
        </div>
      )}

      {credits?.map((credit) => (
        <CreditCard key={credit.id} credit={credit} />
      ))}

      <CreditForm clientId={clientId} isOpen={showForm} onClose={() => setShowForm(false)} />
    </div>
  )
}

export default ActiveCredits
