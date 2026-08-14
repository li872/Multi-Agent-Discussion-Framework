import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Login from './pages/Login'
import NewDiscussion from './pages/NewDiscussion'
import DiscussionRoom from './pages/DiscussionRoom'
import Characters from './pages/Characters'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/discussions/new"
          element={
            <RequireAuth>
              <NewDiscussion />
            </RequireAuth>
          }
        />
        <Route
          path="/discussions/:id"
          element={
            <RequireAuth>
              <DiscussionRoom />
            </RequireAuth>
          }
        />
        <Route
          path="/characters"
          element={
            <RequireAuth>
              <Characters />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}