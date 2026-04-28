import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AppLayout } from '../components/AppLayout'
import { useGetClientQuery } from '../store/api/apiSlice'
import { useGetHistoryQuery } from '../store/api/apiSlice'
import type { HistoryEvent } from '../types'

function getEventTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    CLIENT_CREATED: 'Cliente creado',
    CLIENT_UPDATED: 'Cliente actualizado',
    CLIENT_DELETED: 'Cliente eliminado',
    CREDIT_CREATED: 'Crédito creado',
    CREDIT_CLOSED: 'Crédito cerrado',
    CREDIT_SUSPENDED: 'Crédito suspendido',
    INSTALLMENT_GENERATED: 'Cuota generada',
    PAYMENT_RECORDED: 'Pago registrado',
    SAVINGS_CONTRIBUTION: 'Ahorro registrado',
    SAVINGS_LIQUIDATION: 'Liquidación de ahorro',
  }
  return labels[type] || type
}

function getEventTypeColor(type: string): string {
  const colors: Record<string, string> = {
    CLIENT_CREATED: 'bg-blue-100 text-blue-700',
    CLIENT_UPDATED: 'bg-gray-100 text-gray-700',
    CLIENT_DELETED: 'bg-red-100 text-red-700',
    CREDIT_CREATED: 'bg-green-100 text-green-700',
    CREDIT_CLOSED: 'bg-gray-100 text-gray-700',
    CREDIT_SUSPENDED: 'bg-yellow-100 text-yellow-700',
    INSTALLMENT_GENERATED: 'bg-purple-100 text-purple-700',
    PAYMENT_RECORDED: 'bg-green-100 text-green-700',
    SAVINGS_CONTRIBUTION: 'bg-yellow-100 text-yellow-700',
    SAVINGS_LIQUIDATION: 'bg-orange-100 text-orange-700',
  }
  return colors[type] || 'bg-gray-100 text-gray-700'
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-CO', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function HistoryEventItem({ event }: { event: HistoryEvent }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="relative border-l-2 border-gray-200 pl-4 pb-6 last:pb-0">
      <div className="absolute -left-1.5 top-0 h-3 w-3 rounded-full bg-gray-300" />
      
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${getEventTypeColor(event.event_type)}`}>
            {getEventTypeLabel(event.event_type)}
          </span>
          <span className="text-xs text-gray-400">{formatDate(event.created_at)}</span>
        </div>

        {event.amount != null && (
          <p className="text-lg font-semibold text-gray-900">
            {Number(event.amount).toLocaleString('es-CO', { style: 'currency', currency: 'COP' })}
          </p>
        )}

        <p className="text-sm text-gray-600">{event.description}</p>

        {event.metadata && Object.keys(event.metadata).length > 0 && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-600 hover:underline self-start"
          >
            {expanded ? 'Ocultar detalles' : 'Ver detalles'}
          </button>
        )}

        {expanded && event.metadata && (
          <pre className="mt-2 rounded bg-gray-50 p-2 text-xs overflow-x-auto">
            {JSON.stringify(event.metadata, null, 2)}
          </pre>
        )}

        <p className="text-xs text-gray-400">
          Operador: {event.operator_id}
        </p>
      </div>
    </div>
  )
}

const EVENT_TYPES = [
  'CLIENT_CREATED',
  'CREDIT_CREATED',
  'CREDIT_CLOSED',
  'INSTALLMENT_GENERATED',
  'PAYMENT_RECORDED',
  'SAVINGS_CONTRIBUTION',
  'SAVINGS_LIQUIDATION',
]

export function HistoryPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const [eventType, setEventType] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')

  const { data: client } = useGetClientQuery(clientId!)
  const { data: history = [], isLoading } = useGetHistoryQuery({
    client_id: clientId,
    event_type: eventType || undefined,
  })

  const filteredHistory = history.filter((event) => {
    if (dateFrom) {
      const eventDate = new Date(event.created_at)
      const fromDate = new Date(dateFrom)
      if (eventDate < fromDate) return false
    }
    return true
  })

  if (!clientId) {
    return (
      <AppLayout>
        <p className="p-8 text-center text-red-500">Client ID requerido</p>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate(`/clients/${clientId}`)}
            className="text-blue-600 text-sm hover:underline"
          >
            &larr; Volver
          </button>
        </div>

        <div className="bg-white rounded-xl shadow p-4 mb-4">
          <h1 className="text-xl font-semibold text-gray-900 mb-1">
            Historial
          </h1>
          <p className="text-sm text-gray-500">
            {client?.first_name} {client?.last_name}
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow p-4 mb-4 space-y-3">
          <h2 className="text-sm font-medium text-gray-700">Filtros</h2>
          
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="event-type" className="block text-xs text-gray-500 mb-1">
                Tipo de evento
              </label>
              <select
                id="event-type"
                value={eventType}
                onChange={(e) => setEventType(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Todos</option>
                {EVENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {getEventTypeLabel(type)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="date-from" className="block text-xs text-gray-500 mb-1">
                Desde fecha
              </label>
              <input
                id="date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-xl shadow p-4">
          <h2 className="text-sm font-medium text-gray-700 mb-4">
            Eventos ({filteredHistory.length})
          </h2>

          {isLoading ? (
            <p className="text-center text-gray-500 py-4">Cargando...</p>
          ) : filteredHistory.length === 0 ? (
            <p className="text-center text-gray-400 py-4">No hay eventos registrados</p>
          ) : (
            <div className="ml-2">
              {filteredHistory.map((event) => (
                <HistoryEventItem key={event.id} event={event} />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}