import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { auditLoginPath } from '../api/base'

function logout() {
  localStorage.removeItem('audit_token')
  localStorage.removeItem('audit_admin')
  window.location.href = auditLoginPath()
}

export default function Layout() {
  const location = useLocation()
  const token = localStorage.getItem('audit_token')
  if (!token) {
    const redirect = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?redirect=${redirect}`} replace />
  }

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <span className="app-brand">MADF 审计</span>
        <div className="app-nav-links">
          <NavLink to="/" end className="app-nav-link">
            仪表盘
          </NavLink>
          <NavLink to="/users" className="app-nav-link">
            用户
          </NavLink>
          <NavLink to="/characters" className="app-nav-link">
            角色
          </NavLink>
          <NavLink to="/discussions" className="app-nav-link">
            讨论
          </NavLink>
          <NavLink to="/health" className="app-nav-link">
            健康
          </NavLink>
          <NavLink to="/events" className="app-nav-link">
            审计
          </NavLink>
        </div>
        <button type="button" onClick={logout}>
          退出
        </button>
      </nav>
      <div className="app-main">
        <Outlet />
      </div>
    </div>
  )
}
