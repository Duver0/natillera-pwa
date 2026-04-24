import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AppLayout } from '../components/AppLayout'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  useGetClientQuery,
  useCreateClientMutation,
  useUpdateClientMutation,
} from '../store/api/apiSlice'

const clientSchema = z.object({
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().min(1, 'Last name is required'),
  phone: z.string().min(1, 'Phone is required'),
  document_id: z.string().optional(),
  address: z.string().optional(),
  notes: z.string().optional(),
})

type ClientFormData = z.infer<typeof clientSchema>

export function ClientFormPage() {
  const { clientId } = useParams<{ clientId?: string }>()
  const isEdit = clientId !== undefined && clientId !== 'new'
  const navigate = useNavigate()

  const { data: existing } = useGetClientQuery(clientId!, { skip: !isEdit })
  const [createClient, { isLoading: creating }] = useCreateClientMutation()
  const [updateClient, { isLoading: updating }] = useUpdateClientMutation()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ClientFormData>({
    resolver: zodResolver(clientSchema),
  })

  useEffect(() => {
    if (existing) {
      reset({
        first_name: existing.first_name,
        last_name: existing.last_name,
        phone: existing.phone,
        document_id: existing.document_id ?? '',
        address: existing.address ?? '',
        notes: existing.notes ?? '',
      })
    }
  }, [existing, reset])

  const onSubmit = async (data: ClientFormData) => {
    if (isEdit) {
      await updateClient({ id: clientId!, data })
      navigate(`/clients/${clientId}`)
    } else {
      const created = await createClient(data).unwrap()
      navigate(`/clients/${created.id}`)
    }
  }

  const isSubmitting = creating || updating

  return (
    <AppLayout>
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate(-1)} className="text-blue-600 text-sm">
          Back
        </button>
        <h2 className="text-xl font-semibold text-gray-800">
          {isEdit ? 'Edit Client' : 'New Client'}
        </h2>
      </div>
      <div className="max-w-lg">
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="bg-white rounded-xl shadow p-6 space-y-4"
          data-testid="client-form"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">First Name *</label>
            <input
              {...register('first_name')}
              data-testid="input-first-name"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            {errors.first_name && (
              <p className="text-red-500 text-xs mt-1">{errors.first_name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
            <input
              {...register('last_name')}
              data-testid="input-last-name"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            {errors.last_name && (
              <p className="text-red-500 text-xs mt-1">{errors.last_name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone *</label>
            <input
              {...register('phone')}
              data-testid="input-phone"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            {errors.phone && (
              <p className="text-red-500 text-xs mt-1">{errors.phone.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Document ID</label>
            <input
              {...register('document_id')}
              data-testid="input-document-id"
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
            <input
              {...register('address')}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              {...register('notes')}
              rows={3}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            data-testid="submit-client"
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Saving...' : isEdit ? 'Update Client' : 'Create Client'}
          </button>
        </form>
      </div>
    </AppLayout>
  )
}
