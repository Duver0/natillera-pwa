import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGetClientsQuery } from '../store/api/apiSlice'
import { Client } from '../types'

const PAGE_SIZE = 20

export function ClientListPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)

  const { data, isLoading, isFetching } = useGetClientsQuery(
    { search: search || undefined, limit: PAGE_SIZE, offset },
    { refetchOnMountOrArgChange: true }
  )

  const items: Client[] = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage = Math.floor(offset / PAGE_SIZE)

  const handleSearch = (value: string) => {
    setSearch(value)
    setOffset(0)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800">Clients</h2>
        <button
          onClick={() => navigate('/clients/new')}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
        >
          + Add Client
        </button>
      </div>

      <input
        data-testid="client-search"
        placeholder="Search by name or phone..."
        value={search}
        onChange={(e) => handleSearch(e.target.value)}
        className="w-full border rounded-lg px-3 py-2 text-sm mb-4"
      />

      {isLoading || isFetching ? (
        <p className="text-center text-gray-500">Loading...</p>
      ) : items.length === 0 ? (
        <p className="text-center text-gray-400 mt-8">No clients found.</p>
      ) : (
        <>
          <ul className="space-y-2" data-testid="client-list">
            {items.map((client: Client) => (
              <li
                key={client.id}
                data-testid={`client-row-${client.id}`}
                onClick={() => navigate(`/clients/${client.id}`)}
                className="bg-white rounded-xl shadow px-4 py-3 cursor-pointer hover:shadow-md transition"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">
                      {client.first_name} {client.last_name}
                    </p>
                    <p className="text-sm text-gray-500">{client.phone}</p>
                    {client.document_id && (
                      <p className="text-xs text-gray-400">{client.document_id}</p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {(client.mora_count ?? 0) > 0 && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full font-medium">
                        Mora
                      </span>
                    )}
                    {client.total_debt != null && client.total_debt > 0 && (
                      <span className="text-xs text-gray-600">
                        ${client.total_debt.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-4">
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="px-3 py-1 border rounded-lg text-sm disabled:opacity-40"
              >
                Prev
              </button>
              <span className="text-sm text-gray-600">
                {currentPage + 1} / {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={currentPage >= totalPages - 1}
                className="px-3 py-1 border rounded-lg text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
