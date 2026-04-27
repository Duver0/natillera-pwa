import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useCreateCreditMutation } from '../../store/api/apiSlice'

const schema = z.object({
  initial_capital: z
    .number({ invalid_type_error: 'El capital inicial es requerido' })
    .positive('El capital debe ser mayor a 0'),
  periodicity: z.enum(['DAILY', 'WEEKLY', 'BIWEEKLY', 'MONTHLY'], {
    errorMap: () => ({ message: 'Selecciona una periodicidad' }),
  }),
  annual_interest_rate: z
    .number({ invalid_type_error: 'La tasa es requerida' })
    .min(0, 'La tasa no puede ser negativa')
    .max(100, 'La tasa no puede superar 100%'),
  start_date: z.string().min(1, 'La fecha de inicio es requerida'),
})

type FormValues = z.infer<typeof schema>

interface CreditFormProps {
  clientId: string
  isOpen: boolean
  onClose: () => void
}

const periodicityLabels: Record<string, string> = {
  DAILY: 'Diaria (365/año)',
  WEEKLY: 'Semanal (52/año)',
  BIWEEKLY: 'Quincenal (26/año)',
  MONTHLY: 'Mensual (12/año)',
}

const CreditForm: React.FC<CreditFormProps> = ({ clientId, isOpen, onClose }) => {
  const [createCredit, { isLoading, error }] = useCreateCreditMutation()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      periodicity: 'MONTHLY',
      start_date: new Date().toISOString().split('T')[0],
    },
  })

  if (!isOpen) return null

  const onSubmit = async (values: FormValues) => {
    try {
      await createCredit({
        client_id: clientId,
        initial_capital: values.initial_capital,
        periodicity: values.periodicity,
        annual_interest_rate: values.annual_interest_rate,
        start_date: values.start_date,
      } as Parameters<typeof createCredit>[0]).unwrap()
      reset()
      onClose()
    } catch {
      // error shown via RTK Query error state
    }
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const apiErrorMessage =
    error && 'data' in error
      ? (error.data as { detail?: string })?.detail ?? 'Error al crear el crédito'
      : error
      ? 'Error al conectar con el servidor'
      : null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="credit-form-title"
    >
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 id="credit-form-title" className="text-lg font-semibold text-gray-900">
            Nuevo Crédito
          </h2>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-6 py-5">
          {/* Capital Inicial */}
          <div>
            <label htmlFor="initial_capital" className="block text-sm font-medium text-gray-700">
              Capital inicial
            </label>
            <input
              id="initial_capital"
              type="number"
              step="0.01"
              min="0.01"
              {...register('initial_capital', { valueAsNumber: true })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="0.00"
            />
            {errors.initial_capital && (
              <p className="mt-1 text-xs text-red-600">{errors.initial_capital.message}</p>
            )}
          </div>

          {/* Periodicidad */}
          <div>
            <label htmlFor="periodicity" className="block text-sm font-medium text-gray-700">
              Periodicidad
            </label>
            <select
              id="periodicity"
              {...register('periodicity')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {Object.entries(periodicityLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            {errors.periodicity && (
              <p className="mt-1 text-xs text-red-600">{errors.periodicity.message}</p>
            )}
          </div>

          {/* Tasa de Interés */}
          <div>
            <label htmlFor="annual_interest_rate" className="block text-sm font-medium text-gray-700">
              Tasa de interés anual (%)
            </label>
            <input
              id="annual_interest_rate"
              type="number"
              step="0.01"
              min="0"
              max="100"
              {...register('annual_interest_rate', { valueAsNumber: true })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="12.00"
            />
            {errors.annual_interest_rate && (
              <p className="mt-1 text-xs text-red-600">{errors.annual_interest_rate.message}</p>
            )}
          </div>

          {/* Fecha de Inicio */}
          <div>
            <label htmlFor="start_date" className="block text-sm font-medium text-gray-700">
              Fecha de inicio
            </label>
            <input
              id="start_date"
              type="date"
              {...register('start_date')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {errors.start_date && (
              <p className="mt-1 text-xs text-red-600">{errors.start_date.message}</p>
            )}
          </div>

          {/* API Error */}
          {apiErrorMessage && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{apiErrorMessage}</p>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? 'Guardando…' : 'Crear crédito'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default CreditForm
