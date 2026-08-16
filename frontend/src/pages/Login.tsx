import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

// 只允许站内相对路径，防止开放重定向
function safeRedirect(raw: string | null): string {
  if (!raw) return '/'
  if (!raw.startsWith('/') || raw.startsWith('//')) return '/'
  if (raw.startsWith('/login') || raw.startsWith('/register')) return '/'
  return raw
}

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [username, setUsername] = useState('usertest')
  const [password, setPassword] = useState('123456')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post<
        ApiResult<{ token: { token: string }; user: { username: string } }>
      >('/auth/login', { username, password })
      if (data.code !== 200) {
        setError(data.message || '登录失败')
        return
      }
      localStorage.setItem('token', data.data.token.token)
      navigate(safeRedirect(searchParams.get('redirect')), { replace: true })
    } catch {
      setError('登录失败，请检查账号或后端是否启动')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <h1>MADF 登录</h1>
      <form onSubmit={onSubmit} className="card">
        <label>
          用户名
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          密码
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? '登录中…' : '登录'}
        </button>
      </form>
      <p style={{ marginTop: 16 }}>
        还没有账号？<Link to="/register">去注册</Link>
      </p>
    </div>
  )
}
