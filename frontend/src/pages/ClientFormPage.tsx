import { useNavigate, useParams } from 'react-router-dom'
import { AppLayout } from '../components/AppLayout'
import { ClientForm } from '../components/ClientForm'
import type { ClientFormData } from '../components/ClientForm'
import {
  useGetClientQuery,
  useCreateClientMutation,
  useUpdateClientMutation,
} from '../store/api/clientApi'

export function ClientFormPage() {
  const { clientId } = useParams<{ clientId?: string }>()
  const isEdit = clientId !== undefined && clientId !== 'new'
  const navigate = useNavigate()

  const { data: existing } = useGetClientQuery(clientId!, { skip: !isEdit })
  const [createClient, { isLoading: creating }] = useCreateClientMutation()
  const [updateClient, { isLoading: updating }] = useUpdateClientMutation()

  const onSubmit = async (data: ClientFormData) => {
    if (isEdit) {
      await updateClient({ id: clientId!, data })
      navigate(`/clients/${clientId}`)
    } else {
      const created = await createClient(data).unwrap()
      navigate(`/clients/${created.id}`)
    }
  }

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
      <div className="max-w-lg bg-white rounded-xl shadow p-6">
        <ClientForm
          initial={existing}
          isLoading={creating || updating}
          onSubmit={onSubmit}
          submitLabel={isEdit ? 'Update Client' : 'Create Client'}
        />
      </div>
    </AppLayout>
  )
}
