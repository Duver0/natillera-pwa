import { ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface AppLayoutProps {
  children: ReactNode
}

const NAV_LINKS = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Clients', path: '/clients' },
]

export function AppLayout({ children }: AppLayoutProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span
              className="text-lg font-bold text-gray-900 cursor-pointer"
              onClick={() => navigate('/dashboard')}
            >
              Natillera
            </span>
            <nav className="flex gap-4">
              {NAV_LINKS.map((link) => {
                const active = location.pathname === link.path
                return (
                  <button
                    key={link.path}
                    onClick={() => navigate(link.path)}
                    className={`text-sm font-medium pb-1 border-b-2 transition ${
                      active
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {link.label}
                  </button>
                )
              })}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">{user?.email}</span>
            <button onClick={logout} className="text-sm text-red-600 hover:underline">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">{children}</main>
    </div>
  )
}
