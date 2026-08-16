import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { auditBasename } from './api/base'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import Discussions from './pages/Discussions'
import Health from './pages/Health'
import Characters from './pages/Characters'
import Events from './pages/Events'
import Admins from './pages/Admins'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter basename={auditBasename()}>
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
    </BrowserRouter>
  )
}
