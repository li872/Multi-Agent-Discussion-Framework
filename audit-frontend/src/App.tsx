import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { auditBasename } from './api/base'
import { queryClient } from './queryClient'
import Layout from './components/Layout'
import PageFallback from './components/PageFallback'

const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Users = lazy(() => import('./pages/Users'))
const Discussions = lazy(() => import('./pages/Discussions'))
const Health = lazy(() => import('./pages/Health'))
const Characters = lazy(() => import('./pages/Characters'))
const Events = lazy(() => import('./pages/Events'))
const Admins = lazy(() => import('./pages/Admins'))
const Settings = lazy(() => import('./pages/Settings'))

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={auditBasename()}>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/users" element={<Users />} />
              <Route path="/characters" element={<Characters />} />
              <Route path="/discussions" element={<Discussions />} />
              <Route path="/health" element={<Health />} />
              <Route path="/events" element={<Events />} />
              <Route path="/admins" element={<Admins />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
