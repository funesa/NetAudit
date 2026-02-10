import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Scanner from './pages/Scanner'
import IPMap from './pages/IPMap'
import ADUsers from './pages/ADUsers'
import ADStorage from './pages/ADStorage'
import Security from './pages/Security'
import Tickets from './pages/Tickets'
import Settings from './pages/Settings'

import License from './pages/License'
import Topology from './pages/Topology'
import Layout from './components/Layout'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'))

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={
              isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login onLogin={() => setIsAuthenticated(true)} />
            }
          />

          <Route
            path="/dashboard"
            element={
              isAuthenticated ? (
                <Layout><Dashboard /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/scanner"
            element={
              isAuthenticated ? (
                <Layout><Scanner /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/ip-map"
            element={
              isAuthenticated ? (
                <Layout><IPMap /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/ad-users"
            element={
              isAuthenticated ? (
                <Layout><ADUsers /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/ad-shares"
            element={
              isAuthenticated ? (
                <Layout><ADStorage /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/security"
            element={
              isAuthenticated ? (
                <Layout><Security /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/tickets"
            element={
              isAuthenticated ? (
                <Layout><Tickets /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/settings"
            element={
              isAuthenticated ? (
                <Layout><Settings /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />


          <Route
            path="/license"
            element={
              isAuthenticated ? (
                <Layout><License /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/topology"
            element={
              isAuthenticated ? (
                <Layout><Topology /></Layout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
