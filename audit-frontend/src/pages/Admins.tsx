import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { auditApi } from '../api/client'
import type { ApiResult } from '../api/client'
import { auditApiBase } from '../api/base'

type AdminRow = { id: string; username: string; created_at: string }

export default function Admins() {
  const qc = useQueryClient()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const list = useQuery({
    queryKey: ['audit', 'admins'],
    queryFn: async () => {
      const res = await auditApi.get<ApiResult<{ items: AdminRow[] }>>('/audit/admins')
      return res.data.data?.items || []
    },
  })

  async function onCreate() {
    try {
      await auditApi.post('/audit/admins', { username, password })
      setUsername('')
      setPassword('')
      qc.invalidateQueries({ queryKey: ['audit', 'admins'] })
    } catch {
      setError('创建失败（用户名可能已存在）')
    }
  }

  async function onDelete(id: string) {
    if (!window.confirm('删除该管理员？')) return
    try {
      await auditApi.delete(`/audit/admins/${id}`)
      qc.invalidateQueries({ queryKey: ['audit', 'admins'] })
    } catch {
      setError('不能删除最后一名管理员')
    }
  }

  const items = list.data || []

  return (
    <div className="page wide">
      <h1>管理员</h1>
      {(error || list.isError) && <p className="error">{error || '加载管理员失败'}</p>}
      <p className="muted">API {auditApiBase()}</p>
      <div className="card">
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
        <button type="button" onClick={onCreate} disabled={!username || password.length < 6}>
          新增
        </button>
      </div>
      <ul className="checklist">
        {items.map((a) => (
          <li key={a.id}>
            <strong>{a.username}</strong>
            <button type="button" onClick={() => onDelete(a.id)}>
              删除
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
