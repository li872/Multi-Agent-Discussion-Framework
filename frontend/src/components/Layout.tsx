import { Suspense } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import LogoutButton from './LogoutButton'
import PageFallback from './PageFallback'

const NAV = [
  { to: '/', label: '首页', end: true },
  { to: '/discussions', label: '讨论', end: false },
  { to: '/characters', label: '角色', end: false },
  { to: '/gallery', label: '画廊', end: true },
  { to: '/generate', label: '生成', end: true },
  { to: '/discussions/new', label: '新建讨论', end: true },
  { to: '/profile', label: '个人中心', end: true },
]

function linkActive(pathname: string, to: string, end?: boolean): boolean {
  if (to === '/discussions') {
    // 讨论列表与讨论室高亮「讨论」，但新建讨论走自己的入口
    if (pathname === '/discussions/new') return false
    return pathname === '/discussions' || pathname.startsWith('/discussions/')
  }
  if (end) return pathname === to
  return pathname === to || pathname.startsWith(`${to}/`)
}

// 业务页外壳：统一顶栏导航 + 登录守卫（带 redirect）
export default function Layout() {
  const token = localStorage.getItem('token')
  const location = useLocation()

  if (!token) {
    const redirect = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?redirect=${redirect}`} replace />
  }

  return (
    <div className="app-shell">
      <header className="app-nav">
        <Link to="/" className="app-brand">
          MADF
        </Link>
        <nav className="app-nav-links">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={() =>
                linkActive(location.pathname, item.to, item.end)
                  ? 'app-nav-link active'
                  : 'app-nav-link'
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <LogoutButton />
      </header>
      <main className="app-main">
        <Suspense fallback={<PageFallback />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
