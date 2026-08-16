import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { auditApi } from '../api/client'
import type { ApiResult } from '../api/client'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('audit123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await auditApi.post<
        ApiResult<{ token: string; admin: { username: string } }>
      >('/audit/auth/login', { username, password })
      if (data.code !== 200 || !data.data?.token) {
        setError(data.message || '登录失败')
        return
      }
      localStorage.setItem('audit_token', data.data.token)
      localStorage.setItem('audit_admin', JSON.stringify(data.data.admin))
      navigate('/', { replace: true })
    } catch {
      setError('登录失败，请检查审计后端是否启动')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <h1>MADF 审计登录</h1>
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
    </div>
  )
}
