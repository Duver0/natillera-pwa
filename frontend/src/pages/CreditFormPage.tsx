import { useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useCreateCreditMutation } from '../store/api/apiSlice'
import { AppLayout } from '../components/AppLayout'

const creditSchema = z.object({
  initial_capital: z.coerce.number().gt(0, 'Capital must be greater than 0'),
  annual_interest_rate: z.coerce.number().min(0, 'Rate cannot be negative'),
  periodicity: z.enum(['DAILY', 'WEEKLY', 'BIWEEKLY', 'MONTHLY']),
  start_date: z.string().min(1, 'Start date is required'),
})

type CreditFormData = z.infer<typeof creditSchema>

export function CreditFormPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const [createCredit, { isLoading }] = useCreateCreditMutation()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CreditFormData>({
    resolver: zodResolver(creditSchema),
    defaultValues: {
      periodicity: 'MONTHLY',
      start_date: new Date().toISOString().split('T')[0],
    },
  })

  const onSubmit = async (data: CreditFormData) => {
    await createCredit({ ...data, client_id: clientId })
    navigate(`/clients/${clientId}`)
  }

  return (
    <AppLayout>
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate(`/clients/${clientId}`)} className="text-blue-600 text-sm">
          Back
        </button>
        <h2 className="text-xl font-semibold text-gray-800">New Credit</h2>
      </div>
      <div className="max-w-lg">
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="bg-white rounded-xl shadow p-6 space-y-4"
          data-testid="credit-form"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Initial Capital *
            </label>
            <input
              type="number"
              step="0.01"
              {...register('initial_capital')}
              data-testid="input-capital"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            {errors.initial_capital && (
              <p className="text-red-500 text-xs mt-1">{errors.initial_capital.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Annual Interest Rate (%) *
            </label>
            <input
              type="number"
              step="0.01"
              {...register('annual_interest_rate')}
              data-testid="input-rate"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            {errors.annual_interest_rate && (
              <p className="text-red-500 text-xs mt-1">{errors.annual_interest_rate.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Periodicity *
            </label>
            <select
              {...register('periodicity')}
              data-testid="input-periodicity"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              <option value="MONTHLY">Monthly</option>
              <option value="WEEKLY">Weekly</option>
              <option value="BIWEEKLY">Biweekly</option>
              <option value="DAILY">Daily</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Date *</label>
            <input
              type="date"
              {...register('start_date')}
              data-testid="input-start-date"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            {errors.start_date && (
              <p className="text-red-500 text-xs mt-1">{errors.start_date.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            data-testid="submit-credit"
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Creating...' : 'Create Credit'}
          </button>
        </form>
      </div>
    </AppLayout>
  )
}
