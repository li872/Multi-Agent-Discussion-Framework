import { useEffect, useState } from 'react'
import { auditApi, formatTs } from '../api/client'
import type { ApiResult, PageData } from '../api/client'

type UserRow = {
  id: string
  username: string
  phone: string | null
  status: string
  created_at: string | null
}

export default function Users() {
  const [items, setItems] = useState<UserRow[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<string | null>(null)

  async function load(q = search) {
    const res = await auditApi.get<ApiResult<PageData<UserRow>>>('/admin/users', {
      params: { page: 1, page_size: 50, search: q || undefined },
    })
    setItems(res.data.data?.items || [])
    setTotal(res.data.data?.total || 0)
  }

  useEffect(() => {
    load('').catch(() => setError('加载用户失败'))
  }, [])

  async function setStatus(id: string, enabled: boolean) {
    setBusy(id)
    try {
      await auditApi.put(`/admin/users/${id}/status`, { enabled })
      await load()
    } catch {
      setError('更新状态失败')
    } finally {
      setBusy(null)
    }
  }

  async function resetPassword(id: string) {
    const password = window.prompt('新密码（至少 6 位）')
    if (!password || password.length < 6) return
    setBusy(id)
    try {
      await auditApi.put(`/admin/users/${id}/password`, { password })
    } catch {
      setError('重置密码失败')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="page wide">
      <h1>用户</h1>
      <div className="row">
        <input
          value={search}
          placeholder="搜索用户名"
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="button" onClick={() => load().catch(() => setError('加载用户失败'))}>
          搜索
        </button>
      </div>
      <p className="muted">共 {total} 人</p>
      {error && <p className="error">{error}</p>}
      <ul className="checklist">
        {items.map((u) => (
          <li key={u.id}>
            <strong>{u.username}</strong>
            <span className={`status-pill ${u.status}`}>{u.status}</span>
            <span className="muted"> · {u.phone || '无手机号'} · {formatTs(u.created_at)}</span>
            <div className="row">
              {u.status === 'enabled' ? (
                <button type="button" disabled={busy === u.id} onClick={() => setStatus(u.id, false)}>
                  禁用
                </button>
              ) : (
                <button type="button" disabled={busy === u.id} onClick={() => setStatus(u.id, true)}>
                  启用
                </button>
              )}
              <button type="button" disabled={busy === u.id} onClick={() => resetPassword(u.id)}>
                改密码
              </button>
            </div>
          </li>
        ))}
      </ul>
      {items.length === 0 && !error && <p>暂无用户</p>}
    </div>
  )
}
