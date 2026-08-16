import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { auditApi, formatTs } from '../api/client'
import type { ApiResult, PageData } from '../api/client'

type CharRow = {
  id: string
  owner_id: string
  name: string
  status: string
  is_public: boolean
  created_at: string | null
}

export default function Characters() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [applied, setApplied] = useState('')
  const [galleryOnly, setGalleryOnly] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<string | null>(null)

  const list = useQuery({
    queryKey: ['admin', 'characters', applied],
    queryFn: async () => {
      const res = await auditApi.get<ApiResult<PageData<CharRow>>>('/admin/characters', {
        params: { page: 1, page_size: 50, search: applied || undefined },
      })
      return res.data.data
    },
  })

  const raw = list.data?.items || []
  const items = galleryOnly ? raw.filter((c) => c.is_public) : raw
  const total = list.data?.total || 0

  async function setPublic(id: string, is_public: boolean) {
    setBusy(id)
    try {
      await auditApi.put(`/admin/characters/${id}/visibility`, { is_public })
      qc.invalidateQueries({ queryKey: ['admin', 'characters'] })
    } catch {
      setError('更新可见性失败')
    } finally {
      setBusy(null)
    }
  }

  async function remove(id: string) {
    if (!window.confirm('确认删除该角色？')) return
    setBusy(id)
    try {
      await auditApi.delete(`/admin/characters/${id}`)
      qc.invalidateQueries({ queryKey: ['admin', 'characters'] })
    } catch {
      setError('删除失败')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="page wide">
      <h1>角色</h1>
      <div className="row">
        <input
          value={search}
          placeholder="搜索角色名"
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="button" onClick={() => setApplied(search)}>
          搜索
        </button>
      </div>
      <label className="muted">
        <input
          type="checkbox"
          checked={galleryOnly}
          onChange={(e) => setGalleryOnly(e.target.checked)}
        />{' '}
        只看画廊公开
      </label>
      <p className="muted">共 {total} 个</p>
      {(error || list.isError) && <p className="error">{error || '加载角色失败'}</p>}
      <ul className="checklist">
        {items.map((c) => (
          <li key={c.id}>
            <strong>{c.name}</strong>
            <span className={`status-pill ${c.is_public ? 'enabled' : 'disabled'}`}>
              {c.is_public ? '公开' : '私有'}
            </span>
            <span className={`status-pill ${c.status}`}>{c.status}</span>
            <span className="muted"> · {formatTs(c.created_at)}</span>
            <div className="row">
              {c.is_public ? (
                <button type="button" disabled={busy === c.id} onClick={() => setPublic(c.id, false)}>
                  下架画廊
                </button>
              ) : (
                <button type="button" disabled={busy === c.id} onClick={() => setPublic(c.id, true)}>
                  公开
                </button>
              )}
              <button type="button" disabled={busy === c.id} onClick={() => remove(c.id)}>
                删除
              </button>
            </div>
          </li>
        ))}
      </ul>
      {items.length === 0 && !error && !list.isError && <p>暂无角色</p>}
    </div>
  )
}
