import { useGetPaymentsQuery } from '../store/api/apiSlice'
import type { Payment } from '../types'

interface PaymentHistoryProps {
  creditId: string
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-CO', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function getAppliedTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    OVERDUE_INTEREST: 'Interés moratorio',
    OVERDUE_PRINCIPAL: 'Capital moratorio',
    FUTURE_PRINCIPAL: 'Capital futuro',
    FUTURE_INTEREST: 'Interés futuro',
  }
  return labels[type] || type
}

export function PaymentHistory({ creditId }: PaymentHistoryProps) {
  const { data: payments = [], isLoading, isFetching } = useGetPaymentsQuery(creditId)

  if (isLoading || isFetching) {
    return (
      <div className="text-center py-4">
        <p className="text-sm text-gray-500">Cargando pagos...</p>
      </div>
    )
  }

  if (payments.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-sm text-gray-400">No hay pagos registrados</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h3 className="font-medium text-gray-800 text-sm">Historial de Pagos</h3>
      <ul className="space-y-2">
        {payments.map((payment: Payment) => (
          <li
            key={payment.id}
            className="bg-white rounded-lg shadow p-3 text-sm"
          >
            <div className="flex justify-between items-start mb-2">
              <span className="font-semibold text-green-700">
                ${Number(payment.amount).toFixed(2)}
              </span>
              <span className="text-xs text-gray-500">
                {formatDate(payment.payment_date)}
              </span>
            </div>
            {payment.applied_to && Array.isArray(payment.applied_to) && payment.applied_to.length > 0 && (
              <div className="text-xs text-gray-600 space-y-1">
                <p className="font-medium text-gray-500">Distribución:</p>
                {payment.applied_to.map((entry: any, idx: number) => (
                  <div key={idx} className="flex justify-between pl-2">
                    <span>{getAppliedTypeLabel(entry.type)}</span>
                    <span>${Number(entry.amount).toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
            {payment.notes && (
              <p className="text-xs text-gray-500 mt-2 italic">{payment.notes}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}