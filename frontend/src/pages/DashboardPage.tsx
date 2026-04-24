import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGetClientsQuery } from '../store/api/apiSlice'
import { AppLayout } from '../components/AppLayout'
import { Client } from '../types'

export function DashboardPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const { data, isLoading } = useGetClientsQuery(
    { search: search || undefined, limit: 20, offset: 0 }
  )
  const clients: Client[] = data?.items ?? []

  return (
    <AppLayout>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800">Clients</h2>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/clients')}
            className="border border-blue-600 text-blue-600 px-4 py-2 rounded-lg text-sm hover:bg-blue-50"
          >
            View All
          </button>
          <button
            onClick={() => navigate('/clients/new')}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
          >
            + Add Client
          </button>
        </div>
      </div>

      <input
        placeholder="Search by name or phone..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border rounded-lg px-3 py-2 text-sm mb-4"
      />

      {isLoading ? (
        <p className="text-center text-gray-500">Loading...</p>
      ) : clients.length === 0 ? (
        <p className="text-center text-gray-400 mt-8">No clients yet.</p>
      ) : (
        <ul className="space-y-2">
          {clients.map((client: Client) => (
            <li
              key={client.id}
              onClick={() => navigate(`/clients/${client.id}`)}
              className="bg-white rounded-xl shadow px-4 py-3 cursor-pointer hover:shadow-md transition"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">
                    {client.first_name} {client.last_name}
                  </p>
                  <p className="text-sm text-gray-500">{client.phone}</p>
                </div>
                {(client.mora_count ?? 0) > 0 && (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full font-medium">
                    Mora
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </AppLayout>
  )
}
