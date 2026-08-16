import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ApiResult } from '../api/client'
import { displayName } from '../lib/displayName'

type Character = {
  id: string
  name: string
  description: string
  status: string
  quotes?: string[]
}

export default function Gallery() {
  const qc = useQueryClient()
  const [error, setError] = useState('')
  const [copying, setCopying] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const list = useQuery({
    queryKey: ['gallery', debounced],
    queryFn: async () => {
      const params = debounced ? `?search=${encodeURIComponent(debounced)}` : ''
      const res = await api.get<ApiResult<{ items: Character[] }>>(`/characters/gallery${params}`)
      return res.data.data.items || []
    },
  })

  async function onCopy(id: string, name: string) {
    setCopying(id)
    setError('')
    try {
      await api.post(`/characters/${id}/copy`)
      qc.invalidateQueries({ queryKey: ['characters'] })
      alert(`已复制「${name}」到我的角色`)
    } catch {
      setError('复制失败（可能未登录或角色非公开）')
    } finally {
      setCopying(null)
    }
  }

  const characters = list.data || []

  return (
    <div className="page">
      <h1>公开画廊</h1>
      <div className="row" style={{ marginTop: 16, marginBottom: 8 }}>
        <input
          placeholder="搜索公开角色名或描述"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, maxWidth: 400 }}
        />
      </div>
      {(error || list.isError) && <p className="error">{error || '加载画廊失败'}</p>}
      {characters.length === 0 && !error && !list.isError && <p>暂无公开角色</p>}
      <ul className="checklist">
        {characters.map((c) => (
          <li key={c.id}>
            <strong>{displayName(c.name)}</strong>
            <span> · {c.status}</span>
            {c.description ? <p className="quote">{c.description}</p> : null}
            {c.quotes && c.quotes.length > 1 && (
              <p className="muted">另有 {c.quotes.length - 1} 条引用语</p>
            )}
            <button
              type="button"
              disabled={copying === c.id}
              onClick={() => onCopy(c.id, displayName(c.name))}
            >
              {copying === c.id ? '复制中…' : '复制到我的角色'}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
