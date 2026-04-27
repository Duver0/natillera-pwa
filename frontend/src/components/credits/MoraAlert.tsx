import React from 'react'

interface MoraAlertProps {
  moraSince: string | null | undefined
  moraAmount?: number
}

/**
 * MoraAlert — informational only. No actions. No penalties.
 * Renders null when moraSince is falsy.
 */
const MoraAlert: React.FC<MoraAlertProps> = ({ moraSince, moraAmount }) => {
  if (!moraSince) return null

  const since = new Date(moraSince)
  const today = new Date()
  const diffMs = today.getTime() - since.getTime()
  const daysOverdue = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)))

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <span className="mt-0.5 text-base" aria-hidden="true">⚠️</span>
      <div>
        <p className="font-semibold">Crédito en mora</p>
        <p className="mt-0.5">
          En mora desde el{' '}
          <span className="font-medium">{since.toLocaleDateString('es-CO')}</span>
          {' '}({daysOverdue} {daysOverdue === 1 ? 'día' : 'días'}).
        </p>
        {moraAmount !== undefined && moraAmount > 0 && (
          <p className="mt-0.5">
            Monto vencido:{' '}
            <span className="font-medium">
              {moraAmount.toLocaleString('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 })}
            </span>
          </p>
        )}
        <p className="mt-1 text-xs text-red-600">
          Solo informativo. No se generan intereses adicionales por mora.
        </p>
      </div>
    </div>
  )
}

export default MoraAlert
