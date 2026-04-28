import { useParams, useNavigate } from 'react-router-dom'
import { AppLayout } from '../components/AppLayout'
import { SavingsView } from '../components/SavingsView'
import { useGetClientQuery } from '../store/api/clientApi'

export function SavingsPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const { data: client, isLoading } = useGetClientQuery(clientId!)

  if (isLoading) {
    return (
      <AppLayout>
        <p className="p-8 text-center text-gray-500">Loading...</p>
      </AppLayout>
    )
  }

  if (!client) {
    return (
      <AppLayout>
        <p className="p-8 text-center text-red-500">Client not found</p>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate(`/clients/${clientId}`)}
            aria-label="Back to client detail"
            className="text-blue-600 text-sm hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
          >
            &larr; Back
          </button>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {client.first_name} {client.last_name}
            </h1>
            <p className="text-sm text-gray-500">Savings</p>
          </div>
        </div>

        <SavingsView clientId={clientId!} />
      </div>
    </AppLayout>
  )
}
