import React, { useState } from 'react'
import { useGetInstallmentsQuery } from '../../store/api/apiSlice'
import type { Installment, InstallmentStatus } from '../../types'

interface InstallmentViewProps {
  creditId: string
}

type FilterTab = 'all' | 'upcoming' | 'paid' | 'overdue'

const statusBadge: Record<InstallmentStatus, string> = {
  UPCOMING: 'bg-blue-100 text-blue-700',
  PARTIALLY_PAID: 'bg-yellow-100 text-yellow-700',
  PAID: 'bg-green-100 text-green-700',
  SUSPENDED: 'bg-gray-100 text-gray-500',
}

const statusLabel: Record<InstallmentStatus, string> = {
  UPCOMING: 'Pendiente',
  PARTIALLY_PAID: 'Parcial',
  PAID: 'Pagada',
  SUSPENDED: 'Suspendida',
}

const fmt = (amount: number) =>
  amount.toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 })

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })

function applyFilter(installments: Installment[], tab: FilterTab): Installment[] {
  if (tab === 'all') return installments
  if (tab === 'upcoming') return installments.filter((i) => i.status === 'UPCOMING' && !i.is_overdue)
  if (tab === 'paid') return installments.filter((i) => i.status === 'PAID')
  if (tab === 'overdue') return installments.filter((i) => i.is_overdue && i.status !== 'PAID')
  return installments
}

const tabLabels: { key: FilterTab; label: string }[] = [
  { key: 'all', label: 'Todas' },
  { key: 'upcoming', label: 'Pendientes' },
  { key: 'paid', label: 'Pagadas' },
  { key: 'overdue', label: 'Vencidas' },
]

const InstallmentView: React.FC<InstallmentViewProps> = ({ creditId }) => {
  const [activeTab, setActiveTab] = useState<FilterTab>('all')
  const { data: installments, isLoading, isError } = useGetInstallmentsQuery({ credit_id: creditId })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-gray-500">
        Cargando cuotas…
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
        Error al cargar las cuotas. Intenta de nuevo.
      </div>
    )
  }

  const all = installments ?? []
  const filtered = applyFilter(all, activeTab)

  return (
    <div className="space-y-4">
      {/* Filter tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
        {tabLabels.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              activeTab === key
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {label}
            {key !== 'all' && (
              <span className="ml-1 text-gray-400">
                ({applyFilter(all, key).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="py-6 text-center text-sm text-gray-400">No hay cuotas para mostrar.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-500">#</th>
                <th className="px-3 py-2 text-left font-medium text-gray-500">Fecha</th>
                <th className="px-3 py-2 text-right font-medium text-gray-500">Valor</th>
                <th className="px-3 py-2 text-right font-medium text-gray-500">Pagado</th>
                <th className="px-3 py-2 text-center font-medium text-gray-500">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((inst) => (
                <tr
                  key={inst.id}
                  className={inst.is_overdue && inst.status !== 'PAID' ? 'bg-red-50' : ''}
                >
                  <td className="px-3 py-2 font-mono text-gray-700">{inst.period_number}</td>
                  <td className="px-3 py-2 text-gray-600">{fmtDate(inst.expected_date)}</td>
                  <td className="px-3 py-2 text-right text-gray-900">{fmt(inst.expected_value)}</td>
                  <td className="px-3 py-2 text-right text-gray-600">{fmt(inst.paid_value)}</td>
                  <td className="px-3 py-2 text-center">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        inst.is_overdue && inst.status !== 'PAID'
                          ? 'bg-red-100 text-red-700'
                          : statusBadge[inst.status]
                      }`}
                    >
                      {inst.is_overdue && inst.status !== 'PAID'
                        ? 'Vencida'
                        : statusLabel[inst.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default InstallmentView
