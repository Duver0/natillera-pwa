import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Provider } from 'react-redux'
import { store } from './store/store'
import { AppStartup } from './components/AppStartup'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AppLayout } from './components/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { DashboardPage } from './pages/DashboardPage'
import { ClientDetailPage } from './pages/ClientDetailPage'
import { ClientFormPage } from './pages/ClientFormPage'
import { CreditFormPage } from './pages/CreditFormPage'
import { ClientListPage } from './pages/ClientListPage'
import { SavingsPage } from './pages/SavingsPage'
import { HistoryPage } from './pages/HistoryPage'
import { InstallPrompt } from './components/InstallPrompt'

export default function App() {
  return (
    <Provider store={store}>
      <HashRouter>
        <AppStartup>
        <InstallPrompt />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <ClientListPage />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients/new"
            element={
              <ProtectedRoute>
                <ClientFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients/:clientId/edit"
            element={
              <ProtectedRoute>
                <ClientFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients/:clientId/credits/new"
            element={
              <ProtectedRoute>
                <CreditFormPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients/:clientId/savings"
            element={
              <ProtectedRoute>
                <SavingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients/:clientId/history"
            element={
              <ProtectedRoute>
                <HistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients/:clientId"
            element={
              <ProtectedRoute>
                <ClientDetailPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        </AppStartup>
      </HashRouter>
    </Provider>
  )
}
