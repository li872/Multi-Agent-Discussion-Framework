import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'

export default function Register() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!username.trim() || password.length < 6) {
      setError('用户名必填，密码至少 6 位')
      return
    }
    setError('')
    setLoading(true)
    try {
      const body: { username: string; password: string; phone?: string } = {
        username: username.trim(),
        password,
      }
      if (phone.trim()) body.phone = phone.trim()

      const { data } = await api.post<
        ApiResult<{ token: { token: string }; user: { username: string } }>
      >('/auth/register', body)

      if (data.code !== 200) {
        setError(data.message || '注册失败')
        return
      }
      localStorage.setItem('token', data.data.token.token)
      navigate('/discussions')
    } catch {
      setError('注册失败（用户名可能已存在，或后端未启动）')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <h1>注册</h1>
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
        <label>
          手机号（可选）
          <input value={phone} onChange={(e) => setPhone(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? '注册中…' : '注册'}
        </button>
      </form>
      <p>
        <Link to="/login">已有账号？去登录</Link>
      </p>
    </div>
  )
}