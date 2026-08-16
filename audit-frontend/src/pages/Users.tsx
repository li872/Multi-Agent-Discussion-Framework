import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
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
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [applied, setApplied] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<string | null>(null)

  const list = useQuery({
    queryKey: ['admin', 'users', applied],
    queryFn: async () => {
      const res = await auditApi.get<ApiResult<PageData<UserRow>>>('/admin/users', {
        params: { page: 1, page_size: 50, search: applied || undefined },
      })
      return res.data.data
    },
  })

  const items = list.data?.items || []
  const total = list.data?.total || 0

  async function setStatus(id: string, enabled: boolean) {
    setBusy(id)
    try {
      await auditApi.put(`/admin/users/${id}/status`, { enabled })
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
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
        <button type="button" onClick={() => setApplied(search)}>
          搜索
        </button>
      </div>
      <p className="muted">共 {total} 人</p>
      {(error || list.isError) && <p className="error">{error || '加载用户失败'}</p>}
      <ul className="checklist">
        {items.map((u) => (
          <li key={u.id}>
            <strong>{u.username}</strong>
            <span className={`status-pill ${u.status}`}>{u.status}</span>
            <span className="muted">
              {' '}
              · {u.phone || '无手机号'} · {formatTs(u.created_at)}
            </span>
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
      {items.length === 0 && !error && !list.isError && <p>暂无用户</p>}
    </div>
  )
}
